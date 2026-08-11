"""
Speaker verification — answer the owner's voice, not the room.

## What this is, and what it is not

This is a **convenience filter**. On a laptop microphone in a normal room it
separates the owner from other people well enough to stop the TV and a passing
conversation from issuing commands. It is **not a security control**:

  * a recording of the owner's voice passes it,
  * so does a good impersonation,
  * accuracy falls off with distance, illness, and background noise.

Do not put anything behind it that must not be spoofed. It exists to make
Phoenix stop reacting to everyone in the room, which is the problem that was
actually reported.

## Fail-open, always

Every uncertainty resolves to `accepted=True`:

  * no enrolment profile on this machine,
  * the encoder failed to load or to run,
  * the utterance is too short to judge.

A voice assistant that goes deaf because a model file is missing is a worse
failure than one that occasionally answers a guest. The filter can only ever
*remove* a response it was confident it should remove.

## Ship in "log" mode first

`security.speaker_verification.mode` starts at `"log"`: scores are printed, and
every utterance is still processed. Run it that way for a few days, look at the
real numbers for yourself and for other people, then set `"gate"` with a
threshold picked from that data. A cosine threshold chosen by intuition is how
this feature ends up ignoring its owner when they have a cold.

Enrol with `tests/enroll_voice.py`.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

logger = logging.getLogger("SpeakerID")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROFILE_FILE = os.path.join(_ROOT, "data", "speaker_profile.npz")

SAMPLE_RATE = 16000


@dataclass(frozen=True)
class VerificationResult:
    accepted: bool
    score: float
    reason: str

    @property
    def verifiable(self) -> bool:
        """False when no real decision was made (fail-open path)."""
        return self.reason not in (
            "no-profile",
            "unavailable",
            "too-short",
            "disabled",
            "error",
        )


class SpeakerVerifier:
    """
    Cosine-similarity speaker check against an enrolled profile.

    The encoder is loaded lazily on first use, so importing this module and
    constructing the verifier stay cheap even when verification is switched off
    or nobody has enrolled.
    """

    def __init__(
        self,
        profile_path: str = PROFILE_FILE,
        threshold: float = 0.72,
        min_duration_s: float = 0.8,
        enabled: bool = True,
        mode: str = "log",
    ):
        self.profile_path = profile_path
        self.threshold = float(threshold)
        self.min_duration_s = float(min_duration_s)
        self.enabled = bool(enabled)
        self.mode = mode if mode in ("log", "gate") else "log"

        self._encoder = None
        self._encoder_failed = False
        self._centroid: Optional[np.ndarray] = None
        self._embeddings: Optional[np.ndarray] = None
        self._profile_mtime: Optional[float] = None

        self._load_profile()

    # -- profile ------------------------------------------------------------

    @property
    def enrolled(self) -> bool:
        return self._centroid is not None

    def _load_profile(self) -> bool:
        if not os.path.exists(self.profile_path):
            logger.info("No speaker profile at %s - verification inactive", self.profile_path)
            self._centroid = None
            self._embeddings = None
            return False

        try:
            with np.load(self.profile_path) as data:
                embeddings = np.asarray(data["embeddings"], dtype=np.float32)
                centroid = np.asarray(data["centroid"], dtype=np.float32)
        except Exception as exc:
            # A corrupt profile must not take the voice processor down. Treat it
            # as "not enrolled", which fails open.
            logger.error("Speaker profile unreadable (%s) - verification inactive", exc)
            self._centroid = None
            self._embeddings = None
            return False

        if embeddings.ndim != 2 or centroid.ndim != 1:
            logger.error("Speaker profile has an unexpected shape - verification inactive")
            self._centroid = None
            self._embeddings = None
            return False

        self._embeddings = _l2_normalize_rows(embeddings)
        self._centroid = _l2_normalize(centroid)
        self._profile_mtime = os.path.getmtime(self.profile_path)
        logger.info("Speaker profile loaded: %d enrolled utterances", len(self._embeddings))
        return True

    def reload_if_stale(self):
        """Pick up a profile enrolled while Phoenix was running."""
        try:
            mtime = os.path.getmtime(self.profile_path)
        except OSError:
            return
        if mtime != self._profile_mtime:
            self._load_profile()

    # -- encoder ------------------------------------------------------------

    def _get_encoder(self):
        if self._encoder is not None or self._encoder_failed:
            return self._encoder
        try:
            from resemblyzer import VoiceEncoder

            self._encoder = VoiceEncoder("cpu")
            logger.info("Speaker encoder ready (resemblyzer, cpu)")
        except Exception as exc:
            # Missing dependency, missing weights, broken install -- all the
            # same to us: verification becomes a no-op rather than an outage.
            logger.warning("Speaker encoder unavailable (%s) - verification inactive", exc)
            self._encoder_failed = True
        return self._encoder

    def embed(self, audio: np.ndarray) -> Optional[np.ndarray]:
        """L2-normalised embedding for int16 or float32 mono @ 16 kHz."""
        encoder = self._get_encoder()
        if encoder is None:
            return None

        try:
            from resemblyzer import preprocess_wav

            wav = _to_float(audio)
            # preprocess_wav normalises loudness and trims leading/trailing
            # silence. Enrolment and live audio must go through the SAME
            # preprocessing or the embeddings sit in slightly different spaces
            # and every score comes out low.
            wav = preprocess_wav(wav, source_sr=SAMPLE_RATE)
            if wav.size < int(0.2 * SAMPLE_RATE):
                return None
            return _l2_normalize(np.asarray(encoder.embed_utterance(wav), dtype=np.float32))
        except Exception as exc:
            logger.warning("Embedding failed (%s)", exc)
            return None

    # -- the decision -------------------------------------------------------

    def verify(self, audio: np.ndarray) -> VerificationResult:
        """
        Score `audio` against the enrolled profile.

        Every branch that cannot make a confident judgement returns
        `accepted=True`. Read `VerificationResult.verifiable` to tell a real
        acceptance from a fail-open one.
        """
        if not self.enabled:
            return VerificationResult(True, 0.0, "disabled")

        self.reload_if_stale()
        if not self.enrolled:
            return VerificationResult(True, 0.0, "no-profile")

        duration = len(audio) / float(SAMPLE_RATE)
        if duration < self.min_duration_s:
            # Under a second there is not enough voiced material for a stable
            # embedding, and scoring it anyway produces confident nonsense in
            # both directions.
            return VerificationResult(True, 0.0, "too-short")

        embedding = self.embed(audio)
        if embedding is None:
            return VerificationResult(True, 0.0, "unavailable")

        centroid_score = float(np.dot(embedding, self._centroid))
        best_score = float(np.max(self._embeddings @ embedding))
        # The centroid is the stable summary; the best individual match rescues
        # a legitimate utterance that happens to resemble one enrolment sample
        # far more than the average (a different tone of voice, say).
        score = max(centroid_score, best_score)

        accepted = score >= self.threshold
        return VerificationResult(accepted, score, "match" if accepted else "mismatch")

    def should_reject(self, result: VerificationResult) -> bool:
        """
        Whether the caller must drop this utterance.

        In `log` mode the answer is always False -- the score is recorded and
        nothing is suppressed. That is the shipping default, and flipping it to
        `gate` is a deliberate act taken once the numbers are known.
        """
        if self.mode != "gate":
            return False
        return not result.accepted and result.verifiable


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _to_float(audio: np.ndarray) -> np.ndarray:
    audio = np.asarray(audio)
    if audio.dtype == np.int16:
        return audio.astype(np.float32) / 32768.0
    return audio.astype(np.float32)


def _l2_normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 else vector


def _l2_normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def build_profile(embeddings: List[np.ndarray]) -> dict:
    """Turn enrolment embeddings into the arrays saved in the profile file."""
    stacked = _l2_normalize_rows(np.vstack([np.asarray(e, dtype=np.float32) for e in embeddings]))
    centroid = _l2_normalize(stacked.mean(axis=0))
    return {"embeddings": stacked, "centroid": centroid}


def profile_spread(embeddings: np.ndarray) -> dict:
    """
    Pairwise similarity stats for an enrolment set.

    A tight spread means the samples agree on what the owner sounds like. A wide
    one means something contaminated the recording -- a different mic, another
    person talking, or too much background noise -- and the profile should be
    recorded again rather than used.
    """
    stacked = _l2_normalize_rows(np.asarray(embeddings, dtype=np.float32))
    similarities = stacked @ stacked.T
    upper = similarities[np.triu_indices(len(stacked), k=1)]
    if upper.size == 0:
        return {"min": 1.0, "mean": 1.0, "max": 1.0}
    return {"min": float(upper.min()), "mean": float(upper.mean()), "max": float(upper.max())}


_VERIFIER: Optional[SpeakerVerifier] = None


def get_verifier() -> SpeakerVerifier:
    """Shared instance configured from AppConfig."""
    global _VERIFIER
    if _VERIFIER is None:
        from core.config import AppConfig

        cfg = getattr(AppConfig, "security", {}).get("speaker_verification", {})
        _VERIFIER = SpeakerVerifier(
            threshold=float(cfg.get("threshold", 0.72)),
            min_duration_s=float(cfg.get("min_duration_s", 0.8)),
            enabled=bool(cfg.get("enabled", True)),
            mode=str(cfg.get("mode", "log")),
        )
    return _VERIFIER
