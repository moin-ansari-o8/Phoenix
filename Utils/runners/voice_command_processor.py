"""
Background Voice Processor for Phoenix
Receives audio chunks from queue, transcribes, processes commands, and speaks responses
"""

import sys
import os
import time
import signal
import tkinter as tk
import logging
from datetime import datetime
import numpy as np

# Get root directory for logging
_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Add project root to path so absolute imports like `Utils.limbs...` resolve
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

# Setup logging (file only, console has clean output)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_root_dir, "bg_voice_processor.log")),
    ],
)
logger = logging.getLogger("BgVoiceProcessor")


# Import handlers and helpers
from core.config import AppConfig
from Utils.limbs.audio_capture import SAMPLE_RATE
from Utils.limbs.queue_manager import QueueManager, AudioChunk
from Utils.limbs.speech_filters import (
    HallucinationFilter,
    SelfEchoFilter,
    TranscriptionCandidate,
)
from Utils.limbs.assistant_io import VoiceAssistantGUI, SpeechEngine
from Utils.limbs.action_utilities import Utility, OpenAppHandler, CloseAppHandler
from Utils.limbs.command_processor import PhoenixAssistant
from Utils.limbs.console_ui import (
    user_said,
    phoenix_said,
    listening,
    print_block,
    get_timestamp,
)
from Utils.limbs.time_handlers import (
    TimerHandle,
    AlarmHandle,
    ReminderHandle,
    ScheduleHandle,
)

# Faster-Whisper for offline speech recognition
try:
    from faster_whisper import WhisperModel

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not installed. Processor will not work without it!")


class VoiceProcessor:
    """Background voice command processor"""

    # Wake words that trigger processing (same as original main_assistant.py)
    from core.config import AppConfig

    WAKE_WORDS = AppConfig.wake_words

    def __init__(self, queue_manager):
        """
        Initialize voice processor

        Args:
            queue_manager: QueueManager instance for receiving chunks
        """
        self.queue_manager = queue_manager
        self.running = False
        self.chunks_processed = 0
        self.errors_count = 0
        self.transcriptions_count = 0

        # Wake word / follow-up mode state
        self.loop = False  # True = follow-up mode (no wake word needed)

        logger.info("Initializing VoiceProcessor...")

        # Initialize GUI (hidden for background process)
        self.root = tk.Tk()
        self.root.withdraw()  # Hide GUI window
        self.gui = VoiceAssistantGUI(self.root)

        # Initialize speech engine
        self.speech_engine = SpeechEngine()

        # Initialize utilities (without VoiceRecognition - we handle transcription here)
        self.utility = Utility(spk=self.speech_engine, reco=None)

        # Initialize Faster-Whisper for transcription
        self.whisper_model = None
        self.MIN_SILENCE_DURATION = 0.6

        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "faster-whisper not available! Install with: pip install faster-whisper"
            )

        try:
            self._load_whisper()
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            raise RuntimeError("Whisper is required for voice processor!")

        # Transcript-level defences (see Utils/limbs/speech_filters)
        stt_cfg = AppConfig.stt
        self.hallucination_filter = HallucinationFilter(
            max_no_speech_prob=float(stt_cfg.get("max_no_speech_prob", 0.6)),
            min_avg_logprob=float(stt_cfg.get("min_avg_logprob", -1.0)),
            min_voiced_ms=float(AppConfig.audio.get("min_voiced_ms", 400)),
            wake_words=list(self.WAKE_WORDS),
        )
        self.echo_filter = SelfEchoFilter()

        logger.info("Initializing Phoenix handlers...")

        # Initialize handlers
        self.open_handler = OpenAppHandler(self.utility)
        self.close_handler = CloseAppHandler(self.utility)
        self.timer_handle = TimerHandle(self.utility)
        self.alarm_handle = AlarmHandle(self.utility)
        self.reminder_handle = ReminderHandle(self.utility)
        self.schedule_handle = ScheduleHandle(self.utility)

        # Initialize PhoenixAssistant (intent matcher and action executor)
        self.phoenix_assistant = PhoenixAssistant(
            utility=self.utility,
            open_handler=self.open_handler,
            close_handler=self.close_handler,
            timer_handle=self.timer_handle,
            alarm_handle=self.alarm_handle,
            schedule_handle=self.schedule_handle,
            reminder_handle=self.reminder_handle,
        )

        logger.info("VoiceProcessor initialized successfully")

    def _resolve_device(self, requested: str):
        """
        Pick the Whisper device.

        The old code asked `torch.cuda.is_available()`, but torch here is a
        CPU-only build while CTranslate2 -- the library that actually runs the
        model -- can see the GPU perfectly well. So the probe answered "no GPU"
        for the wrong reason and pinned STT to the CPU permanently.  We now ask
        CTranslate2 directly.

        The default stays CPU regardless: this box has 4 GB of VRAM and Ollama
        already occupies most of it, so borrowing VRAM for STT would slow the
        LLM down by more than it speeds up transcription.
        """
        if requested in ("cpu", "cuda"):
            device = requested
        else:
            device = "cpu"  # "auto" - see docstring

        if device == "cuda":
            try:
                import ctranslate2

                if ctranslate2.get_cuda_device_count() < 1:
                    logger.warning("CUDA requested but no device visible; using CPU")
                    device = "cpu"
            except Exception as exc:
                logger.warning(f"CUDA probe failed ({exc}); using CPU")
                device = "cpu"

        compute_type = "int8" if device == "cpu" else "int8_float16"
        return device, compute_type

    def _load_whisper(self):
        stt_cfg = AppConfig.stt
        model_name = stt_cfg.get("model", "base.en")
        device, compute_type = self._resolve_device(stt_cfg.get("device", "auto"))

        for attempt_device, attempt_compute in ((device, compute_type), ("cpu", "int8")):
            logger.info(
                f"Loading Faster-Whisper '{model_name}' on {attempt_device} "
                f"({attempt_compute})..."
            )
            kwargs = {"device": attempt_device, "compute_type": attempt_compute}
            if attempt_device == "cpu":
                # 6 physical cores here; more threads than that buys ~2%.
                kwargs["cpu_threads"] = 6

            try:
                model = WhisperModel(model_name, **kwargs)

                # Warm up on the real code path. A cold model costs a couple of
                # seconds on its first call, and this is also where a broken
                # CUDA install surfaces: the model loads fine and only fails at
                # encode time with a missing cublas DLL, so warming up on GPU is
                # the only way to find out before the user's first command does.
                warm_start = time.time()
                list(
                    model.transcribe(
                        np.zeros(SAMPLE_RATE, dtype=np.float32),
                        language="en",
                        beam_size=1,
                    )[0]
                )
                self.whisper_model = model
                self.stt_device = attempt_device
                logger.info(
                    f"Whisper ready on {attempt_device} "
                    f"(warm-up {time.time() - warm_start:.2f}s)"
                )
                return
            except Exception as exc:
                if attempt_device == "cpu":
                    raise
                logger.warning(f"Whisper on {attempt_device} unusable ({exc}); using CPU")

    def has_wake_word(self, text: str) -> bool:
        """Check if text contains any wake word"""
        text_lower = text.lower()
        return any(word in text_lower for word in self.WAKE_WORDS)

    def _runtime_trace(self, tag: str, message: str):
        """Emit concise stdout trace lines that the runtime manager can forward."""
        print(f"\n[{tag}] {message}", flush=True)

    def _build_dynamic_prompt(self) -> str:
        """
        Builds a dynamic context string (initial_prompt) to feed to Faster-Whisper.
        This tells the model what words to 'expect', fixing phonetically hallucinated
        wake words (e.g. 'increase' instead of 'igris', 'rice' instead of 'arise').
        """
        try:
            from core.config import AppConfig
            import json

            # Start with proper capitalized forms of wake words
            prompt_words = set()
            for ww in self.WAKE_WORDS:
                prompt_words.add(ww.capitalize())

            # Add the user name
            user_name = getattr(AppConfig, "user_name", "User").capitalize()
            prompt_words.add(user_name)

            # Load intents.json to add domain-specific vocabulary
            intents_path = os.path.join(_root_dir, "data", "intents.json")
            if os.path.exists(intents_path):
                with open(intents_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Extract some high-value command words from patterns
                # We don't want the prompt to be too huge, but Whisper handles a comma-separated list well.
                for intent in data.get("intents", []):
                    for pattern in intent.get("patterns", []):
                        for word in pattern.split():
                            word = word.lower().strip("?!.,;")
                            if (
                                len(word) > 4
                            ):  # Filter out common short words to save token space
                                prompt_words.add(word)

            # Give specific hints for known troublesome phonetic pairs
            prompt_words.add("Arise")
            prompt_words.add("Igris")
            prompt_words.add("Phoenix")

            # Sort to make deterministic, limit to ~80 unique words so we don't overflow context
            prompt_list = sorted(list(prompt_words))[:80]

            final_prompt = f"Commands and entities: {', '.join(prompt_list)}."
            logger.info(f"Generated dynamic STT prompt: {final_prompt}")
            return final_prompt

        except Exception as e:
            logger.error(f"Error building dynamic prompt: {e}")
            return "Commands: Phoenix, Igris, arise, open, weather, time, user."

    def transcribe_audio(self, chunk: AudioChunk) -> TranscriptionCandidate:
        """
        Transcribe an utterance with Faster-Whisper.

        Returns a TranscriptionCandidate carrying the text plus the two
        confidence signals Whisper exposes, which the hallucination filter needs
        to tell "the user said thank you" from "the model invented thank you
        because it was fed silence".

        `vad_filter` is deliberately off: the listener already ran Silero over
        this audio frame by frame, and re-running it here would be pure
        duplicated work on the critical path.
        """
        try:
            audio_float = chunk.audio_data.astype(np.float32) / 32768.0

            if getattr(self, "_dynamic_prompt", None) is None:
                self._dynamic_prompt = self._build_dynamic_prompt()

            started = time.time()
            segments, info = self.whisper_model.transcribe(
                audio_float,
                language="en",
                beam_size=int(AppConfig.stt.get("beam_size", 1)),
                initial_prompt=self._dynamic_prompt,
                condition_on_previous_text=False,  # stops hallucination loops
                vad_filter=False,
                word_timestamps=False,
            )

            texts = []
            no_speech_prob = 0.0
            avg_logprob = 0.0
            for segment in segments:
                texts.append(segment.text)
                no_speech_prob = max(no_speech_prob, getattr(segment, "no_speech_prob", 0.0))
                avg_logprob = min(avg_logprob, getattr(segment, "avg_logprob", 0.0))

            elapsed = time.time() - started
            text = " ".join(texts).strip()

            self._runtime_trace(
                "STT",
                f"utt={chunk.duration:.1f}s voiced={chunk.voiced_ms/1000:.1f}s "
                f"stt={elapsed:.2f}s rtf={elapsed / max(chunk.duration, 0.01):.2f}",
            )

            if text:
                self.transcriptions_count += 1
                logger.info(
                    "Transcribed in %.2fs: '%s' (no_speech=%.2f, logprob=%.2f)",
                    elapsed,
                    text,
                    no_speech_prob,
                    avg_logprob,
                )

            return TranscriptionCandidate(
                text=text,
                duration=chunk.duration,
                voiced_ms=chunk.voiced_ms,
                no_speech_prob=no_speech_prob,
                avg_logprob=avg_logprob,
            )

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}", exc_info=True)
            return TranscriptionCandidate(text="")

    def process_audio_chunk(self, chunk: AudioChunk):
        """
        Process one complete utterance.

        Flow:
        1. Transcribe
        2. Reject Whisper hallucinations (silence artefacts)
        3. Reject / trim Phoenix's own voice
        4. Wake word gives one command; a matched command opens follow-up mode
        """
        try:
            logger.debug(f"Processing utterance: {chunk.duration:.2f}s")
            chunk_timestamp = datetime.fromtimestamp(chunk.timestamp).strftime(
                "%H:%M:%S"
            )

            candidate = self.transcribe_audio(chunk)

            # Step 2: is this something Whisper invented?
            reason = self.hallucination_filter.rejection_reason(candidate)
            if reason:
                logger.info(f"Discarded '{candidate.text}': {reason}")
                self._runtime_trace("DISCARDED", f"{candidate.text or '<empty>'} ({reason})")
                self.chunks_processed += 1
                return

            # Step 3: is this Phoenix hearing itself? The acoustic gate in the
            # listener is the first line of defence; this is the second, and it
            # also catches speech from other Phoenix processes (battery/time
            # announcements are spoken by the TUI process, not this one).
            self.echo_filter.set_history(self.queue_manager.recent_tts())
            verdict = self.echo_filter.check(candidate.text)
            if verdict.rejected:
                logger.info(f"Self-echo rejected '{candidate.text}': {verdict.reason}")
                self._runtime_trace("SELF_ECHO", candidate.text)
                self.chunks_processed += 1
                return

            transcription = verdict.text
            if verdict.action == "trim":
                logger.info(f"Self-echo trimmed: {verdict.reason} -> '{transcription}'")

            user_said(transcription, chunk_timestamp)

            # Step 4: Wake word logic
            has_wake = self.has_wake_word(transcription)

            if has_wake and not self.loop:
                # Wake word detected, process command
                self._runtime_trace("HEARD", transcription)
                logger.info(f"Wake word detected: '{transcription}'")
                self._runtime_trace("PROCESSING", "wake word detected")
                result = self.phoenix_assistant.main(transcription)
                self._runtime_trace(
                    "INTENT", "matched" if result is not False else "no match"
                )
                self.loop = True if result is not False else False
                listening()  # Back to listening

            elif self.loop:
                # Follow-up mode - process without wake word
                self._runtime_trace("HEARD", transcription)
                logger.info(f"Follow-up: '{transcription}'")
                self._runtime_trace("PROCESSING", "follow-up mode")
                result = self.phoenix_assistant.main(transcription)
                self._runtime_trace(
                    "INTENT", "matched" if result is not False else "no match"
                )
                self.loop = True if result is not False else False
                listening()  # Back to listening

            else:
                # No wake word - ignored
                self._runtime_trace("IGNORED_HEARD", transcription)
                self.loop = False
                listening()  # Back to listening

            self.chunks_processed += 1

        except Exception as e:
            self.errors_count += 1
            self.loop = False
            logger.error(f"Error processing chunk: {e}", exc_info=True)
            listening()

    def main_loop(self):
        """Main processing loop - receives and processes chunks"""
        logger.info("Starting main processing loop...")
        self.running = True

        consecutive_empty_count = 0
        max_consecutive_empty = 50

        while self.running:
            try:
                # Receive chunk from queue (0.1s timeout)
                chunk = self.queue_manager.receive_chunk(timeout=0.1)

                if chunk is not None:
                    consecutive_empty_count = 0
                    self.process_audio_chunk(chunk)
                else:
                    # No chunk available
                    consecutive_empty_count += 1

                    if consecutive_empty_count >= max_consecutive_empty:
                        if consecutive_empty_count == max_consecutive_empty:
                            logger.debug(
                                "Queue empty for 5+ seconds, waiting for audio..."
                            )
                        consecutive_empty_count = 0  # Reset to avoid spam

                # Brief sleep to prevent CPU spinning
                time.sleep(0.01)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down...")
                break
            except Exception as e:
                self.errors_count += 1
                logger.error(f"Error in main loop: {e}", exc_info=True)
                # Continue running despite errors
                time.sleep(0.1)

        logger.info("Main loop stopped")

    def get_stats(self):
        """Get processor statistics"""
        return {
            "chunks_processed": self.chunks_processed,
            "transcriptions_count": self.transcriptions_count,
            "errors_count": self.errors_count,
            "queue_stats": self.queue_manager.get_stats(),
        }

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down VoiceProcessor...")
        self.running = False

        # Print statistics
        stats = self.get_stats()
        logger.info("=== Processor Statistics ===")
        logger.info(f"  Chunks processed: {stats['chunks_processed']}")
        logger.info(f"  Successful transcriptions: {stats['transcriptions_count']}")
        logger.info(f"  Errors: {stats['errors_count']}")
        logger.info(f"  Queue stats: {stats['queue_stats']}")

        # Cleanup
        try:
            self.root.destroy()
        except:
            pass

        logger.info("Shutdown complete")


class ProcessManager:
    """Manages the background processor lifecycle"""

    def __init__(self):
        self.processor = None
        self.queue_manager = None

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        if self.processor:
            self.processor.shutdown()
        sys.exit(0)

    def start(self):
        """Start the background processor"""
        try:
            logger.info("=" * 70)
            logger.info("PHOENIX BACKGROUND VOICE PROCESSOR")
            logger.info("=" * 70)
            logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("")

            # Initialize queue manager
            logger.info("Initializing queue manager...")
            self.queue_manager = QueueManager(max_size=10)

            # Initialize processor
            logger.info("Initializing voice processor...")
            self.processor = VoiceProcessor(self.queue_manager)

            # Start main loop
            logger.info("Starting processing loop...")
            logger.info("Ready to receive audio chunks from listener!")
            logger.info("")

            self.processor.main_loop()

        except Exception as e:
            logger.critical(
                f"CRITICAL ERROR: Processor failed to start: {e}", exc_info=True
            )
            sys.exit(1)
        finally:
            if self.processor:
                self.processor.shutdown()


if __name__ == "__main__":
    try:
        manager = ProcessManager()
        manager.start()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
