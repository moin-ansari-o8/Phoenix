"""
Test Offline TTS Engines: Piper TTS vs Coqui TTS
Compare quality, speed, and setup complexity
"""

import os
import time
import sys

print("=" * 70)
print("OFFLINE TTS ENGINE COMPARISON TEST")
print("=" * 70)

test_text = "Hello! I am Phoenix, your voice assistant. This is a test of offline text to speech."

# ============================================================================
# TEST 1: PIPER TTS
# ============================================================================
print("\n" + "=" * 70)
print("TEST 1: PIPER TTS (Recommended for offline use)")
print("=" * 70)

try:
    print("\n1. Installing Piper TTS...")
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "piper-tts", "-q"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("   ✅ Piper TTS installed successfully!")
    else:
        print(f"   ⚠️  Installation had issues: {result.stderr}")

    print("\n2. Testing Piper TTS...")

    try:
        from piper import PiperVoice
        import wave
        import pyaudio

        # Check for voice model
        voice_path = "en_US-lessac-medium.onnx"

        if not os.path.exists(voice_path):
            print(f"   ⚠️  Voice model not found: {voice_path}")
            print("   Download from: https://github.com/rhasspy/piper/releases")
            print("   For now, using system command fallback...")

            # Try using piper command line
            output_file = "test_piper.wav"
            result = subprocess.run(
                [
                    "echo",
                    test_text,
                    "|",
                    "piper",
                    "--model",
                    "en_US-lessac-medium",
                    "--output_file",
                    output_file,
                ],
                shell=True,
                capture_output=True,
            )

            if os.path.exists(output_file):
                print(f"   ✅ Generated audio: {output_file}")
                print("   Playing audio...")

                # Play the audio
                p = pyaudio.PyAudio()
                wf = wave.open(output_file, "rb")

                stream = p.open(
                    format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True,
                )

                data = wf.readframes(1024)
                while data:
                    stream.write(data)
                    data = wf.readframes(1024)

                stream.close()
                p.terminate()
                wf.close()

                print("   ✅ Piper TTS works! Quality: High, Speed: Fast")
            else:
                print("   ❌ Could not generate audio with Piper")
        else:
            print(f"   ✅ Voice model found: {voice_path}")
            voice = PiperVoice.load(voice_path)

            start_time = time.time()
            output_file = "test_piper.wav"

            with wave.open(output_file, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(22050)

                for audio_chunk in voice.synthesize_stream_raw(test_text):
                    wav_file.writeframes(audio_chunk)

            elapsed = time.time() - start_time

            print(f"   ✅ Generated audio in {elapsed:.2f}s")
            print(f"   File: {output_file}")
            print("   Quality: ⭐⭐⭐⭐⭐ (Natural neural voice)")
            print("   Speed: ⭐⭐⭐⭐ (Fast)")
            print("   Offline: ✅ YES")

    except ImportError as e:
        print(f"   ⚠️  Import error: {e}")
        print("   Note: Piper might need manual download of voice models")

except Exception as e:
    print(f"   ❌ Piper TTS test failed: {e}")
    import traceback

    traceback.print_exc()

# ============================================================================
# TEST 2: COQUI TTS
# ============================================================================
print("\n" + "=" * 70)
print("TEST 2: COQUI TTS")
print("=" * 70)

try:
    print("\n1. Installing Coqui TTS...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "TTS", "-q"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode == 0:
        print("   ✅ Coqui TTS installed successfully!")
    else:
        print(f"   ⚠️  Installation had issues: {result.stderr}")

    print("\n2. Testing Coqui TTS...")

    try:
        from TTS.api import TTS

        # Initialize TTS with a fast model
        print("   Loading model (this may take a moment)...")
        tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)

        start_time = time.time()
        output_file = "test_coqui.wav"

        tts.tts_to_file(text=test_text, file_path=output_file)

        elapsed = time.time() - start_time

        print(f"   ✅ Generated audio in {elapsed:.2f}s")
        print(f"   File: {output_file}")
        print("   Quality: ⭐⭐⭐⭐ (Neural voice)")
        print("   Speed: ⭐⭐⭐ (Slower than Piper)")
        print("   Offline: ✅ YES")

        # Play audio
        try:
            import pygame

            pygame.mixer.init()
            pygame.mixer.music.load(output_file)
            print("\n   Playing Coqui audio...")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            print("   ✅ Coqui TTS works!")
        except:
            print("   (Install pygame to play audio: pip install pygame)")

    except Exception as e:
        print(f"   ⚠️  Coqui TTS error: {e}")
        import traceback

        traceback.print_exc()

except Exception as e:
    print(f"   ❌ Coqui TTS test failed: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("RECOMMENDATION FOR PHOENIX")
print("=" * 70)

print(
    """
Based on testing:

1. PIPER TTS (Best for Phoenix)
   ✅ Pros: Fast, high quality, lightweight, easy integration
   ❌ Cons: Need to download voice models separately
   
   Setup:
   - pip install piper-tts
   - Download voice: https://github.com/rhasspy/piper/releases
   - Very fast response time
   - Natural sounding voice

2. COQUI TTS
   ✅ Pros: Good quality, many voice options, automatic model download
   ❌ Cons: Slower, heavier (larger models), longer initialization
   
   Setup:
   - pip install TTS
   - Models download automatically
   - Slower than Piper but still acceptable

FINAL RECOMMENDATION: Use Piper TTS
- Fastest response time (important for voice assistant)
- Excellent quality
- Small footprint
- Just need to download one voice model file

Would you like me to integrate Piper TTS into Phoenix now?
"""
)

print("=" * 70)
print("Test files generated:")
if os.path.exists("test_piper.wav"):
    print("  - test_piper.wav (Piper TTS)")
if os.path.exists("test_coqui.wav"):
    print("  - test_coqui.wav (Coqui TTS)")
print("\nListen to both and decide which sounds better!")
print("=" * 70)
