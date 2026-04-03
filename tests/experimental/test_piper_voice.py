"""
Test Piper TTS Voice
Quick test to hear the downloaded voice
"""

import os
import sys

print("=" * 70)
print("PIPER TTS VOICE TEST")
print("=" * 70)

# Find voice files
voices_dir = "piper_voices"
if not os.path.exists(voices_dir):
    print(f"\n❌ {voices_dir}/ directory not found!")
    print("   Run: python download_piper_voices.py")
    sys.exit(1)

voices = [f for f in os.listdir(voices_dir) if f.endswith(".onnx")]
if not voices:
    print(f"\n❌ No voice files found in {voices_dir}/")
    print("   Run: python download_piper_voices.py")
    sys.exit(1)

print(f"\n✅ Found {len(voices)} voice(s):")
for i, voice in enumerate(voices, 1):
    print(f"  {i}. {voice}")

if len(voices) == 1:
    choice = 1
else:
    choice = int(input(f"\nChoose voice to test (1-{len(voices)}): "))

voice_file = os.path.join(voices_dir, voices[choice - 1])
print(f"\n✅ Using voice: {voice_file}")

# Test text
test_text = "Hello! I am Phoenix, your offline voice assistant. This is a test of Piper TTS. How do I sound?"

print(f'\n📝 Text: "{test_text}"')
print("\n🔊 Generating speech...")

try:
    # Try using piper-tts Python package
    try:
        from piper.voice import PiperVoice
        import wave
        import io

        print("   Using piper-tts Python library...")
        voice = PiperVoice.load(voice_file)

        # Generate audio
        audio_data = io.BytesIO()
        with wave.open(audio_data, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)

            for chunk in voice.synthesize_stream_raw(test_text):
                wav_file.writeframes(chunk)

        # Save to file
        output_file = "test_piper_output.wav"
        with open(output_file, "wb") as f:
            f.write(audio_data.getvalue())

        print(f"   ✅ Audio saved: {output_file}")

    except ImportError:
        print("   Trying piper command line...")
        import subprocess

        output_file = "test_piper_output.wav"
        result = subprocess.run(
            ["piper", "--model", voice_file, "--output_file", output_file],
            input=test_text.encode(),
            capture_output=True,
        )

        if result.returncode != 0:
            raise Exception(f"Piper command failed: {result.stderr.decode()}")

        print(f"   ✅ Audio saved: {output_file}")

    # Play audio
    print("\n🎵 Playing audio...")

    try:
        import pygame

        pygame.mixer.init()
        pygame.mixer.music.load(output_file)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            import time

            time.sleep(0.1)

        print("   ✅ Playback complete!")

    except ImportError:
        print("   ⚠️  pygame not installed for playback")
        print("      Install: pip install pygame")
        print(f"      Or play manually: {output_file}")

    print("\n" + "=" * 70)
    print("✅ PIPER TTS WORKS!")
    print("=" * 70)
    print("\nIf the voice sounds good, I can integrate it into Phoenix!")
    print("It will replace Edge TTS and work 100% offline.")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()

    print("\n" + "=" * 70)
    print("TROUBLESHOOTING:")
    print("=" * 70)
    print("1. Make sure piper-tts is installed:")
    print("   pip install piper-tts")
    print()
    print("2. Or install piper command line tool:")
    print("   https://github.com/rhasspy/piper")
    print()
    print("3. Make sure voice files are in piper_voices/")
    print("=" * 70)
