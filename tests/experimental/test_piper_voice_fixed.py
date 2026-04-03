"""
Test Piper TTS Voice - FIXED API
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
print(f"\n✅ Using voice: {voice_file}")

# Test text
test_text = "Hello! I am Phoenix, your offline voice assistant. This is a test of Piper TTS. How do I sound?"

print(f'\n📝 Text: "{test_text}"')
print("\n🔊 Generating speech...")

try:
    # Try using piper-tts Python package
    try:
        from piper.voice import PiperVoice

        print("   Using piper-tts Python library...")
        voice = PiperVoice.load(voice_file)

        # Generate audio - New API
        output_file = "test_piper_output.wav"

        with open(output_file, "wb") as f:
            voice.synthesize(test_text, f)

        print(f"   ✅ Audio saved: {output_file}")

    except (ImportError, AttributeError) as e:
        print(f"   Python library issue ({e})")
        print("   Trying piper command line...")
        import subprocess

        output_file = "test_piper_output.wav"

        # Try piper executable
        result = subprocess.run(
            ["piper", "--model", voice_file, "--output_file", output_file],
            input=test_text.encode(),
            capture_output=True,
        )

        if result.returncode != 0:
            # Try with echo pipe (Windows)
            result = subprocess.run(
                f"echo {test_text} | piper --model {voice_file} --output_file {output_file}",
                shell=True,
                capture_output=True,
            )

            if result.returncode != 0:
                raise Exception(
                    f"Piper command failed. Install piper executable or use pip install piper-tts"
                )

        print(f"   ✅ Audio saved: {output_file}")

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

    except ImportError:
        print("   ⚠️  pygame not installed for playback")
        print("      Install: pip install pygame")
        print(f"      Or play manually: {output_file}")

        # Try Windows media player
        try:
            import subprocess

            subprocess.run(["start", output_file], shell=True)
            print(f"   🎵 Opening in default player...")
        except:
            pass

    print("\n" + "=" * 70)
    print("✅ PIPER TTS WORKS!")
    print("=" * 70)
    print("\nIf the voice sounds good, I can integrate it into Phoenix!")
    print("It will replace Edge TTS and work 100% offline.")
    print("\nLet me know which voice you prefer!")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()

    print("\n" + "=" * 70)
    print("TROUBLESHOOTING:")
    print("=" * 70)
    print("1. Install piper-tts Python package:")
    print("   pip install piper-tts")
    print()
    print("2. Or download piper executable:")
    print("   https://github.com/rhasspy/piper/releases")
    print("   Extract and add to PATH")
    print()
    print("3. Make sure voice files (.onnx and .json) are in piper_voices/")
    print("=" * 70)
