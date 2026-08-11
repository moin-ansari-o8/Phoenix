"""
One way to configure logging, used by every process.

Before this there were five, and they disagreed:

    main.py                     logs/phoenix.log          INFO
    voice_command_processor.py  bg_voice_processor.log    DEBUG   <- repo root
    continuous_listener.py      phoenix_listener.log      INFO    <- repo root
    launch_phoenix.py           phoenix_launcher.log      INFO    <- repo root
    queue_manager.py            phoenix_queue.log         INFO    <- repo root

Three consequences, all of which bit:

1. **Paths were relative**, so the file landed wherever the process happened to
   be started from. The repo root accumulated four stray .log files.
2. **The processor ran at DEBUG in production.** That is why
   bg_voice_processor.log reached 2.2 MB and why a real traceback in it was
   buried under thousands of lines of comtypes COM refcount chatter.
3. `basicConfig` is a no-op if the root logger already has handlers, so
   whichever module imported first silently won and the others were ignored.

Everything now writes into `logs/`, rotates, and takes its level from
`PHOENIX_LOG_LEVEL` (default INFO) so DEBUG is opt-in per run rather than
committed.
"""

from __future__ import annotations

import logging
import logging.handlers
import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(_BASE, "logs")

# 2 MB x 3 - enough to cover a long session, bounded so a debug run cannot fill
# the disk while nobody is watching.
MAX_BYTES = 2 * 1024 * 1024
BACKUP_COUNT = 3

_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

# Third-party loggers that emit at DEBUG and drown everything else. comtypes in
# particular logs every COM AddRef/Release, which is what made the processor log
# unreadable at the exact moment it mattered.
_NOISY = ("comtypes", "urllib3", "httpx", "httpcore", "PIL", "matplotlib", "asyncio")

_configured = set()


def setup_logging(name: str, level: str = None) -> logging.Logger:
    """
    Configure root logging for this process and return a named logger.

    `name` picks the file: setup_logging("listener") -> logs/phoenix_listener.log.
    Idempotent - calling it twice in one process does not double the handlers,
    which is what produced duplicated lines when a module was imported twice
    under different names.
    """
    if name in _configured:
        return logging.getLogger(name)

    os.makedirs(LOG_DIR, exist_ok=True)
    resolved = (level or os.environ.get("PHOENIX_LOG_LEVEL", "INFO")).upper()
    numeric = getattr(logging, resolved, logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, f"phoenix_{name}.log"),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(_FORMAT))

    root = logging.getLogger()
    # Not basicConfig: it silently does nothing when handlers already exist, so
    # in a process that imported any library which configured logging first, the
    # old calls were no-ops.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(numeric)

    for noisy in _NOISY:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured.add(name)
    return logging.getLogger(name)
