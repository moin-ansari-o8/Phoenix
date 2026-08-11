"""
Queue Manager for Phoenix Voice Assistant
Client side of core/queue_server.py - shared audio queue and speech state.
"""

from multiprocessing.managers import BaseManager
import queue
import numpy as np
import time
import logging
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass

# File-only logging
logger = logging.getLogger("QueueManager")
if not logger.handlers:
    handler = logging.FileHandler("phoenix_queue.log")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
# File-only: without this the records also reach the root logger and print into
# the chat on every single speak() call. The queue server is optional, so its
# absence must be silent.
logger.propagate = False

# Indices into the shared speech-state array (must match core/queue_server.py)
SPEAKING_SINCE = 0
SPEAKING_UNTIL = 1
INTERRUPT_REQUESTED = 2
ECHO_OPEN = 3  # 1 = headphones (gate off), 0 = speakers (gate on), -1 = unset

# How far ahead of "now" the speaking window is held while audio plays. The
# speech engine re-extends it on a heartbeat, so a crash mid-sentence releases
# the microphone after this long instead of never.
SPEAKING_HEARTBEAT_HOLD = 0.5

MAX_TTS_HISTORY = 5


@dataclass
class AudioChunk:
    """Audio chunk with metadata for processing"""

    audio_data: np.ndarray
    sample_rate: int
    timestamp: float  # when the utterance ENDED (epoch seconds)
    duration: float
    energy_level: float
    start_timestamp: float = 0.0  # when the utterance STARTED
    voiced_ms: float = 0.0  # VAD-measured speech inside the utterance
    end_reason: str = "silence"  # "silence" | "max_duration"


# Client manager to connect to queue server
class QueueClientManager(BaseManager):
    pass


# Register the remote queue and shared state getters
QueueClientManager.register("get_audio_queue")
QueueClientManager.register("get_speech_state")
QueueClientManager.register("get_tts_history")


def connect_to_queue_server(
    host="127.0.0.1",
    port=50000,
    authkey=b"phoenix_audio_queue",
    retries=6,
    retry_delay=0.5,
):
    """Connect to queue server with retries, return a dict of shared handles."""
    import sys

    if sys.platform == "win32":
        address = r"\\.\pipe\phoenix_audio_queue"
    else:
        address = (host, port)

    for attempt in range(retries):
        try:
            logger.info(
                f"Connecting to queue server at {address} (attempt {attempt+1}/{retries})..."
            )
            manager = QueueClientManager(address=address, authkey=authkey)
            manager.connect()
            handles = {
                "queue": manager.get_audio_queue(),
                "speech_state": manager.get_speech_state(),
                "tts_history": manager.get_tts_history(),
                "manager": manager,
            }
            logger.info("Connected to queue server successfully!")
            return handles
        except ConnectionRefusedError:
            if attempt < retries - 1:
                logger.warning(f"Connection refused, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    "Queue server not running! Start it with: python queue_server.py"
                )
                raise
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(f"Connection failed: {e}, retrying...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect after {retries} attempts: {e}")
                raise


class QueueManager:
    """Manages audio chunk queue and shared speech state."""

    def __init__(self, max_size: int = 10):
        """Initialize queue manager by connecting to queue server"""
        self.max_size = max_size
        handles = connect_to_queue_server()
        self.queue = handles["queue"]
        self.speech_state = handles["speech_state"]
        self.tts_history = handles["tts_history"]
        self.manager = handles["manager"]
        self._chunks_sent = 0
        self._chunks_received = 0
        self._chunks_dropped = 0
        logger.info("QueueManager initialized (connected to server)")

    # -- audio transport ---------------------------------------------------

    def send_chunk(self, audio_chunk: AudioChunk, timeout: float = 0.1) -> bool:
        """Send audio chunk to queue (non-blocking)"""
        try:
            self.queue.put(audio_chunk, block=True, timeout=timeout)
            self._chunks_sent += 1
            logger.debug(f"Chunk sent (total: {self._chunks_sent})")
            return True
        except queue.Full:
            self._chunks_dropped += 1
            logger.warning(f"Queue full! Chunk dropped.")
            return False
        except Exception as e:
            logger.error(f"Error sending chunk: {e}")
            return False

    def receive_chunk(self, timeout: float = 0.1) -> Optional[AudioChunk]:
        """Receive audio chunk from queue (blocking with timeout)"""
        try:
            chunk = self.queue.get(block=True, timeout=timeout)
            self._chunks_received += 1
            logger.debug(f"Chunk received (total: {self._chunks_received})")
            return chunk
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error receiving chunk: {e}")
            return None

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        try:
            return self.queue.empty()
        except Exception:
            return True

    def get_size(self) -> int:
        """Get approximate queue size"""
        try:
            return self.queue.qsize()
        except Exception:
            return 0

    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        return {
            "chunks_sent": self._chunks_sent,
            "chunks_received": self._chunks_received,
            "chunks_dropped": self._chunks_dropped,
            "current_size": self.get_size(),
            "max_size": self.max_size,
        }

    def clear(self):
        """Clear all items from queue"""
        cleared = 0
        try:
            while not self.queue.empty():
                self.queue.get_nowait()
                cleared += 1
        except Exception:
            pass
        if cleared > 0:
            logger.info(f"Cleared {cleared} chunks from queue")

    # -- speech window (self-voice gating) ---------------------------------

    def begin_speaking(self, hold: float = SPEAKING_HEARTBEAT_HOLD):
        """Open the speaking window. Call right before audio starts playing."""
        now = time.time()
        try:
            self.speech_state[SPEAKING_SINCE] = now
            self.speech_state[SPEAKING_UNTIL] = now + hold
            self.speech_state[INTERRUPT_REQUESTED] = 0.0
        except Exception as e:
            logger.error(f"Failed to open speaking window: {e}")

    def heartbeat_speaking(self, hold: float = SPEAKING_HEARTBEAT_HOLD):
        """Extend the speaking window while audio is still playing."""
        try:
            self.speech_state[SPEAKING_UNTIL] = time.time() + hold
        except Exception as e:
            logger.debug(f"Speaking heartbeat failed: {e}")

    def end_speaking(self, tail: float = 0.0):
        """
        Close the speaking window.

        `since` is deliberately left set so the listener can still judge frames
        captured during playback that it has not drained yet.
        """
        try:
            self.speech_state[SPEAKING_UNTIL] = time.time() + tail
        except Exception as e:
            logger.error(f"Failed to close speaking window: {e}")

    def get_speech_window(self) -> Tuple[float, float]:
        """Return (speaking_since, speaking_until) in epoch seconds."""
        try:
            state = self.speech_state[:]
            return float(state[SPEAKING_SINCE]), float(state[SPEAKING_UNTIL])
        except Exception:
            return 0.0, 0.0

    def set_speaking(self, is_speaking: bool):
        """Compatibility wrapper over the speaking window."""
        if is_speaking:
            self.begin_speaking()
        else:
            self.end_speaking()

    def is_speaking(self) -> bool:
        """Check if Phoenix is currently speaking"""
        since, until = self.get_speech_window()
        return since > 0.0 and time.time() <= until

    # -- barge-in ----------------------------------------------------------

    def request_interrupt(self):
        """Ask the speech engine to stop talking immediately."""
        try:
            self.speech_state[INTERRUPT_REQUESTED] = 1.0
            logger.info("Interrupt requested")
        except Exception as e:
            logger.error(f"Failed to request interrupt: {e}")

    def interrupt_requested(self) -> bool:
        try:
            return self.speech_state[INTERRUPT_REQUESTED] >= 1.0
        except Exception:
            return False

    def clear_interrupt(self):
        try:
            self.speech_state[INTERRUPT_REQUESTED] = 0.0
        except Exception:
            pass

    # -- echo mode (speakers vs headphones) --------------------------------

    def set_echo_open(self, is_open: bool):
        """
        Switch between headphone mode (gate off, barge-in on) and speaker mode.

        Kept in shared state rather than read from config per process, so
        saying "headphone mode" takes effect in the running listener instead of
        needing a restart.
        """
        try:
            self.speech_state[ECHO_OPEN] = 1.0 if is_open else 0.0
        except Exception as e:
            logger.error(f"Failed to set echo mode: {e}")

    def is_echo_open(self) -> Optional[bool]:
        """True (headphones) / False (speakers) / None if nobody has set it."""
        try:
            value = self.speech_state[ECHO_OPEN]
        except Exception:
            return None
        if value < 0:
            return None
        return value >= 1.0

    # -- TTS history (self-echo rejection) ---------------------------------

    def remember_tts(self, text: str):
        """Record something Phoenix said so the processor can spot echoes."""
        if not text:
            return
        try:
            self.tts_history.append(text)
            overflow = len(self.tts_history) - MAX_TTS_HISTORY
            for _ in range(max(0, overflow)):
                self.tts_history.pop(0)
        except Exception as e:
            logger.debug(f"Failed to record TTS text: {e}")

    def recent_tts(self) -> List[str]:
        try:
            return list(self.tts_history)
        except Exception:
            return []

    def close(self):
        """Close connection"""
        logger.info("Queue connection closed")


def create_audio_chunk(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    energy_level: float = 0.0,
    start_timestamp: float = 0.0,
    end_timestamp: float = 0.0,
    voiced_ms: float = 0.0,
    end_reason: str = "silence",
) -> AudioChunk:
    """Helper function to create AudioChunk with automatic metadata"""
    duration = len(audio_data) / sample_rate
    timestamp = end_timestamp or time.time()
    return AudioChunk(
        audio_data=audio_data,
        sample_rate=sample_rate,
        timestamp=timestamp,
        duration=duration,
        energy_level=energy_level,
        start_timestamp=start_timestamp or (timestamp - duration),
        voiced_ms=voiced_ms,
        end_reason=end_reason,
    )


if __name__ == "__main__":
    print("=== QueueManager Test ===")
    print("Make sure queue_server.py is running first!")
    print()

    try:
        qm = QueueManager(max_size=5)

        test_audio = np.random.randn(16000).astype(np.float32)
        chunk = create_audio_chunk(test_audio, sample_rate=16000, energy_level=150.0)
        print(f"Created chunk: duration={chunk.duration:.2f}s")

        success = qm.send_chunk(chunk)
        print(f"Send: {'OK' if success else 'FAILED'}")

        received = qm.receive_chunk(timeout=1.0)
        if received:
            print(f"Receive: OK (duration={received.duration:.2f}s)")
        else:
            print("Receive: No chunk (timeout)")

        qm.begin_speaking()
        print(f"Speaking window open: is_speaking={qm.is_speaking()}")
        qm.end_speaking()
        print(f"Speaking window closed: is_speaking={qm.is_speaking()}")

        print("\nStats:", qm.get_stats())
        qm.close()
        print("Test complete!")

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure queue_server.py is running!")
