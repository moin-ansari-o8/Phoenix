"""
Regression tests for Utils/limbs/speaker_id.py.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\tests\\test_speaker_id.py

The fail-open paths are the point of this file. Speaker verification sits in
front of everything else in the processing chain, so any way it can raise, or
any way it can reject when it should not, takes Phoenix's hearing with it. A
missing profile, a corrupt profile, a missing dependency and a too-short clip
must all end with the utterance being processed normally.

Runs without a microphone. The encoder is only exercised if resemblyzer is
installed; the fail-open logic is tested either way.
"""

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Utils.limbs.speaker_id import (
    SAMPLE_RATE,
    SpeakerVerifier,
    build_profile,
    profile_spread,
)

_RESULTS = []


def check(name, condition, detail=""):
    _RESULTS.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f"  -- {detail}" if detail and not condition else ""))


def section(title):
    print(f"\n{title}\n{'-' * len(title)}")


def tone(seconds=2.0, freq=140.0, seed=0):
    """A voiced-ish signal: a harmonic stack with noise, as int16."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, seconds, int(SAMPLE_RATE * seconds), endpoint=False)
    wave = sum(np.sin(2 * np.pi * freq * k * t) / k for k in (1, 2, 3, 4))
    wave = wave / np.max(np.abs(wave))
    wave = wave * (0.4 + 0.2 * np.sin(2 * np.pi * 3 * t))  # crude envelope
    wave = wave + rng.normal(0, 0.01, wave.shape)
    return (wave * 12000).astype(np.int16)


# --------------------------------------------------------------------------
# 1. Fail-open behaviour -- the important half
# --------------------------------------------------------------------------


def test_fails_open():
    section("Fail-open paths")

    audio = tone(2.0)

    missing = SpeakerVerifier(profile_path=os.path.join(tempfile.gettempdir(), "nope.npz"))
    result = missing.verify(audio)
    check("no profile -> accepted", result.accepted, result.reason)
    check("no profile is marked unverifiable", not result.verifiable, result.reason)
    check("no profile never rejects", not missing.should_reject(result))

    disabled = SpeakerVerifier(enabled=False)
    result = disabled.verify(audio)
    check("disabled -> accepted", result.accepted and not result.verifiable, result.reason)

    # A corrupt profile is the case that would otherwise crash the processor at
    # construction time and stop the audio queue being drained at all.
    with tempfile.TemporaryDirectory() as tmp:
        corrupt = os.path.join(tmp, "speaker_profile.npz")
        with open(corrupt, "wb") as handle:
            handle.write(b"this is not an npz file at all")
        broken = SpeakerVerifier(profile_path=corrupt)
        check("a corrupt profile does not raise on load", not broken.enrolled)
        result = broken.verify(audio)
        check("a corrupt profile still accepts", result.accepted, result.reason)

        # Right container, wrong contents.
        wrong_shape = os.path.join(tmp, "wrong.npz")
        np.savez(wrong_shape, embeddings=np.zeros(5), centroid=np.zeros((3, 3)))
        odd = SpeakerVerifier(profile_path=wrong_shape)
        check("a wrongly-shaped profile is rejected safely", not odd.enrolled)
        check("a wrongly-shaped profile still accepts", odd.verify(audio).accepted)


def test_short_audio_passes():
    section("Short audio is not judged")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "profile.npz")
        rng = np.random.default_rng(1)
        embeddings = [rng.normal(0, 1, 256).astype(np.float32) for _ in range(6)]
        np.savez(path, **build_profile(embeddings))

        verifier = SpeakerVerifier(profile_path=path, min_duration_s=0.8)
        check("the profile loaded", verifier.enrolled)

        short = tone(0.4)
        result = verifier.verify(short)
        check("400ms of audio is not judged", result.accepted, result.reason)
        check("too-short is marked unverifiable", not result.verifiable, result.reason)
        check("too-short never rejects", not verifier.should_reject(result))


# --------------------------------------------------------------------------
# 2. Mode behaviour
# --------------------------------------------------------------------------


def test_log_mode_never_suppresses():
    section("Log mode suppresses nothing")

    from Utils.limbs.speaker_id import VerificationResult

    logger_mode = SpeakerVerifier(mode="log", threshold=0.72)
    gate_mode = SpeakerVerifier(mode="gate", threshold=0.72)

    mismatch = VerificationResult(accepted=False, score=0.31, reason="mismatch")
    check("log mode does not reject a mismatch", not logger_mode.should_reject(mismatch))
    check("gate mode rejects a mismatch", gate_mode.should_reject(mismatch))

    match = VerificationResult(accepted=True, score=0.91, reason="match")
    check("gate mode accepts a match", not gate_mode.should_reject(match))

    # Fail-open reasons must survive gate mode too -- this is the difference
    # between "we judged you and said no" and "we could not judge you".
    for reason in ("no-profile", "unavailable", "too-short", "disabled", "error"):
        result = VerificationResult(accepted=True, score=0.0, reason=reason)
        check(f"gate mode never rejects on '{reason}'", not gate_mode.should_reject(result))


def test_invalid_mode_defaults_to_log():
    section("Configuration safety")

    check("an unknown mode falls back to log", SpeakerVerifier(mode="banana").mode == "log")
    check("gate is honoured when asked for", SpeakerVerifier(mode="gate").mode == "gate")


# --------------------------------------------------------------------------
# 3. Profile maths
# --------------------------------------------------------------------------


def test_profile_maths():
    section("Profile construction")

    rng = np.random.default_rng(7)
    base = rng.normal(0, 1, 256).astype(np.float32)
    tight = [base + rng.normal(0, 0.05, 256).astype(np.float32) for _ in range(8)]
    loose = [rng.normal(0, 1, 256).astype(np.float32) for _ in range(8)]

    profile = build_profile(tight)
    check("embeddings are stacked", profile["embeddings"].shape == (8, 256))
    check(
        "rows are unit length",
        np.allclose(np.linalg.norm(profile["embeddings"], axis=1), 1.0, atol=1e-5),
    )
    check(
        "the centroid is unit length",
        abs(float(np.linalg.norm(profile["centroid"])) - 1.0) < 1e-5,
    )

    tight_spread = profile_spread(build_profile(tight)["embeddings"])
    loose_spread = profile_spread(build_profile(loose)["embeddings"])
    check(
        "consistent samples score a tight spread",
        tight_spread["mean"] > 0.9,
        f"{tight_spread['mean']:.2f}",
    )
    check(
        "unrelated samples score a loose spread",
        loose_spread["mean"] < 0.3,
        f"{loose_spread['mean']:.2f}",
    )


# --------------------------------------------------------------------------
# 4. The encoder, if it is installed
# --------------------------------------------------------------------------


def test_encoder_if_available():
    section("Encoder (skipped if resemblyzer is absent)")

    verifier = SpeakerVerifier()
    if verifier._get_encoder() is None:
        print("  [SKIP] resemblyzer not installed")
        return

    audio = tone(2.0, freq=140.0, seed=0)
    embedding = verifier.embed(audio)
    check("an embedding is produced", embedding is not None)
    if embedding is None:
        return

    check("the embedding is 256-dimensional", embedding.shape == (256,), str(embedding.shape))
    check(
        "the embedding is unit length",
        abs(float(np.linalg.norm(embedding)) - 1.0) < 1e-4,
    )

    # The same audio must embed identically, or nothing downstream is stable.
    again = verifier.embed(audio)
    check(
        "the same audio embeds to the same vector",
        again is not None and float(np.dot(embedding, again)) > 0.999,
    )

    check("silence produces no embedding", verifier.embed(np.zeros(16000, dtype=np.int16)) is None)


if __name__ == "__main__":
    print("Phoenix speaker verification regression tests")
    test_fails_open()
    test_short_audio_passes()
    test_log_mode_never_suppresses()
    test_invalid_mode_defaults_to_log()
    test_profile_maths()
    test_encoder_if_available()

    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    failed = [(name, detail) for name, ok, detail in _RESULTS if not ok]

    print(f"\n{'=' * 60}")
    print(f"{passed}/{len(_RESULTS)} checks passed")
    if failed:
        print("\nFailures:")
        for name, detail in failed:
            print(f"  - {name}" + (f"  ({detail})" if detail else ""))
    sys.exit(1 if failed else 0)
