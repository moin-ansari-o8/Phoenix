"""
Regression tests for the listening pipeline.

Run directly (no pytest in this venv):
    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\tests\\test_listener_pipeline.py

Every test here corresponds to a defect that actually shipped and made voice
mode unusable in the 19:54-20:12 session:

  * endpointer    - it never ended an utterance on silence; every chunk was
                    exactly 30.08 s of mostly room noise
  * echo gate     - the speaking flag never crossed the process boundary, so
                    Phoenix transcribed its own replies as user speech
  * hallucination - 30 s of silence made Whisper emit "Thank you."
  * self-echo     - a reply and the user's next command arrived fused into one
                    transcript
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Utils.limbs.audio_capture import (
    FRAME_MS,
    FRAME_SAMPLES,
    EchoGate,
    Endpointer,
    EndpointerConfig,
    Frame,
    frames_for_ms,
)
from Utils.limbs.speech_filters import (
    HallucinationFilter,
    SelfEchoFilter,
    TranscriptionCandidate,
)

# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------

_RESULTS = []


def check(name, condition, detail=""):
    _RESULTS.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f"  -- {detail}" if detail and not condition else ""))


def section(title):
    print(f"\n{title}\n{'-' * len(title)}")


def make_frame(index, level=1000):
    """A frame whose capture timestamp is derived from its index."""
    return Frame(
        timestamp=index * FRAME_MS / 1000.0,
        samples=(np.ones(FRAME_SAMPLES) * level).astype(np.int16),
        rms=float(level),
    )


def drive(endpointer, pattern, start_index=0):
    """Feed a list of booleans; return (utterances, next_index)."""
    utterances = []
    index = start_index
    for voiced in pattern:
        result = endpointer.push(make_frame(index), voiced)
        if result is not None:
            utterances.append(result)
        index += 1
    return utterances, index


# --------------------------------------------------------------------------
# 1. Endpointer
# --------------------------------------------------------------------------


def test_endpointer():
    section("Endpointer")
    config = EndpointerConfig(
        pre_roll_ms=300, hangover_ms=600, min_voiced_ms=400, max_utterance_ms=12000
    )

    # THE original bug: a permanently noisy room must never produce an utterance.
    endpointer = Endpointer(config)
    utterances, _ = drive(endpointer, [False] * frames_for_ms(60000))
    check(
        "60s of silence produces no utterance",
        not utterances,
        f"got {len(utterances)}",
    )
    check("endpointer stays idle through silence", not endpointer.active)

    # Normal turn: ~2 s of speech then a pause.
    endpointer = Endpointer(config)
    speech = [True] * frames_for_ms(2000)
    trailing = [False] * frames_for_ms(1000)
    utterances, _ = drive(endpointer, speech + trailing)
    check("speech then silence yields one utterance", len(utterances) == 1)
    if utterances:
        utterance = utterances[0]
        check(
            "utterance closed on silence, not a timeout",
            utterance.reason == "silence",
            utterance.reason,
        )
        check(
            "duration is ~2s of speech plus hangover, not 30s",
            2.0 <= utterance.duration <= 3.5,
            f"{utterance.duration:.2f}s",
        )
        check(
            "pre-roll is included so the first syllable survives",
            utterance.start_timestamp < speech_start_time(config),
            f"start={utterance.start_timestamp:.3f}",
        )
        check(
            "voiced time is measured, not assumed",
            1800 <= utterance.voiced_ms <= 2200,
            f"{utterance.voiced_ms:.0f}ms",
        )

    # A door slam: too little voiced audio to be a command.
    endpointer = Endpointer(config)
    utterances, _ = drive(
        endpointer, [True] * frames_for_ms(200) + [False] * frames_for_ms(1000)
    )
    check("a 200ms blip is discarded as noise", not utterances, f"got {len(utterances)}")

    # Someone talking continuously must be cut at the cap, and the cap must be
    # nowhere near the 30 s that used to be hardcoded.
    endpointer = Endpointer(config)
    utterances, _ = drive(endpointer, [True] * frames_for_ms(20000))
    check("continuous speech is capped", len(utterances) >= 1)
    if utterances:
        check(
            "cap fires at 12s, not 30s",
            utterances[0].reason == "max_duration"
            and 11.0 <= utterances[0].duration <= 13.0,
            f"{utterances[0].duration:.2f}s / {utterances[0].reason}",
        )

    # reset() must abandon an in-progress utterance (used when the echo gate
    # closes, so self-voice cannot be stitched onto a live utterance).
    endpointer = Endpointer(config)
    drive(endpointer, [True] * frames_for_ms(1000))
    check("utterance is in progress before reset", endpointer.active)
    endpointer.reset()
    check("reset abandons the in-progress utterance", not endpointer.active)
    utterances, _ = drive(endpointer, [False] * frames_for_ms(1000), start_index=100)
    check("nothing is emitted after a reset", not utterances)


def speech_start_time(config):
    """Timestamp of the frame where speech was actually confirmed."""
    return (config.start_frames - 1) * FRAME_MS / 1000.0 + 1e-9


# --------------------------------------------------------------------------
# 2. Echo gate
# --------------------------------------------------------------------------


def test_echo_gate():
    section("Echo gate")

    window = {"since": 0.0, "until": 0.0}
    gate = EchoGate(
        state_provider=lambda: (window["since"], window["until"]),
        lead_in=0.15,
        tail=0.40,
        poll_interval=0.0,  # no throttling in tests
    )

    # Phoenix spoke from t=100 to t=105.
    window["since"], window["until"] = 100.0, 105.0

    check("frame captured before playback is kept", not gate.should_drop(99.0))
    check("frame captured during playback is dropped", gate.should_drop(102.0))
    check("frame in the reverb tail is dropped", gate.should_drop(105.2))
    check("frame well after playback is kept", not gate.should_drop(106.0))

    # THE regression that broke everything: a frame recorded mid-playback but
    # examined only after playback finished. A live boolean "is it speaking
    # now?" says False here and lets self-voice straight through.
    window["since"], window["until"] = 100.0, 105.0
    check(
        "mid-playback frame examined late is still dropped",
        gate.should_drop(102.0),
        "self-voice would leak",
    )

    # Close edge fires exactly once, so the driver flushes once.
    gate2 = EchoGate(
        state_provider=lambda: (100.0, 105.0), lead_in=0.15, tail=0.40, poll_interval=0.0
    )
    gate2.should_drop(102.0)  # gating
    gate2.should_drop(106.0)  # no longer gating -> edge
    check("close edge is reported once", gate2.consume_close_edge())
    check("close edge is not reported twice", not gate2.consume_close_edge())

    # Headphone mode: nothing is ever gated.
    gate3 = EchoGate(
        state_provider=lambda: (100.0, 105.0), poll_interval=0.0, enabled=False
    )
    check("disabled gate passes audio during playback", not gate3.should_drop(102.0))


# --------------------------------------------------------------------------
# 3. Hallucination filter
# --------------------------------------------------------------------------


def test_hallucination_filter():
    section("Hallucination filter")

    filt = HallucinationFilter(wake_words=["phoenix", "igris", "yo", "babe"])

    # Exactly what the log showed at 19:59, 20:02 and 20:03.
    ghost = TranscriptionCandidate(
        text="Thank you.  Bye.",
        duration=0.9,
        voiced_ms=500,
        no_speech_prob=0.85,
        avg_logprob=-1.4,
    )
    check("silence hallucination is rejected", not filt.accepts(ghost))

    quiet = TranscriptionCandidate(
        text="Thank you.", duration=0.8, voiced_ms=120, no_speech_prob=0.2, avg_logprob=-0.3
    )
    check(
        "utterance with too little voiced audio is rejected",
        not filt.accepts(quiet),
        filt.rejection_reason(quiet) or "",
    )

    boilerplate = TranscriptionCandidate(
        text="Thanks for watching!",
        duration=1.0,
        voiced_ms=600,
        no_speech_prob=0.3,
        avg_logprob=-0.5,
    )
    check("subtitle boilerplate is rejected", not filt.accepts(boilerplate))

    real = TranscriptionCandidate(
        text="set brightness to 50 percent",
        duration=2.1,
        voiced_ms=1700,
        no_speech_prob=0.05,
        avg_logprob=-0.25,
    )
    check("a real command is accepted", filt.accepts(real), filt.rejection_reason(real) or "")

    # Wake words must never be filtered as boilerplate, or Phoenix goes deaf.
    for wake in ("phoenix", "yo", "babe"):
        candidate = TranscriptionCandidate(
            text=wake, duration=0.6, voiced_ms=500, no_speech_prob=0.1, avg_logprob=-0.4
        )
        check(f"wake word '{wake}' survives the filter", filt.accepts(candidate))

    empty = TranscriptionCandidate(text="", duration=1.0, voiced_ms=500)
    check("empty transcript is rejected", not filt.accepts(empty))


# --------------------------------------------------------------------------
# 4. Self-echo filter
# --------------------------------------------------------------------------


def test_self_echo_filter():
    section("Self-echo filter")

    filt = SelfEchoFilter()
    reply = (
        "I'm running on kALY's Windows PC, sir. Assisting with tasks and "
        "answering questions to the best of my abilities."
    )
    filt.remember(reply)
    filt.remember("Brightness has been set to 50 percent.")

    verdict = filt.check("I'm running on Kaly's Windows PC, your majesty, assisting "
                         "with tasks and answering questions to the best of my abilities.")
    check("Phoenix repeating itself is rejected", verdict.rejected, verdict.reason or "")

    # The exact 20:11 failure: own reply with the user's next command glued on.
    fused = (
        "I'm running on Kaly's Windows PC, your majesty, assisting with tasks and "
        "answering questions to the best of my abilities.  Set brightness to 50%."
    )
    verdict = filt.check(fused)
    check("fused transcript is trimmed, not dropped", verdict.action == "trim", verdict.action)
    if verdict.action == "trim":
        check(
            "the user's actual command survives trimming",
            "set brightness" in verdict.text.lower(),
            verdict.text,
        )
        check(
            "the echoed reply is gone",
            "windows pc" not in verdict.text.lower(),
            verdict.text,
        )

    verdict = filt.check("what is the weather in mumbai")
    check("unrelated speech is accepted", verdict.action == "accept", verdict.action)

    verdict = filt.check("Brightness has been set to 50 percent.")
    check("a short self-repeat is rejected too", verdict.rejected, verdict.reason or "")

    # Cross-process history replacement (battery/time announcements come from
    # the TUI process, not the voice processor).
    filt.set_history(["Your battery is at 20 percent, sir."])
    verdict = filt.check("Your battery is at 20 percent, sir.")
    check("history from another process is honoured", verdict.rejected)
    verdict = filt.check("I'm running on Kaly's Windows PC")
    check("replaced history no longer matches old speech", verdict.action == "accept")


# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# 5. Whole pipeline on real audio (skipped if the sample recording is missing)
# --------------------------------------------------------------------------

# Lives under tests/fixtures/ on purpose. This used to point at a scratch wav
# in the repo root, which a housekeeping pass deleted -- and the test then
# skipped silently, quietly losing the only check that runs real speech through
# the real VAD. A test's input belongs with the test.
SAMPLE_WAV = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "speech_sample.wav"
)


def load_sample_16k():
    import wave

    with wave.open(SAMPLE_WAV, "rb") as handle:
        rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if rate != 16000:
        from scipy.signal import resample_poly

        audio = resample_poly(audio, 16000, rate)
    return audio.astype(np.int16)


def test_pipeline_on_real_audio():
    section("Whole pipeline on real speech")

    if not os.path.exists(SAMPLE_WAV):
        print(f"  [SKIP] sample recording not found: {SAMPLE_WAV}")
        return

    from Utils.limbs.audio_capture import CapturePipeline, compute_rms

    speech = load_sample_16k()
    rng = np.random.default_rng(0)
    fan = lambda seconds: rng.normal(0, 80, int(16000 * seconds)).astype(np.int16)

    # Fan noise, speech, pause, speech, fan noise -- the shape of a real session.
    timeline = np.concatenate(
        [
            fan(3),
            speech[16000 * 1 : 16000 * 3 + 8000],
            fan(2),
            speech[16000 * 3 : 16000 * 5],
            fan(3),
        ]
    )

    utterances = []
    pipeline = CapturePipeline(on_utterance=utterances.append)
    for index in range(len(timeline) // FRAME_SAMPLES):
        block = timeline[index * FRAME_SAMPLES : (index + 1) * FRAME_SAMPLES]
        pipeline.process_frame(
            Frame(
                timestamp=index * FRAME_MS / 1000.0,
                samples=block,
                rms=compute_rms(block),
            )
        )

    check(
        "both spoken segments are detected",
        len(utterances) == 2,
        f"got {len(utterances)}",
    )
    check(
        "callback and stats agree",
        pipeline.stats.utterances == len(utterances),
        f"stats={pipeline.stats.utterances} callback={len(utterances)}",
    )
    check(
        "the fan does not latch the detector open",
        all(u.reason == "silence" for u in utterances),
        str([u.reason for u in utterances]),
    )
    for utterance in utterances:
        check(
            f"utterance is speech-sized, not a 30s blob ({utterance.duration:.2f}s)",
            1.0 <= utterance.duration <= 5.0,
            f"{utterance.duration:.2f}s",
        )
    check(
        "noise floor adapts to the fan rather than sitting at a constant",
        50 < pipeline.stats.last_noise_floor < 150,
        f"{pipeline.stats.last_noise_floor:.1f}",
    )


# --------------------------------------------------------------------------
# 6. Input device selection
# --------------------------------------------------------------------------


class FakePyAudio:
    """Stands in for PyAudio so device selection can be tested without hardware."""

    def __init__(self, devices, default_index):
        # devices: {index: (name, peak)} -- peak 0 means busy/muted
        self.devices = devices
        self.default_index = default_index
        self.opened = []

    def get_default_input_device_info(self):
        return {"index": self.default_index}

    def get_host_api_info_by_index(self, _):
        return {"deviceCount": len(self.devices)}

    def get_device_info_by_host_api_device_index(self, _, index):
        return {"name": self.devices[index][0], "maxInputChannels": 1}

    def open(self, **kwargs):
        index = kwargs["input_device_index"]
        self.opened.append(index)
        peak = self.devices[index][1]

        class _Stream:
            def read(self, count, exception_on_overflow=False):
                return (np.ones(count, dtype=np.int16) * peak).tobytes()

            def stop_stream(self):
                pass

            def close(self):
                pass

        return _Stream()


def test_device_selection():
    section("Input device selection")

    from Utils.limbs.audio_capture import select_input_device

    # The situation on this machine right now: the default mic is busy in a
    # call and delivers digital silence, while a headset is live.
    audio = FakePyAudio(
        {0: ("Microphone Array (busy in call)", 0), 1: ("Headset Mic", 900)},
        default_index=0,
    )
    chosen, probes = select_input_device(audio)
    check(
        "a mic held by a call is skipped for a live one",
        chosen == 1,
        f"chose {chosen}",
    )
    check("the busy device was actually probed", any(p.index == 0 for p in probes))

    # A healthy default must win without hunting around.
    audio = FakePyAudio(
        {0: ("Microphone Array", 700), 1: ("Headset Mic", 900)}, default_index=0
    )
    chosen, _ = select_input_device(audio)
    check("a healthy default is preferred", chosen == 0, f"chose {chosen}")

    # Every device dead: still return something so the listener keeps running
    # and can retry, rather than crashing out.
    audio = FakePyAudio({0: ("Mic A", 0), 1: ("Mic B", 0)}, default_index=0)
    chosen, _ = select_input_device(audio)
    check("all-dead falls back to the default instead of failing", chosen == 0)

    # Pinning must bypass probing entirely.
    audio = FakePyAudio({0: ("Mic A", 0), 1: ("Mic B", 900)}, default_index=0)
    chosen, probes = select_input_device(audio, preferred=1)
    check("a pinned device is used without probing", chosen == 1 and not probes)

    # Mid-session switch: avoid the device we are stuck on.
    audio = FakePyAudio(
        {0: ("Mic A", 900), 1: ("Mic B", 900)}, default_index=0
    )
    chosen, _ = select_input_device(audio, avoid=0)
    check("re-selection avoids the current device", chosen == 1, f"chose {chosen}")


if __name__ == "__main__":
    print("Phoenix listening pipeline regression tests")
    test_endpointer()
    test_echo_gate()
    test_hallucination_filter()
    test_self_echo_filter()
    test_pipeline_on_real_audio()
    test_device_selection()

    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    failed = [(name, detail) for name, ok, detail in _RESULTS if not ok]

    print(f"\n{'=' * 60}")
    print(f"{passed}/{len(_RESULTS)} checks passed")
    if failed:
        print("\nFailures:")
        for name, detail in failed:
            print(f"  - {name}" + (f"  ({detail})" if detail else ""))
    sys.exit(1 if failed else 0)
