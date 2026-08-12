"""
One structured line per event, instead of tags parsed by regex.

The TUI reads the voice processor's stdout. Until now that channel carried two
different things - trace events meant for the UI, and any `print()` anywhere in
~3,500 lines of action code - and the UI told them apart by string matching:
`startswith("[VOICE_STATE]")`, plus a heuristic that dropped any line containing
`"|"` or `"---"`. Two consequences:

1. A stray print could be mistaken for a trace, or corrupt the status line.
2. `manager.py` grew a *second*, subtly different copy of the same parser, and
   the two drifted - one matched emoji prefixes that had already been removed
   from the emitting side, so it had silently stopped matching anything.

Traces now carry a sentinel prefix and a JSON body:

    @@PHX@@{"event": "heard", "text": "what time is it"}

Anything without the prefix is, by definition, not a trace, so ordinary output
can never be misread as one. Fields are named rather than positional, so adding
one does not require touching every parser.

The prefix is deliberately ugly: it must never occur in ordinary speech,
transcripts, or a traceback.
"""

from __future__ import annotations

import json
import sys
from typing import Optional

PREFIX = "@@PHX@@"


def emit(event: str, stream=None, **fields) -> None:
    """
    Write one trace line.

    Never raises: a UI event failing to serialise must not take down the
    process that was only trying to describe what it was doing.
    """
    stream = stream or sys.stdout
    try:
        payload = {"event": event}
        payload.update({k: v for k, v in fields.items() if v is not None})
        line = PREFIX + json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        line = PREFIX + json.dumps({"event": event})
    try:
        stream.write("\n" + line + "\n")
        stream.flush()
    except Exception:
        pass


def parse(line: str) -> Optional[dict]:
    """
    Decode a trace line, or None if this is ordinary output.

    Returning None for anything unrecognised is the whole point: the caller can
    then treat non-traces as plain text without guessing.
    """
    if not line:
        return None
    stripped = line.strip()
    index = stripped.find(PREFIX)
    if index < 0:
        return None
    try:
        decoded = json.loads(stripped[index + len(PREFIX):])
    except ValueError:
        return None
    if not isinstance(decoded, dict) or "event" not in decoded:
        return None
    return decoded
