"""
Phoenix Listener - Continuous Audio Capture
Sends audio chunks to background processor via queue
"""

import sys
import os
import time
import signal
import tkinter as tk
import logging
import numpy as np
import pyaudio

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Utils.limbs.queue_manager import QueueManager, create_audio_chunk
from Utils.limbs.assistant_io import VoiceAssistantGUI
from Utils.limbs.console_ui import (
    listening,
    detected,
    processing,
    print_block,
    get_timestamp,
)

# VAD (Voice Activity Detection) for continuous listening
try:
    import webrtcvad

    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False

# Setup logging (file only)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("phoenix_listener.log")],
)
logger = logging.getLogger("PhoenixListener")

# Remove any console handlers that may have been added
for handler in logger.handlers[:]:
    if isinstance(handler, logging.StreamHandler) and handler.stream in (
        sys.stdout,
        sys.stderr,
    ):
        logger.removeHandler(handler)

# Also remove from root logger
root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    if isinstance(handler, logging.StreamHandler) and handler.stream in (
        sys.stdout,
        sys.stderr,
    ):
        root_logger.removeHandler(handler)


class ContinuousListener:
    """Continuous audio listener that sends chunks to processor"""

    def __init__(self, queue_manager):
        """
        Initialize continuous listener

        Args:
            queue_manager: QueueManager instance for sending chunks
        """
        self.queue_manager = queue_manager
        self.running = False
        self.chunks_sent = 0

        logger.info("Initializing ContinuousListener...")

        # Audio settings for continuous listening
        self.SAMPLE_RATE = 16000
        self.CHUNK_SIZE = 1024
        self.CHANNELS = 1

        # VAD settings (optimized for faster response)
        self.MIN_SILENCE_DURATION = 0.6  # Seconds of silence to trigger processing
        self.MIN_SPEECH_DURATION = 0.3  # Minimum speech duration
        self.ENERGY_THRESHOLD = 150  # RMS energy threshold (raised for fan noise)
        self.SPEECH_CONFIRMATION_CHUNKS = (
            3  # Require N consecutive chunks to confirm speech
        )
        self.MAX_SPEECH_DURATION = 30.0  # Max seconds before auto-processing

        # State management
        self.audio_buffer = []
        self.is_speaking = False
        self.silence_start_time = None
        self.speech_start_time = None
        self.consecutive_speech_chunks = 0
        self.consecutive_silence_chunks = 0

        # Initialize VAD
        self.vad = None
        if VAD_AVAILABLE:
            try:
                self.vad = webrtcvad.Vad()
                self.vad.set_mode(3)  # Most aggressive (human voice only)
                logger.info("VAD initialized (mode 3)")
            except Exception as e:
                logger.warning(f"VAD failed to initialize: {e}")
                self.vad = None
        else:
            logger.warning("VAD not available")

        # Initialize GUI (optional, for visual feedback)
        self.root = tk.Tk()
        self.gui = VoiceAssistantGUI(self.root)

        logger.info("ContinuousListener initialized successfully")

    def _runtime_trace(self, tag: str, message: str):
        """Emit line-based runtime traces for the manager parser."""
        print(f"[{tag}] {message}", flush=True)

    def _detect_speech(self, audio_chunk):
        """Detect if audio chunk contains speech using VAD and/or energy"""
        # Energy-based detection
        if len(audio_chunk) > 0:
            rms_energy = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
            energy_detected = rms_energy > self.ENERGY_THRESHOLD
        else:
            energy_detected = False

        # VAD detection
        vad_detected = False
        if self.vad is not None:
            try:
                audio_bytes = audio_chunk.tobytes()
                vad_detected = self.vad.is_speech(audio_bytes, self.SAMPLE_RATE)
            except Exception:
                pass

        # Combine both detections (OR logic)
        return energy_detected or vad_detected

    def _calculate_energy(self, audio_chunk):
        """Calculate RMS energy of audio chunk"""
        if len(audio_chunk) > 0:
            return np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
        return 0.0

    def _send_to_processor(self, audio_buffer):
        """
        Send audio buffer to processor via queue

        Args:
            audio_buffer: List of audio chunks (numpy arrays)
        """
        try:
            # Combine all chunks into single array
            audio_array = np.concatenate(audio_buffer)

            # Calculate energy
            energy_level = self._calculate_energy(audio_array)

            # Create audio chunk
            chunk = create_audio_chunk(
                audio_data=audio_array,
                sample_rate=self.SAMPLE_RATE,
                energy_level=energy_level,
            )

            # Send to queue
            success = self.queue_manager.send_chunk(chunk, timeout=0.5)

            if success:
                self.chunks_sent += 1
                logger.info(
                    f"Chunk sent: {chunk.duration:.2f}s, energy: {energy_level:.1f}"
                )
            else:
                logger.warning("Queue full - chunk dropped")

        except Exception as e:
            logger.error(f"Error sending chunk: {e}", exc_info=True)

    def listen_continuously(self):
        """Main continuous listening loop"""
        logger.info("Starting continuous listening...")
        self.running = True

        try:
            # Initialize PyAudio
            audio = pyaudio.PyAudio()
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK_SIZE,
            )

            self.gui.show_listen_image()
            listening()  # TUI status
            self._runtime_trace("VOICE_STATE", "listening")

            # Reset state
            self.audio_buffer = []
            self.is_speaking = False
            self.silence_start_time = None
            self.speech_start_time = None
            self.consecutive_speech_chunks = 0
            self.consecutive_silence_chunks = 0

            chunk_count = 0

            # Continuous listening loop
            while self.running:
                # Check if Phoenix is speaking - PAUSE listening if so
                if self.queue_manager.is_speaking():
                    # Phoenix is speaking, skip audio capture
                    print_block("[DEBUG] Listener: Phoenix speaking - SKIPPING audio")
                    stream.read(
                        self.CHUNK_SIZE, exception_on_overflow=False
                    )  # Drain buffer
                    time.sleep(0.05)  # Brief sleep
                    continue

                # Read audio chunk
                audio_data = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                audio_chunk = np.frombuffer(audio_data, dtype=np.int16)
                chunk_count += 1

                # Detect speech
                has_speech = self._detect_speech(audio_chunk)
                current_time = time.time()

                # Update consecutive counters
                if has_speech:
                    self.consecutive_speech_chunks += 1
                    self.consecutive_silence_chunks = 0
                else:
                    self.consecutive_silence_chunks += 1
                    self.consecutive_speech_chunks = 0

                # Require multiple consecutive chunks to confirm speech/silence
                confirmed_speech = (
                    self.consecutive_speech_chunks >= self.SPEECH_CONFIRMATION_CHUNKS
                )
                confirmed_silence = (
                    self.consecutive_silence_chunks >= self.SPEECH_CONFIRMATION_CHUNKS
                )

                if confirmed_speech:
                    # Confirmed speech detected
                    if not self.is_speaking:
                        # Speech just started
                        detected()  # TUI status
                        self._runtime_trace("VOICE_STATE", "detected")
                        logger.debug(f"Speech CONFIRMED (chunk {chunk_count})")
                        self.is_speaking = True
                        self.speech_start_time = current_time
                        self.audio_buffer = []
                        self.silence_start_time = None

                    # Add to buffer
                    self.audio_buffer.append(audio_chunk)

                    # Check if speech duration exceeded max
                    speech_duration_so_far = current_time - self.speech_start_time
                    if speech_duration_so_far >= self.MAX_SPEECH_DURATION:
                        processing()  # TUI status
                        self._runtime_trace("VOICE_STATE", "processing")
                        self.gui.show_recognize_image()

                        # Send to processor
                        self._send_to_processor(self.audio_buffer)

                        # Reset state
                        self.audio_buffer = []
                        self.is_speaking = False
                        self.silence_start_time = None
                        self.speech_start_time = None
                        self.gui.hide_recognize_image()
                        self.gui.show_listen_image()
                        listening()  # TUI status
                        self._runtime_trace("VOICE_STATE", "listening")

                elif confirmed_silence and self.is_speaking:
                    # Confirmed silence during speech
                    if self.silence_start_time is None:
                        self.silence_start_time = current_time

                    # Continue buffering
                    self.audio_buffer.append(audio_chunk)

                    # Check if silence duration exceeded threshold
                    silence_duration = current_time - self.silence_start_time
                    if silence_duration >= self.MIN_SILENCE_DURATION:
                        # Check if speech is long enough
                        speech_duration = (
                            len(self.audio_buffer) * self.CHUNK_SIZE / self.SAMPLE_RATE
                        )

                        if speech_duration >= self.MIN_SPEECH_DURATION:
                            processing()  # TUI status
                            self._runtime_trace("VOICE_STATE", "processing")
                            self.gui.show_recognize_image()

                            # Send to processor
                            self._send_to_processor(self.audio_buffer)

                            # Reset state
                            self.audio_buffer = []
                            self.is_speaking = False
                            self.silence_start_time = None
                            self.speech_start_time = None
                            self.gui.hide_recognize_image()
                            self.gui.show_listen_image()
                            # Note: listening() will be called after processor shows output
                            self._runtime_trace("VOICE_STATE", "listening")
                        else:
                            # Too short, ignore
                            self.audio_buffer = []
                            self.is_speaking = False
                            self.silence_start_time = None
                            self.speech_start_time = None
                            listening()  # Back to listening
                            self._runtime_trace("VOICE_STATE", "listening")

                elif self.is_speaking:
                    # Transitional state - buffer audio but don't change state
                    self.audio_buffer.append(audio_chunk)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"Error in continuous listening: {e}", exc_info=True)
        finally:
            # Cleanup
            try:
                stream.stop_stream()
                stream.close()
                audio.terminate()
            except:
                pass
            self.gui.hide_listen_image()
            logger.info("Continuous listening stopped")

    def get_stats(self):
        """Get listener statistics"""
        return {
            "chunks_sent": self.chunks_sent,
            "queue_stats": self.queue_manager.get_stats(),
        }

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down ContinuousListener...")
        self.running = False

        # Print statistics
        stats = self.get_stats()
        logger.info("=== Listener Statistics ===")
        logger.info(f"  Chunks sent: {stats['chunks_sent']}")
        logger.info(f"  Queue stats: {stats['queue_stats']}")

        # Cleanup
        try:
            self.root.destroy()
        except:
            pass

        logger.info("Shutdown complete")


class ListenerManager:
    """Manages the listener lifecycle"""

    def __init__(self):
        self.listener = None
        self.queue_manager = None

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        if self.listener:
            self.listener.shutdown()
        sys.exit(0)

    def start(self):
        """Start the listener"""
        try:
            logger.info("PHOENIX CONTINUOUS LISTENER STARTING")

            # Initialize queue manager
            self.queue_manager = QueueManager(max_size=10)

            # Initialize listener
            self.listener = ContinuousListener(self.queue_manager)

            # Start listening
            self.listener.listen_continuously()

        except Exception as e:
            logger.critical(
                f"CRITICAL ERROR: Listener failed to start: {e}", exc_info=True
            )
            sys.exit(1)
        finally:
            if self.listener:
                self.listener.shutdown()


if __name__ == "__main__":
    try:
        manager = ListenerManager()
        manager.start()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
