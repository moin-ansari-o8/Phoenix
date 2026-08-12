"""
Turn a token stream into speakable sentences.

The answer model generates at roughly 170 characters per second on this box, so
a three-sentence reply takes 2-3 s to finish. Waiting for the whole thing before
synthesising anything means the user hears nothing for that entire time. Feeding
TTS sentence by sentence means the first words start while the rest is still
being written, which roughly halves *perceived* latency without making the model
one token faster.

The hard parts are all about not cutting in the wrong place:

- **Abbreviations.** "Dr. Ambedkar" and "at 5 p.m. tomorrow" contain a period
  that is not a sentence end. Splitting there makes TTS stop dead mid-phrase
  with falling intonation, which sounds worse than not streaming at all.
- **Decimals and versions.** "3.14", "Python 3.11" - same problem.
- **A model that forgets punctuation.** Small models sometimes produce a long
  run-on. Without a cap the first audio never starts, so there is a forced flush
  at `max_chars` on the last word boundary.
- **Too-short fragments.** "Yes." on its own is a whole TTS round trip for one
  word, and the pause after it reads as the answer being finished. Short pieces
  are held and merged with the next.
"""

from __future__ import annotations

import re
from typing import Iterable, Iterator, List

# Tokens ending in "." that do not end a sentence.
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "mt", "rev", "hon",
    "inc", "ltd", "co", "corp", "dept", "est", "fig", "vs", "etc", "eg", "ie",
    "approx", "min", "max", "no", "vol", "pp", "ed", "al",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct",
    "nov", "dec", "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
}

_SENTENCE_END = re.compile(r"[.!?]+[\"')\]]*\s")
_LAST_WORD = re.compile(r"(\w+)[.!?]+[\"')\]]*\s*$")
_DIGIT_BEFORE_DOT = re.compile(r"\d\s*[.]$")


class SentenceSplitter:
    """
    Accumulates fragments and emits complete sentences.

    Not thread-safe; it is driven from one generator loop.
    """

    def __init__(self, min_chars: int = 12, max_chars: int = 160):
        self.min_chars = min_chars
        self.max_chars = max_chars
        self._buffer = ""

    def _is_real_boundary(self, text: str) -> bool:
        """Is the '.' at the end of `text` an actual sentence end?"""
        if _DIGIT_BEFORE_DOT.search(text):
            return False  # "3." of "3.14", or a numbered list item
        match = _LAST_WORD.search(text)
        if match and match.group(1).lower() in _ABBREVIATIONS:
            return False
        return True

    def feed(self, fragment: str) -> List[str]:
        """Add text, return any sentences that are now complete."""
        self._buffer += fragment
        out = []

        while True:
            match = _SENTENCE_END.search(self._buffer)
            if match:
                cut = match.end()
                candidate = self._buffer[:cut]
                if not self._is_real_boundary(candidate):
                    # Not a real end. Look past it for the next candidate
                    # rather than emitting "at 5 p."
                    later = _SENTENCE_END.search(self._buffer, cut)
                    if not later:
                        break
                    cut = later.end()
                    candidate = self._buffer[:cut]
                    if not self._is_real_boundary(candidate):
                        break

                # Too short to be worth its own TTS round trip, and the pause
                # after it would read as the answer ending. Keep accumulating.
                if len(candidate.strip()) < self.min_chars:
                    if len(self._buffer) < self.max_chars:
                        break

                out.append(candidate.strip())
                self._buffer = self._buffer[cut:]
                continue

            # No punctuation in sight and the buffer is long: a model that
            # forgot to punctuate must not stall the audio forever. Flush on
            # the last word boundary so a word is never cut in half.
            if len(self._buffer) >= self.max_chars:
                space = self._buffer.rfind(" ", 0, self.max_chars)
                if space <= 0:
                    break
                out.append(self._buffer[:space].strip())
                self._buffer = self._buffer[space:]
                continue

            break

        return [s for s in out if s]

    def flush(self) -> List[str]:
        """Emit whatever is left. Call once the stream ends."""
        rest = self._buffer.strip()
        self._buffer = ""
        return [rest] if rest else []


def stream_sentences(
    fragments: Iterable[str], min_chars: int = 12, max_chars: int = 160
) -> Iterator[str]:
    """Convenience wrapper: fragment iterable -> sentence iterator."""
    splitter = SentenceSplitter(min_chars=min_chars, max_chars=max_chars)
    for fragment in fragments:
        for sentence in splitter.feed(fragment):
            yield sentence
    for sentence in splitter.flush():
        yield sentence
