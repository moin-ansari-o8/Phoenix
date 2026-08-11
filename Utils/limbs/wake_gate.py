"""
Wake gate — decides whether an utterance is addressed to Phoenix.

Phoenix boots DORMANT: it transcribes everything it hears but answers nothing.
Saying a wake word anywhere in a sentence wakes it AND answers that same
sentence. It then stays AWAKE, so follow-ups need no wake word, and falls back
to DORMANT after a configurable idle window.

                wake word matched (anywhere in the sentence)
    DORMANT ───────────────────────────────────────────────► AWAKE
       ▲       answers THAT sentence, wake word stripped       │
       │                                                       │
       └───────────────────────────────────────────────────────┘
                    now() >= awake_until   (idle window)


Two defects in the previous implementation drove this design.

1. Matching was `any(word in text_lower for word in WAKE_WORDS)` — a naive
   substring test. The profile contains "yo", and `"yo" in "you"` is True, so
   any sentence containing "you" or "your" passed the gate. That is most
   sentences, which is why Phoenix appeared to answer everything and the
   IGNORED_HEARD branch was close to unreachable. Matching is now a
   word-boundary regex.

2. AWAKE was a bool (`self.loop`) set from `result is not False`, and
   `PhoenixAssistant.main()` always returns True. So it latched on at the first
   wake word and never cleared. It is now a DEADLINE, not a flag:
   `is_awake` is `now() < _awake_until`. A deadline cannot latch, because only
   an arriving utterance can push it forward — silence expires it by
   construction. This is the same reasoning as the speaking_since/until window
   in queue_server.py, and for the same reason: a boolean cannot express "was
   this still true a moment ago".

Wake words come from `core/config.json -> profile.<active>.wake_words` and are
never hardcoded here, so switching profile switches the wake words with it.

This module is deliberately pure: no config import, no clock of its own that
cannot be replaced, no I/O. `time_source` is injectable so the state machine is
testable without sleeping. See tests/test_wake_gate.py.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

# Wake words are stripped before routing, except where the wake word is acting
# as a noun modifier rather than an address. "open phoenix folder" names a
# directory; stripping it there would route "open folder".
PROTECTED_FOLLOWERS = ("folder",)

# Leading punctuation and conjunctions left behind after a wake word is cut out
# of the front of a sentence: "Phoenix, turn it down" -> ", turn it down".
_LEADING_JUNK = re.compile(r"^[\s,.\-;:!?]+")
_COLLAPSE_SPACE = re.compile(r"\s{2,}")


@dataclass(frozen=True)
class WakeDecision:
    """What the processor should do with one transcript."""

    # "respond"     - route `query` and speak the answer
    # "acknowledge" - the user said only the wake word; wake up, no query to run
    # "ignore"      - dormant and not addressed; log it, do nothing
    action: str
    query: str = ""
    # "wake" (explicitly addressed) or "followup" (already awake). Only
    # meaningful when action == "respond".
    trigger: str = ""
    matched: str = ""

    @property
    def should_respond(self) -> bool:
        return self.action == "respond"


class WakeGate:
    """
    Dormant/awake state machine for one voice processor.

    Not thread-safe: it is driven from a single processing loop. If that ever
    changes, the deadline is a plain float and a lock around evaluate/refresh
    is enough.
    """

    def __init__(
        self,
        wake_words: Iterable[str],
        followup_window_seconds: float = 30.0,
        time_source: Callable[[], float] = time.time,
    ):
        self._now = time_source
        self.followup_window = float(followup_window_seconds)

        # Longest first so "hey phoenix" wins over "phoenix" — Python's regex
        # alternation is first-match, not longest-match, so without this the
        # bare "phoenix" branch would match and leave a dangling "hey".
        cleaned = sorted(
            {w.strip().lower() for w in wake_words if w and w.strip()},
            key=len,
            reverse=True,
        )
        self.wake_words = cleaned

        if cleaned:
            alternation = "|".join(re.escape(w) for w in cleaned)
            guard = "".join(rf"(?! {f})" for f in PROTECTED_FOLLOWERS)
            self._wake_re: Optional[re.Pattern] = re.compile(
                rf"\b({alternation})\b{guard}", re.IGNORECASE
            )
        else:
            # No wake words configured. Match nothing rather than everything —
            # a config typo should make Phoenix quiet, not permanently open.
            self._wake_re = None

        self._awake_until = 0.0

    # ------------------------------------------------------------------ state

    @property
    def is_awake(self) -> bool:
        return self._now() < self._awake_until

    @property
    def seconds_remaining(self) -> float:
        return max(0.0, self._awake_until - self._now())

    def refresh(self) -> None:
        """Extend the awake window. Call after a turn Phoenix actually answered."""
        self._awake_until = self._now() + self.followup_window

    def sleep(self) -> None:
        """Force dormant immediately."""
        self._awake_until = 0.0

    # ----------------------------------------------------------- wake matching

    def find_wake(self, text: str) -> Optional[str]:
        """Return the wake word found in `text`, or None."""
        if not text or self._wake_re is None:
            return None
        match = self._wake_re.search(text)
        return match.group(1).lower() if match else None

    def strip_wake(self, text: str) -> str:
        """
        Remove wake-word occurrences and tidy what is left.

        Every occurrence is removed, not just the first: "phoenix, phoenix turn
        it off" should route "turn it off". Occurrences protected by
        PROTECTED_FOLLOWERS are preserved by the regex itself.
        """
        if not text or self._wake_re is None:
            return text.strip()
        stripped = self._wake_re.sub(" ", text)
        stripped = _LEADING_JUNK.sub("", stripped)
        stripped = _COLLAPSE_SPACE.sub(" ", stripped)
        return stripped.strip()

    # ------------------------------------------------------------ the decision

    def evaluate(self, text: str) -> WakeDecision:
        """
        Classify one transcript. Pure: reads state, never writes it.

        The caller decides whether the turn earned a window refresh, because
        only the caller knows whether the router actually produced an answer.
        That separation is what stops the old latch from coming back.
        """
        text = (text or "").strip()
        if not text:
            return WakeDecision(action="ignore")

        matched = self.find_wake(text)

        if matched:
            query = self.strip_wake(text)
            if not query:
                # Just the wake word on its own. There is nothing to route, but
                # the user clearly addressed Phoenix, so wake up and let the
                # next sentence through without demanding the word again.
                return WakeDecision(
                    action="acknowledge", trigger="wake", matched=matched
                )
            return WakeDecision(
                action="respond", query=query, trigger="wake", matched=matched
            )

        if self.is_awake:
            return WakeDecision(action="respond", query=text, trigger="followup")

        return WakeDecision(action="ignore", query=text)
