"""
Queue Manager for Phoenix Voice Assistant
Connects to queue_server.py for cross-process queue sharing
"""

from multiprocessing.managers import BaseManager
import queue
import numpy as np
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

# File-only logging
logger = logging.getLogger("QueueManager")
if not logger.handlers:
    handler = logging.FileHandler("phoenix_queue.log")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


@dataclass
class AudioChunk:
    """Audio chunk with metadata for processing"""

    audio_data: np.ndarray
    sample_rate: int
    timestamp: float
    duration: float
    energy_level: float


# Client manager to connect to queue server
class QueueClientManager(BaseManager):
    pass


# Register the remote queue and speaking flag getters
QueueClientManager.register("get_audio_queue")
QueueClientManager.register("get_speaking_flag")


def connect_to_queue_server(
    host="127.0.0.1",
    port=50000,
    authkey=b"phoenix_audio_queue",
    retries=1,
    retry_delay=0,
):
    """Connect to queue server with retries, return (queue, speaking_flag, manager)"""
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
            queue_obj = manager.get_audio_queue()
            speaking_flag = manager.get_speaking_flag()
            logger.info("Connected to queue server successfully!")
            return queue_obj, speaking_flag, manager
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
    """Manages audio chunk queue - connects to queue_server.py"""

    def __init__(self, max_size: int = 10):
        """Initialize queue manager by connecting to queue server"""
        self.max_size = max_size
        self.queue, self.speaking_flag, self.manager = connect_to_queue_server()
        self._chunks_sent = 0
        self._chunks_received = 0
        self._chunks_dropped = 0
        logger.info("QueueManager initialized (connected to server)")

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

    def set_speaking(self, is_speaking: bool):
        """Set the speaking flag (True = Phoenix is speaking, pause listener)"""
        try:
            self.speaking_flag.value = 1 if is_speaking else 0
            logger.debug(f"Speaking flag set to: {is_speaking}")
        except Exception as e:
            logger.error(f"Failed to set speaking flag: {e}")

    def is_speaking(self) -> bool:
        """Check if Phoenix is currently speaking"""
        try:
            return self.speaking_flag.value == 1
        except Exception:
            return False

    def close(self):
        """Close connection"""
        logger.info("Queue connection closed")


def create_audio_chunk(
    audio_data: np.ndarray, sample_rate: int = 16000, energy_level: float = 0.0
) -> AudioChunk:
    """Helper function to create AudioChunk with automatic metadata"""
    timestamp = time.time()
    duration = len(audio_data) / sample_rate
    return AudioChunk(
        audio_data=audio_data,
        sample_rate=sample_rate,
        timestamp=timestamp,
        duration=duration,
        energy_level=energy_level,
    )


if __name__ == "__main__":
    print("=== QueueManager Test ===")
    print("Make sure queue_server.py is running first!")
    print()

    try:
        qm = QueueManager(max_size=5)

        # Create test chunk
        test_audio = np.random.randn(16000).astype(np.float32)
        chunk = create_audio_chunk(test_audio, sample_rate=16000, energy_level=150.0)

        print(f"Created chunk: duration={chunk.duration:.2f}s")

        # Test send
        success = qm.send_chunk(chunk)
        print(f"Send: {'OK' if success else 'FAILED'}")

        # Test receive
        received = qm.receive_chunk(timeout=1.0)
        if received:
            print(f"Receive: OK (duration={received.duration:.2f}s)")
        else:
            print("Receive: No chunk (timeout)")

        print("\nStats:", qm.get_stats())
        qm.close()
        print("Test complete!")

    except Exception as e:
        print(f"Error: {e}")
        print("Make sure queue_server.py is running!")
