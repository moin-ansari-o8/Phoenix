"""
Two-turn confirmation for actions you cannot undo.

Phoenix's input is *speech from a room*. Whisper mishears, other people talk,
the TV talks. Meanwhile `shutD()` runs `shutdown /s` and `close_all_py()` runs
`taskkill /F /IM python.exe` -- and both were reachable from a single utterance
with no confirmation at all. One mistranscription cost you every unsaved file
on the machine.

So destructive tags are parked instead of executed. Phoenix asks, the next
utterance answers, and only an explicit yes runs it:

    user     "phoenix shut down the pc"
    phoenix  "That will shut down the PC. Should I go ahead?"
    user     "yes"                        -> runs
    user     "no" / anything else         -> cancelled

Design notes:

- **Expires.** A pending action is a loaded gun; it holds for
  `timeout_seconds` (default 30) and then lapses. Deadline, not a flag - the
  same reason as WakeGate, and the failure it prevents is worse here: a "yes"
  to some unrelated question ten minutes later must never shut the PC down.
- **One slot.** A second destructive request replaces the first rather than
  queueing, so "shut down... no wait, restart" cannot leave a shutdown armed.
- **Cancel wins ties.** Anything that is not clearly affirmative is treated as
  a refusal. Under mishearing, a false cancel costs a repeated sentence and a
  false confirm costs the session.

Turn it off with `confirm_destructive: false` in core/config.json.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Callable, Optional

# Tags that cannot be undone. Names match command_processor's action_map.
DESTRUCTIVE_TAGS = {
    "pcshutdown": "shut down the PC",
    "pcrestart": "restart the PC",
    "pchibernate": "hibernate the PC",
    "pcsleep": "put the PC to sleep",
    "closeallpy": "close every Python process",
    "closebgpy": "close the background Python processes",
    "phnxrestart": "restart Phoenix",
}

# Bare, unambiguous agreement only. "yes please shut it down" is fine; a
# sentence that merely CONTAINS "yes" is not, because the utterance after a
# confirmation prompt is far more likely to be unrelated speech than an answer.
_AFFIRMATIVE = re.compile(
    r"^\W*(yes|yeah|yep|yup|yaa+|ha+n|sure|ok|okay|confirm(ed)?|"
    r"go ahead|do it|proceed|affirmative|please do)\b",
    re.IGNORECASE,
)
_NEGATIVE = re.compile(
    r"^\W*(no|nope|nah|cancel|stop|don'?t|do not|abort|never ?mind|wait)\b",
    re.IGNORECASE,
)


@dataclass
class Pending:
    tag: str
    query: str
    description: str
    expires_at: float


class ConfirmationGate:
    """Holds at most one armed destructive action."""

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        enabled: bool = True,
        time_source: Callable[[], float] = time.time,
    ):
        self.timeout_seconds = float(timeout_seconds)
        self.enabled = bool(enabled)
        self._now = time_source
        self._pending: Optional[Pending] = None

    # ------------------------------------------------------------------ state

    @property
    def pending(self) -> Optional[Pending]:
        """The armed action, or None if there is none or it has lapsed."""
        if self._pending is None:
            return None
        if self._now() >= self._pending.expires_at:
            self._pending = None
        return self._pending

    @property
    def is_armed(self) -> bool:
        return self.pending is not None

    def clear(self):
        self._pending = None

    # ----------------------------------------------------------------- arming

    def needs_confirmation(self, tag: str) -> bool:
        return self.enabled and tag in DESTRUCTIVE_TAGS

    def arm(self, tag: str, query: str = "") -> str:
        """Park `tag` and return the question to ask. Replaces any prior arm."""
        description = DESTRUCTIVE_TAGS.get(tag, f"run {tag}")
        self._pending = Pending(
            tag=tag,
            query=query,
            description=description,
            expires_at=self._now() + self.timeout_seconds,
        )
        return f"That will {description}. Should I go ahead?"

    # --------------------------------------------------------------- resolving

    def resolve(self, text: str):
        """
        Interpret `text` as an answer to the pending question.

        Returns (outcome, tag, query, spoken):
          "none"      nothing was armed - `text` is an ordinary command
          "confirmed" caller should execute `tag`
          "cancelled" caller should not
        """
        current = self.pending
        if current is None:
            return ("none", None, "", None)

        answer = (text or "").strip()

        if _AFFIRMATIVE.match(answer):
            self._pending = None
            return ("confirmed", current.tag, current.query, None)

        if _NEGATIVE.match(answer):
            self._pending = None
            return ("cancelled", current.tag, current.query,
                    f"Okay, I won't {current.description}.")

        # Neither. Treat as a refusal AND let the utterance be handled as a
        # normal command - the user has clearly moved on, and leaving the
        # action armed would let a later stray "yes" fire it.
        self._pending = None
        return ("cancelled", current.tag, current.query, None)
