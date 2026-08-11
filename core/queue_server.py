"""
Phoenix Queue Server - shared state for the three-process voice runtime.

Owns:
  * the audio queue  (listener -> processor)
  * the speech window (speech engine -> listener, for self-voice gating)
  * the interrupt flag (listener -> speech engine, for barge-in)
  * recent TTS text   (speech engine -> processor, for self-echo rejection)

The speech window used to be a single boolean "is Phoenix speaking".  That was
unusable for its actual job: audio is examined well after it was captured, and
a boolean read at examination time says nothing about the moment of capture.
It is now a (since, until) pair of epoch timestamps, so a frame can be judged
against the state of the world when the microphone actually recorded it.

`until` is heartbeated forward while audio plays rather than being set once at
the start.  If the speaking process dies mid-sentence the window simply expires
and the microphone reopens; a boolean flag would have wedged it shut forever.
"""

import multiprocessing as mp
from multiprocessing.managers import BaseManager, ListProxy
import logging
import os
import sys

# Ensure project root is importable in this process (required for unpickling AudioChunk)
_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("QueueServer")

# Layout of the shared speech-state array
SPEAKING_SINCE = 0
SPEAKING_UNTIL = 1
INTERRUPT_REQUESTED = 2
ECHO_OPEN = 3  # 1 = headphones (gate off), 0 = speakers (gate on), -1 = unset
SPEECH_STATE_SLOTS = 4

audio_queue = None
speech_state = None
tts_history = None


def get_queue():
    """Return the shared audio queue"""
    global audio_queue
    if audio_queue is None:
        audio_queue = mp.Queue(maxsize=10)
        logger.info("Audio queue created")
    return audio_queue


def get_speech_state():
    """
    Shared [speaking_since, speaking_until, interrupt_requested].

    A plain list behind a ListProxy, deliberately NOT mp.Value or mp.Array.
    Those get wrapped in an AutoProxy that exposes only
    ('acquire', 'get_lock', 'get_obj', 'release') -- no `.value`, no item
    assignment.  The previous `speaking_flag = mp.Value("i", 0)` therefore never
    crossed the process boundary at all: `flag.value = 1` set an attribute on
    the local proxy object, and every other process reading `.value` got an
    AttributeError that QueueManager.is_speaking() swallowed into `False`.
    Self-voice suppression was unreachable dead code for as long as it existed.

    One list rather than three scalars so a client reads the whole state in a
    single round trip over the named pipe.
    """
    global speech_state
    if speech_state is None:
        speech_state = [0.0] * SPEECH_STATE_SLOTS
        speech_state[ECHO_OPEN] = -1.0  # unset until the listener seeds it
        logger.info("Speech state created")
    return speech_state


def get_tts_history():
    """Recent things Phoenix said, newest last, for self-echo rejection."""
    global tts_history
    if tts_history is None:
        tts_history = []
        logger.info("TTS history created")
    return tts_history


class QueueManager(BaseManager):
    pass


QueueManager.register("get_audio_queue", callable=get_queue)
QueueManager.register("get_speech_state", callable=get_speech_state, proxytype=ListProxy)
QueueManager.register("get_tts_history", callable=get_tts_history, proxytype=ListProxy)


def start_queue_server(host="127.0.0.1", port=50000, authkey=b"phoenix_audio_queue"):
    """Start the queue server"""
    try:
        if sys.platform == "win32":
            address = r"\\.\pipe\phoenix_audio_queue"
            logger.info(f"Starting queue server on Named Pipe {address}")
        else:
            address = (host, port)
            logger.info(f"Starting queue server on {host}:{port}")

        manager = QueueManager(address=address, authkey=authkey)
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
