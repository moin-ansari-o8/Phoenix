"""
Live microphone meter - run this and watch it while you talk.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\tests\\mic_check.py

Shows, in real time, exactly what Phoenix's listener sees: signal level, the
adaptive threshold, and Silero's speech probability per frame. When it stops it
saves the recording and transcribes it, so you can tell the difference between
"the mic is not picking up my voice" and "the mic is fine, the detector is
mistuned" -- which are indistinguishable from the outside.

Ctrl+C to stop early. Optional args: seconds (default 30), output wav path.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Utils.limbs.audio_capture import (
    FRAME_MS,
    SAMPLE_RATE,
    MicStream,
    NoiseFloor,
    VoiceDetector,
    select_input_device,
)

DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
OUT_WAV = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "mic_check_recording.wav"
)

BAR_WIDTH = 34
BAR_FULL_SCALE = 4000.0  # RMS that fills the bar


def bar(value, marker_at=None):
    filled = int(min(1.0, value / BAR_FULL_SCALE) * BAR_WIDTH)
    cells = ["#" if i < filled else "-" for i in range(BAR_WIDTH)]
    if marker_at is not None:
        pos = int(min(1.0, marker_at / BAR_FULL_SCALE) * BAR_WIDTH)
        if 0 <= pos < BAR_WIDTH and cells[pos] == "-":
            cells[pos] = "|"
    return "".join(cells)


def main():
    detector = VoiceDetector()
    noise_floor = NoiseFloor()
    mic = MicStream()
    mic.start()

    print(f"VAD backend : {detector.backend}")
    print(f"Input device: {mic.device_index}")
    print()
    print("TALK NOW. The bar is your signal, '|' is the threshold it must beat.")
    print("'SPEECH' means Silero recognised your voice.\n")

    captured = []
    speech_frames = 0
    veto_blocked = 0
    deadline = time.time() + DURATION
    last_draw = 0.0

    try:
        while time.time() < deadline:
            frame = mic.read(timeout=0.2)
            if frame is None:
                continue
            captured.append(frame.samples)

            prob = detector.speech_probability(frame)
            is_speech = prob >= detector.threshold
            loud = noise_floor.is_loud_enough(frame.rms)
            if is_speech:
                speech_frames += 1
                if not loud:
                    veto_blocked += 1
            else:
                noise_floor.update(frame.rms)

            now = time.time()
            if now - last_draw >= 0.1:
                last_draw = now
                label = "SPEECH" if (is_speech and loud) else (
                    "vetoed" if is_speech else "      "
                )
                sys.stdout.write(
                    f"\r[{bar(frame.rms, noise_floor.threshold)}] "
                    f"rms{frame.rms:6.0f} thr{noise_floor.threshold:6.0f} "
                    f"p={prob:4.2f} {label}"
                )
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        mic.stop()

    print("\n" + "=" * 66)
    if not captured:
        print("No audio captured at all - the microphone is not delivering data.")
        return 1

    audio = np.concatenate(captured)
    seconds = len(audio) / SAMPLE_RATE
    rms = np.array([float(np.sqrt(np.mean(c.astype(np.float32) ** 2))) for c in captured])

    print(f"recorded          : {seconds:.1f}s")
    print(f"level median/peak : {np.median(rms):.0f} / {rms.max():.0f}")
    print(f"Silero speech     : {speech_frames} frames "
          f"({speech_frames * FRAME_MS / 1000:.1f}s)")
    print(f"blocked by energy : {veto_blocked} frames")

    import wave

    with wave.open(OUT_WAV, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(audio.tobytes())
    print(f"saved             : {OUT_WAV}")

    # Transcribe regardless of what the VAD thought. If Whisper can read this
    # back, the microphone is fine and any miss is the detector's fault.
    print("\ntranscribing the whole recording (ignoring the VAD)...")
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=6)
        segments, _ = model.transcribe(
            audio.astype(np.float32) / 32768.0,
            language="en",
            beam_size=1,
            condition_on_previous_text=False,
            vad_filter=False,
        )
        text = " ".join(s.text for s in segments).strip()
        print(f"Whisper heard     : {text!r}")

        print("\nVERDICT:")
        if text and speech_frames > 10:
            print("  Microphone and detector are both working.")
        elif text:
            print("  The MICROPHONE IS FINE - Whisper read your voice back - but Silero")
            print("  did not flag it as speech. The detector is mistuned for this mic.")
        elif speech_frames > 10:
            print("  Silero heard speech but Whisper produced nothing. Odd; check levels.")
        else:
            print("  Neither Whisper nor Silero found speech. If you were definitely")
            print("  talking, this microphone is not capturing your voice - check the")
            print("  Windows input device, its level, and any noise-cancelling feature.")
    except Exception as exc:
        print(f"  (transcription unavailable: {exc})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
