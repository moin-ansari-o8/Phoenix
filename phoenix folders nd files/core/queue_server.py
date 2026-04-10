"""
Phoenix Queue Server - Shared queue server for IPC
Both listener and processor connect to this to share audio chunks
Also manages speaking state for self-voice suppression
"""

import multiprocessing as mp
from multiprocessing.managers import BaseManager
import time
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("QueueServer")

# Shared queue and speaking flag
audio_queue = None
speaking_flag = None


def get_queue():
    """Return the shared audio queue"""
    global audio_queue
    if audio_queue is None:
        audio_queue = mp.Queue(maxsize=10)
        logger.info("Audio queue created")
    return audio_queue


def get_speaking_flag():
    """Return the shared speaking flag (multiprocessing Value)"""
    global speaking_flag
    if speaking_flag is None:
        speaking_flag = mp.Value('i', 0)  # 0 = not speaking, 1 = speaking
        logger.info("Speaking flag created")
    return speaking_flag


class QueueManager(BaseManager):
    pass


# Register the queue and speaking flag getters
QueueManager.register("get_audio_queue", callable=get_queue)
QueueManager.register("get_speaking_flag", callable=get_speaking_flag)


def start_queue_server(host="127.0.0.1", port=50000, authkey=b"phoenix_audio_queue"):
    """Start the queue server"""
    try:
        logger.info(f"Starting queue server on {host}:{port}")
        manager = QueueManager(address=(host, port), authkey=authkey)
        server = manager.get_server()
        logger.info("Queue server ready!")
        logger.info("Listener and processor can now connect...")
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Queue server stopped")
    except Exception as e:
        logger.error(f"Queue server error: {e}", exc_info=True)


if __name__ == "__main__":
    start_queue_server()
