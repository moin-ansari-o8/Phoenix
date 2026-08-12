"""
Say a Hindi song name and see what each STT config actually hears.

Built because "sahiba" was coming out as "saiva saum" and there was no way to
tell whether the fix should be the model, the beam width, or the lexicon. The
answer to that is empirical and it depends on YOUR voice and YOUR microphone,
so guessing from a benchmark on an English test clip is not good enough.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\scripts\\utilities\\stt_ab.py

It records a few seconds, then transcribes the SAME audio through every
configuration and shows what each produced, plus what the song lexicon would
resolve it to. Nothing is changed - it only reports.
"""

import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np  # noqa: E402

RECORD_SECONDS = 5
SAMPLE_RATE = 16000

# (model, beam). The first row is what Phoenix used before 2026-08-12.
CONFIGS = [
    ("base.en", 1),
    ("base.en", 5),
    ("base", 1),
    ("base", 5),
]


def record(seconds=RECORD_SECONDS):
    import pyaudio

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=1024,
    )
    print(f"\nSpeak now - {seconds} seconds. Say it exactly as you would to Phoenix.")
    print("   e.g.  \"play sahiba\"\n")
    frames = []
    for _ in range(int(SAMPLE_RATE / 1024 * seconds)):
        frames.append(stream.read(1024, exception_on_overflow=False))
    print("Done recording.\n")
    stream.stop_stream()
    stream.close()
    pa.terminate()
    audio = np.frombuffer(b"".join(frames), dtype=np.int16)
    return audio.astype(np.float32) / 32768.0


def main():
    from faster_whisper import WhisperModel
    from Utils.limbs.lexicon import get_lexicon

    lexicon = get_lexicon()
    try:
        hotwords = ", ".join(lexicon.hotwords()) if hasattr(lexicon, "hotwords") else ""
    except Exception:
        hotwords = ""

    audio = record()

    print(f"{'model':9} {'beam':>4}  {'secs':>5}  transcript")
    print("-" * 78)

    for model_name, beam in CONFIGS:
        try:
            model = WhisperModel(
                model_name, device="cpu", compute_type="int8", cpu_threads=6
            )
        except Exception as exc:
            print(f"{model_name:9} {beam:>4}  load failed: {exc}")
            continue

        started = time.time()
        kwargs = {"language": "en", "beam_size": beam}
        if hotwords:
            kwargs["hotwords"] = hotwords
        segments, _ = model.transcribe(audio, **kwargs)
        text = " ".join(s.text for s in segments).strip()
        elapsed = time.time() - started

        print(f"{model_name:9} {beam:>4}  {elapsed:5.2f}  {text!r}")

        # What the song matcher would do with it.
        try:
            slot = lexicon.extract_song_slot(text) or text
            best = lexicon.resolve_song(slot, min_score=0)
            if best:
                print(f"{'':16}  -> song match: {best[0]!r} at {best[1]:.0f}%")
        except Exception:
            pass

        del model

    print(
        "\nA match below ~60% is a wrong song. If every row is wrong, the title is\n"
        "not in data/songs.txt or the microphone did not get a clean recording."
    )


if __name__ == "__main__":
    main()
