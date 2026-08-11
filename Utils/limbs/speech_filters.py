"""
Transcript-level filters that sit between Whisper and the intent router.

Two independent problems are handled here, both observed in the 19:54-20:12
session log:

  1. Whisper hallucinates on near-silence.  Fed 30 s of room noise it emitted
     "Thank you.  Bye." three times in eight minutes with nobody in the room.
     These are the model's stock silence artefacts, learned from subtitle
     training data.

  2. Phoenix hears its own voice.  The log contains a single "user" utterance
     that is Phoenix's own reply with the user's next command glued onto the
     end: "I'm running on Kaly's Windows PC, your majesty, ... Set brightness
     to 50%."

The acoustic echo gate in audio_capture handles (2) at the frame level.  This
module is the second, independent layer: even if a stray syllable of self-voice
survives the gate, it must not reach the router.  Either defence alone leaks.
"""

from __future__ import annotations

import logging
import re
from collections import deque
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Deque, List, Optional, Tuple

logger = logging.getLogger("PhoenixSpeechFilters")

_WORD_RE = re.compile(r"[a-z0-9']+")

# Whisper's stock silence artefacts.  Only applied to short, low-confidence
# utterances -- a deliberate "thank you" mid-conversation is still allowed
# through when the model is confident about it.
HALLUCINATION_PHRASES = frozenset(
    {
        "",
        ".",
        "..",
        "...",
        "you",
        "thank you",
        "thanks",
        "thank you very much",
        "thank you so much",
        "thanks for watching",
        "thank you for watching",
        "thanks for watching!",
        "please subscribe",
        "like and subscribe",
        "bye",
        "bye bye",
        "goodbye",
        "okay",
        "ok",
        "oh",
        "uh",
        "um",
        "hmm",
        "yeah",
        "so",
        "the",
        "subtitles by the amara.org community",
        "subtitles by the amara org community",
        "transcription by castingwords",
        "www.mooji.org",
    }
)


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return " ".join(_WORD_RE.findall(text.lower()))


def tokenize_with_spans(text: str) -> Tuple[List[str], List[Tuple[int, int]]]:
    """Word tokens plus their character spans in the original string."""
    tokens: List[str] = []
    spans: List[Tuple[int, int]] = []
    for match in _WORD_RE.finditer(text.lower()):
        tokens.append(match.group())
        spans.append((match.start(), match.end()))
    return tokens, spans


# --------------------------------------------------------------------------
# Hallucination filter
# --------------------------------------------------------------------------


@dataclass
class TranscriptionCandidate:
    """What Whisper produced, with the confidence signals it exposes."""

    text: str
    duration: float = 0.0  # seconds of audio transcribed
    voiced_ms: float = 0.0  # VAD-measured speech inside that audio
    no_speech_prob: float = 0.0  # max across segments
    avg_logprob: float = 0.0  # min across segments


class HallucinationFilter:
    """
    Rejects transcripts that Whisper invented rather than heard.

    Whisper exposes two usable confidence signals per segment: `no_speech_prob`
    (its own estimate that the audio contains no speech) and `avg_logprob`
    (token confidence).  Hallucinated subtitle boilerplate scores badly on both.
    The phrase blacklist is only consulted for short utterances, and never for
    wake words -- rejecting "yo" or "babe" would make Phoenix unwakeable.
    """

    def __init__(
        self,
        max_no_speech_prob: float = 0.6,
        min_avg_logprob: float = -1.0,
        short_utterance_seconds: float = 1.2,
        min_voiced_ms: float = 400.0,
        wake_words: Optional[List[str]] = None,
    ):
        self.max_no_speech_prob = max_no_speech_prob
        self.min_avg_logprob = min_avg_logprob
        self.short_utterance_seconds = short_utterance_seconds
        self.min_voiced_ms = min_voiced_ms

        protected = {normalize(w) for w in (wake_words or [])}
        self.phrases = frozenset(p for p in HALLUCINATION_PHRASES if p not in protected)

    def rejection_reason(self, candidate: TranscriptionCandidate) -> Optional[str]:
        text = normalize(candidate.text)

        if not text:
            return "empty"

        if candidate.voiced_ms and candidate.voiced_ms < self.min_voiced_ms:
            return f"only {candidate.voiced_ms:.0f}ms voiced"

        if candidate.no_speech_prob > self.max_no_speech_prob:
            return f"no_speech_prob={candidate.no_speech_prob:.2f}"

        if candidate.avg_logprob < self.min_avg_logprob:
            return f"avg_logprob={candidate.avg_logprob:.2f}"

        if (
            candidate.duration
            and candidate.duration < self.short_utterance_seconds
            and text in self.phrases
        ):
            return f"boilerplate '{text}'"

        return None

    def accepts(self, candidate: TranscriptionCandidate) -> bool:
        return self.rejection_reason(candidate) is None


# --------------------------------------------------------------------------
# Self-echo filter
# --------------------------------------------------------------------------


@dataclass
class EchoVerdict:
    action: str  # "accept" | "reject" | "trim"
    text: str  # the text to use (trimmed when action == "trim")
    reason: Optional[str] = None

    @property
    def rejected(self) -> bool:
        return self.action == "reject"


class SelfEchoFilter:
    """
    Rejects transcripts that are Phoenix repeating itself.

    Comparison is word-level, not character-level, because Whisper transcribes
    its own synthesized voice with different punctuation and casing than the
    text that was fed to the TTS engine.

    Three outcomes:
      * whole transcript closely matches something Phoenix just said -> reject
      * a long echoed block sits at one end with real speech at the other
        -> trim the echo and keep the rest (this is the exact
        "<reply>. Set brightness to 50%" case from the log)
      * otherwise -> accept
    """

    def __init__(
        self,
        history_size: int = 5,
        similarity_threshold: float = 0.62,
        min_overlap_words: int = 5,
        reject_coverage: float = 0.6,
        min_kept_words: int = 2,
    ):
        self._history: Deque[List[str]] = deque(maxlen=history_size)
        self.similarity_threshold = similarity_threshold
        self.min_overlap_words = min_overlap_words
        self.reject_coverage = reject_coverage
        self.min_kept_words = min_kept_words

    def remember(self, text: str):
        """Record something Phoenix just said."""
        tokens = normalize(text).split()
        if tokens:
            self._history.append(tokens)

    def set_history(self, texts: List[str]):
        """
        Replace the history wholesale.

        Used to pull the shared TTS history off the queue server, so speech
        produced by *other* Phoenix processes -- battery and time announcements
        come from the TUI process, not this one -- is also recognised as
        self-voice.
        """
        self._history.clear()
        for text in texts:
            self.remember(text)

    def clear(self):
        self._history.clear()

    def check(self, text: str) -> EchoVerdict:
        tokens, spans = tokenize_with_spans(text)
        if not tokens or not self._history:
            return EchoVerdict("accept", text)

        for spoken in reversed(self._history):
            matcher = SequenceMatcher(None, tokens, spoken, autojunk=False)
            blocks = [b for b in matcher.get_matching_blocks() if b.size > 0]

            if blocks:
                # Total matched words, not just the longest run. Whisper
                # transcribes Phoenix's synthesized voice with small
                # substitutions ("sir" -> "your majesty"), which splits one
                # echo into several blocks; judging by the longest block alone
                # makes a pure repeat look like it has original content in it.
                matched = sum(b.size for b in blocks)
                span_start = blocks[0].a
                span_end = blocks[-1].a + blocks[-1].size  # exclusive

                if matched >= self.min_overlap_words:
                    # Salvage before rejecting: the characteristic failure is
                    # Phoenix's reply with the user's next command glued onto
                    # the end, and rejecting that outright throws the command
                    # away. Only audio outside the matched span can be real.
                    head, tail = tokens[:span_start], tokens[span_end:]

                    if len(tail) >= self.min_kept_words and len(tail) >= len(head):
                        logger.info("Trimmed %d echoed words from head", span_end)
                        return EchoVerdict(
                            "trim",
                            text[spans[span_end][0] :].strip(),
                            f"removed {span_end} echoed words",
                        )
                    if len(head) >= self.min_kept_words:
                        logger.info("Trimmed %d echoed words from tail", len(tokens) - span_start)
                        return EchoVerdict(
                            "trim",
                            text[: spans[span_start - 1][1]].strip(),
                            f"removed {len(tokens) - span_start} echoed words",
                        )

                    coverage = matched / len(tokens)
                    if coverage >= self.reject_coverage:
                        return EchoVerdict(
                            "reject", text, f"{coverage:.0%} of it is own speech"
                        )

            if matcher.ratio() >= self.similarity_threshold:
                return EchoVerdict(
                    "reject", text, f"matches own speech ({matcher.ratio():.0%})"
                )

        return EchoVerdict("accept", text)
