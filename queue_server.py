"""
Phoenix Queue Server - Shared queue server for IPC
Both listener and processor connect to this to share audio chunks
"""

import multiprocessing as mp
from multiprocessing.managers import BaseManager
import time
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("QueueServer")

# Shared queue
audio_queue = None


def get_queue():
    """Return the shared audio queue"""
    global audio_queue
    if audio_queue is None:
        audio_queue = mp.Queue(maxsize=10)
        logger.info("Audio queue created")
    return audio_queue


class QueueManager(BaseManager):
    pass


# Register the queue getter
QueueManager.register("get_audio_queue", callable=get_queue)


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
