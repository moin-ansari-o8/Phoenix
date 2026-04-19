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
from Utils.limbs.queue_manager import QueueManager, AudioChunk
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

        # Initialize Faster-Whisper for transcription (CUDA/GPU for speed!)
        self.whisper_model = None
        self.MIN_SILENCE_DURATION = 0.6  # Seconds (optimized for faster response)

        if WHISPER_AVAILABLE:
            try:
                # Try CUDA (GPU) first for maximum speed
                try:
                    import torch

                    cuda_available = torch.cuda.is_available()
                except ImportError:
                    cuda_available = False

                if cuda_available:
                    logger.info("Loading Faster-Whisper (small model) on CUDA/GPU...")
                    self.whisper_model = WhisperModel(
                        "small", device="cuda", compute_type="float16"
                    )
                    logger.info(
                        "Faster-Whisper loaded on GPU - Ultra-fast transcription!"
                    )
                else:
                    logger.info("CUDA not available, loading Faster-Whisper on CPU...")
                    self.whisper_model = WhisperModel(
                        "small", device="cpu", compute_type="int8"
                    )
                    logger.info(
                        "Faster-Whisper loaded on CPU - Ready for transcription!"
                    )
            except Exception as e:
                logger.error(f"Failed to load Whisper: {e}")
                raise RuntimeError("Whisper is required for voice processor!")
        else:
            raise RuntimeError(
                "faster-whisper not available! Install with: pip install faster-whisper"
            )

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

    def transcribe_audio(self, chunk: AudioChunk, timestamp: str = None) -> str:
        """
        Transcribe audio chunk with Faster-Whisper

        Args:
            chunk: AudioChunk to transcribe
            timestamp: Optional timestamp string for when audio was captured

        Returns:
            Transcribed text (empty string if failed)
        """
        try:
            logger.debug(
                f"Transcribing audio (shape: {chunk.audio_data.shape}, dtype: {chunk.audio_data.dtype})"
            )

            # Convert to float32 normalized to [-1.0, 1.0]
            audio_float = chunk.audio_data.astype(np.float32) / 32768.0

            # Compile dynamic prompt if not cached
            if getattr(self, "_dynamic_prompt", None) is None:
                self._dynamic_prompt = self._build_dynamic_prompt()

            # Transcribe with Faster-Whisper (optimized for speed)
            segments, info = self.whisper_model.transcribe(
                audio_float,
                language="en",
                beam_size=1,  # Faster than beam_size=5, minimal accuracy loss
                initial_prompt=self._dynamic_prompt,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=int(self.MIN_SILENCE_DURATION * 1000),
                    threshold=0.3,
                ),
            )

            # Combine all segments
            transcription = " ".join([segment.text for segment in segments]).strip()

            if transcription:
                logger.info(f"Transcribed: '{transcription}'")
                self.transcriptions_count += 1
            else:
                logger.debug("Empty transcription")
                self._runtime_trace("HEARD", "<empty>")
                listening()  # Back to listening

            return transcription

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}", exc_info=True)
            print_block("⚠️  Transcription error")
            listening()
            return ""

    def process_audio_chunk(self, chunk: AudioChunk):
        """
        Process a single audio chunk with wake word logic.

        Flow:
        0. If Phoenix is speaking → Skip (avoid self-listening)
        1. If wake word detected AND loop=False → Process, enable follow-up mode
        2. If loop=True (follow-up mode) → Process without wake word
        3. If no wake word AND loop=False → Ignore
        4. Empty transcription → Reset loop

        Args:
            chunk: AudioChunk to process
        """
        try:
            # Skip processing while Phoenix is speaking (self-voice suppression)
            if self.queue_manager.is_speaking():
                logger.debug("Skipping chunk - Phoenix is speaking")
                self.chunks_processed += 1
                # Also clear the queue to remove any accumulated audio during speech
                try:
                    cleared = 0
                    while not self.queue_manager.is_empty():
                        self.queue_manager.receive_chunk(timeout=0.01)
                        cleared += 1
                        if cleared > 20:  # Safety limit
                            break
                    if cleared > 0:
                        logger.debug(
                            f"Cleared {cleared} chunks from queue during speaking"
                        )
                except:
                    pass
                return

            logger.debug(f"Processing chunk: {chunk.duration:.2f}s")

            # Get timestamp from when audio was captured (for accurate timing)
            chunk_timestamp = datetime.fromtimestamp(chunk.timestamp).strftime(
                "%H:%M:%S"
            )

            # Step 1: Transcribe audio chunk with Whisper
            transcription = self.transcribe_audio(chunk, chunk_timestamp)

            # Empty transcription = reset follow-up mode
            if not transcription:
                self.loop = False
                self.chunks_processed += 1
                listening()  # Back to listening
                return

            # Print to GUI/Console
            if ":" not in chunk_timestamp:
                chunk_timestamp = datetime.now().strftime("%H:%M:%S")
            user_said(transcription, chunk_timestamp)

            # Step 2: Wake word logic
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
