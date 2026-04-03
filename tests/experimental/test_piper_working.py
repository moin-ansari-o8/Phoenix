"""
Test Piper TTS Voice - FIXED WAV FORMAT
Properly formats the audio as a valid WAV file
"""

import os
import sys
import wave
import json

print("=" * 70)
print("PIPER TTS VOICE TEST (Fixed WAV Format)")
print("=" * 70)

# Find voice files
voices_dir = "piper_voices"
if not os.path.exists(voices_dir):
    print(f"\n❌ {voices_dir}/ directory not found!")
    print("   Run: python download_piper_voices_fixed.py")
    sys.exit(1)

voices = [f for f in os.listdir(voices_dir) if f.endswith(".onnx")]
if not voices:
    print(f"\n❌ No voice files found in {voices_dir}/")
    print("   Run: python download_piper_voices_fixed.py")
    sys.exit(1)

print(f"\n✅ Found {len(voices)} voice(s):")
for i, voice in enumerate(voices, 1):
    print(f"  {i}. {voice}")

if len(voices) == 1:
    choice = 1
else:
    choice = int(input(f"\nChoose voice to test (1-{len(voices)}): "))

voice_file = os.path.join(voices_dir, voices[choice - 1])
config_file = voice_file + ".json"

print(f"\n✅ Using voice: {voice_file}")

# Load config to get audio parameters
with open(config_file, "r") as f:
    config = json.load(f)
    sample_rate = config["audio"]["sample_rate"]
    print(f"   Sample rate: {sample_rate} Hz")

# Test text
test_text = "Hello! I am Phoenix, your offline voice assistant. This is a test of Piper TTS. How do I sound?"

print(f'\n📝 Text: "{test_text}"')
print("\n🔊 Generating speech...")

try:
    from piper.voice import PiperVoice

    print("   Loading voice model...")
    voice = PiperVoice.load(voice_file)

    # Generate audio to temporary raw file
    output_file = "test_piper_output.wav"
    raw_audio = []

    print("   Synthesizing audio...")

    # Use the synthesize_stream_raw method to get raw audio data
    for audio_bytes in voice.synthesize_stream_raw(test_text):
        raw_audio.append(audio_bytes)

    # Combine all audio data
    audio_data = b"".join(raw_audio)

    print(f"   Generated {len(audio_data)} bytes of audio")

    # Write properly formatted WAV file
    print("   Writing WAV file...")
    with wave.open(output_file, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data)

    file_size = os.path.getsize(output_file) / 1024
    print(f"   ✅ Audio saved: {output_file} ({file_size:.1f} KB)")

    # Play audio
    print("\n🎵 Playing audio...")

    try:
        import pygame

        pygame.mixer.init()
        pygame.mixer.music.load(output_file)
        pygame.mixer.music.play()

        import time

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        print("   ✅ Playback complete!")

    except Exception as e:
        print(f"   ⚠️  pygame playback failed: {e}")
        print("   Trying Windows media player...")

        # Try Windows media player
        import subprocess

        subprocess.run(["start", "", output_file], shell=True)
        print(f"   🎵 Opened in default player")

    print("\n" + "=" * 70)
    print("✅ PIPER TTS WORKS!")
    print("=" * 70)
    print("\n🎧 Listen to the voice!")
    print("If it sounds good, I'll integrate it into Phoenix.")
    print("Phoenix will then work 100% offline with high-quality voice!")

except AttributeError:
    print("\n⚠️  The piper-tts API has changed. Trying alternative method...")

    # Alternative: use onnxruntime directly
    try:
        import onnxruntime as ort
        import numpy as np

        print("   Using ONNX Runtime directly...")

        # This is more complex but works with any version
        # For now, let's just use a simpler subprocess approach
        raise ImportError("Using subprocess fallback")

    except:
        print("   Using piper executable...")
        import subprocess

        output_file = "test_piper_output_raw.bin"

        # Generate raw audio
        result = subprocess.run(
            ["piper", "--model", voice_file, "--output-raw"],
            input=test_text.encode(),
            capture_output=True,
        )

        if result.returncode == 0:
            # Convert raw to WAV
            raw_audio = result.stdout

            wav_file = "test_piper_output.wav"
            with wave.open(wav_file, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(raw_audio)

            print(f"   ✅ Audio saved: {wav_file}")

            # Play it
            import subprocess

            subprocess.run(["start", "", wav_file], shell=True)
            print(f"   🎵 Opened in default player")
        else:
            print("   ❌ Piper executable not found or failed")
            print("   Install: pip install piper-tts")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()

    print("\n" + "=" * 70)
    print("ALTERNATIVE: Use Coqui TTS instead")
    print("=" * 70)
    print("Coqui TTS is easier to use:")
    print("  pip install TTS")
    print("  (works out of the box, no format issues)")
    print("=" * 70)
