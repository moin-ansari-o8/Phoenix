"""
Enrol your voice so Phoenix can tell you from everyone else in the room.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\tests\\enroll_voice.py

Records ~20 short phrases through Phoenix's own microphone path, turns them into
speaker embeddings and writes `data/speaker_profile.npz`.

## Record the way you actually talk

The profile captures the room and the microphone, not just your vocal cords. So:

  * sit where you normally sit, at your normal distance from the mic,
  * talk at your normal speed and volume - do not enunciate for the machine,
  * leave the room as it normally is. If a fan is usually running, leave it on.

Recording somewhere else, or on another device, produces a profile of "you over
there" and your everyday voice will score as a stranger.

## After enrolling

Verification stays in `log` mode (`core/config.json` ->
`security.speaker_verification.mode`). Phoenix keeps answering everyone, but
prints a `[SPEAKER]` score for every utterance. Watch those numbers for a few
days - yours and other people's - then set the threshold between the two and
switch the mode to `"gate"`.

Re-run this script any time to replace the profile. Existing WAVs in
`data/voice_enroll/owner/` are reused, so you can also drop in your own
recordings (16 kHz mono 16-bit WAV) instead of speaking the prompts.
"""

import os
import sys
import time
import wave

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Utils.limbs.audio_capture import SAMPLE_RATE, MicStream
from Utils.limbs.speaker_id import PROFILE_FILE, SpeakerVerifier, build_profile, profile_spread

ENROLL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "voice_enroll",
    "owner",
)

# Varied on purpose: commands, questions, and one long sentence. A profile built
# only from "phoenix" three-word commands describes how you say those three
# words, not how you speak.
PHRASES = [
    "Phoenix, what is the time",
    "Open brave for me",
    "Set the volume to forty percent",
    "How much battery do I have left",
    "Play sahiba",
    "Phoenix, increase the brightness a little",
    "What is the weather looking like today",
    "Remind me to call mom at six in the evening",
    "Close spotify please",
    "Take a screenshot",
    "Phoenix, are you listening to me right now",
    "Set a timer for ten minutes",
    "Play vhalam aavo ne",
    "What did you just say, I could not hear you",
    "Tell me something interesting about the ocean",
    "Turn the volume down a bit, it is too loud in here",
    "Who am I and what do you know about me",
    "Phoenix, restart yourself",
    "I have been working on this project for a while now and I think it is finally coming together",
    "Thanks Phoenix, that is all for now",
]

MIN_SECONDS = 1.5
MAX_SECONDS = 8.0


def record_phrase(mic, seconds=5.0):
    """Capture `seconds` of audio from the live mic stream."""
    frames = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        frame = mic.read(timeout=0.2)
        if frame is not None:
            frames.append(frame.samples)
    if not frames:
        return np.zeros(0, dtype=np.int16)
    return np.concatenate(frames).astype(np.int16)


def save_wav(path, audio):
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(audio.tobytes())


def load_wav(path):
    with wave.open(path, "rb") as handle:
        if handle.getframerate() != SAMPLE_RATE or handle.getnchannels() != 1:
            raise ValueError(
                f"{os.path.basename(path)} must be {SAMPLE_RATE} Hz mono 16-bit"
            )
        return np.frombuffer(handle.readframes(handle.getnframes()), dtype=np.int16)


def voiced_ratio(audio):
    """Rough share of the clip that is above the noise floor."""
    if audio.size == 0:
        return 0.0
    frame = 512
    count = len(audio) // frame
    if count == 0:
        return 0.0
    blocks = audio[: count * frame].reshape(count, frame).astype(np.float32)
    rms = np.sqrt(np.mean(blocks**2, axis=1))
    return float(np.mean(rms > max(np.percentile(rms, 20) * 3.0, 120.0)))


def record_all():
    os.makedirs(ENROLL_DIR, exist_ok=True)
    mic = MicStream()
    mic.start()
    print("\nMicrophone open. Speak normally, at your usual distance.\n")
    time.sleep(1.0)

    saved = 0
    try:
        for index, phrase in enumerate(PHRASES, start=1):
            path = os.path.join(ENROLL_DIR, f"enroll_{index:02d}.wav")
            while True:
                print(f"[{index:2d}/{len(PHRASES)}] Say:  \"{phrase}\"")
                input("          press Enter, then speak...")
                mic.flush()
                audio = record_phrase(mic, seconds=5.0)
                duration = len(audio) / SAMPLE_RATE
                ratio = voiced_ratio(audio)

                if duration < MIN_SECONDS:
                    print(f"          too short ({duration:.1f}s) - again\n")
                    continue
                if ratio < 0.10:
                    print(f"          barely any speech detected ({ratio:.0%}) - again\n")
                    continue

                save_wav(path, audio)
                saved += 1
                print(f"          saved ({duration:.1f}s, {ratio:.0%} voiced)\n")
                break
    except KeyboardInterrupt:
        print("\nStopped early - building a profile from what was recorded.")
    finally:
        mic.stop()
    return saved


def build():
    verifier = SpeakerVerifier(enabled=True)
    if verifier._get_encoder() is None:
        print("\nThe speaker encoder could not be loaded. Install it with:")
        print("    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe -m pip install resemblyzer")
        print("\nNOTE: if pip also installs a package called `typing`, uninstall it")
        print("      immediately - it shadows the standard library on Python 3.11.")
        return 1

    wavs = sorted(
        os.path.join(ENROLL_DIR, name)
        for name in os.listdir(ENROLL_DIR)
        if name.lower().endswith(".wav")
    )
    if len(wavs) < 5:
        print(f"\nOnly {len(wavs)} recordings found - need at least 5 for a usable profile.")
        return 1

    embeddings = []
    for path in wavs:
        try:
            audio = load_wav(path)
        except ValueError as exc:
            print(f"  skipped {os.path.basename(path)}: {exc}")
            continue
        embedding = verifier.embed(audio)
        if embedding is None:
            print(f"  skipped {os.path.basename(path)}: no usable speech")
            continue
        embeddings.append(embedding)

    if len(embeddings) < 5:
        print(f"\nOnly {len(embeddings)} usable recordings - re-record in a quieter moment.")
        return 1

    profile = build_profile(embeddings)
    os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
    np.savez(PROFILE_FILE, **profile)

    spread = profile_spread(profile["embeddings"])
    print(f"\nProfile written: {PROFILE_FILE}")
    print(f"  {len(embeddings)} utterances enrolled")
    print(f"  self-similarity  min {spread['min']:.2f}  mean {spread['mean']:.2f}")

    # A loose profile means the samples disagree about what you sound like, and
    # any threshold picked from it will be wrong in both directions.
    if spread["mean"] < 0.75:
        print("\n  WARNING: the samples do not agree well with each other.")
        print("  Something varied between takes - background noise, distance, or")
        print("  another voice in a recording. Delete data/voice_enroll/owner and")
        print("  record again in one sitting.")
    elif spread["min"] < 0.60:
        print("\n  NOTE: at least one recording is an outlier. If scores look odd")
        print("  later, delete that file and rebuild.")
    else:
        print("\n  Spread looks healthy.")

    print("\nNext: leave mode on \"log\" in core/config.json, use Phoenix normally,")
    print("and watch the [SPEAKER] scores. Set the threshold between your scores")
    print("and other people's before switching mode to \"gate\".")
    return 0


if __name__ == "__main__":
    print(__doc__)
    if "--build-only" not in sys.argv:
        if os.path.isdir(ENROLL_DIR) and any(
            n.lower().endswith(".wav") for n in os.listdir(ENROLL_DIR)
        ):
            answer = input("Existing recordings found. Re-record them? [y/N] ").strip().lower()
            if answer == "y":
                record_all()
        else:
            record_all()
    sys.exit(build())
