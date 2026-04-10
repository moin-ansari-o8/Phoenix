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

# Add project root to path so absolute imports like `utils.helpers...` resolve
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
from utils.helpers.queue_manager import QueueManager, AudioChunk
from utils.helpers.assistant_io import VoiceAssistantGUI, SpeechEngine
from utils.helpers.action_utilities import Utility, OpenAppHandler, CloseAppHandler
from utils.helpers.command_processor import PhoenixAssistant
from utils.helpers.console_ui import user_said, phoenix_said, listening, print_block, get_timestamp
from utils.helpers.time_handlers import (
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


def is_speaking():
    """Check if Phoenix is currently speaking (via shared file)"""
    speaking_file = os.path.join(_root_dir, ".speaking")
    if os.path.exists(speaking_file):
        try:
            with open(speaking_file, "r") as f:
                start_time = float(f.read().strip())
            # Speaking flag valid for max 30 seconds (safety)
            if time.time() - start_time < 30:
                logger.debug("is_speaking() = True (Phoenix is speaking, audio will be skipped)")
                return True
            # Stale file, remove it
            logger.warning("Stale .speaking file detected, removing")
            os.remove(speaking_file)
        except Exception as e:
            logger.debug(f"Error reading .speaking file: {e}")
            pass
    return False


class VoiceProcessor:
    """Background voice command processor"""

    # Wake words that trigger processing (same as original main_assistant.py)
    WAKE_WORDS = [
        "phoenix",
        "finish",
        "feelings",
        "feeling",
        "friend",
        "buddy",
        "love",
        "baby",
    ]

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
                    logger.info("Faster-Whisper loaded on GPU - Ultra-fast transcription!")
                else:
                    logger.info("CUDA not available, loading Faster-Whisper on CPU...")
                    self.whisper_model = WhisperModel(
                        "small", device="cpu", compute_type="int8"
                    )
                    logger.info("Faster-Whisper loaded on CPU - Ready for transcription!")
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
        print(f"[{tag}] {message}", flush=True)

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

            # Transcribe with Faster-Whisper (optimized for speed)
            segments, info = self.whisper_model.transcribe(
                audio_float,
                language="en",
                beam_size=1,  # Faster than beam_size=5, minimal accuracy loss
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=int(self.MIN_SILENCE_DURATION * 1000),
                    threshold=0.3,
                ),
            )

            # Combine all segments
            transcription = " ".join([segment.text for segment in segments]).strip()

            if transcription:
                # Show what was heard using TUI with accurate timestamp
                user_said(transcription, timestamp)
                self._runtime_trace("HEARD", transcription)
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
            if is_speaking():
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
                        logger.debug(f"Cleared {cleared} chunks from queue during speaking")
                except:
                    pass
                return
            
            logger.debug(f"Processing chunk: {chunk.duration:.2f}s")
            
            # Get timestamp from when audio was captured (for accurate timing)
            chunk_timestamp = datetime.fromtimestamp(chunk.timestamp).strftime("%H:%M:%S")

            # Step 1: Transcribe audio chunk with Whisper
            transcription = self.transcribe_audio(chunk, chunk_timestamp)

            # Empty transcription = reset follow-up mode
            if not transcription:
                self.loop = False
                self.chunks_processed += 1
                listening()  # Back to listening
                return

            # Step 2: Wake word logic
            has_wake = self.has_wake_word(transcription)

            if has_wake and not self.loop:
                # Wake word detected, process command
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
                logger.debug(f"Ignored (no wake word): '{transcription}'")
                self._runtime_trace("IGNORED", "no wake word")
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
