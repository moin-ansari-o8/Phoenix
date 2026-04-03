"""
Test Coqui TTS - Simple and Works!
Much easier than Piper TTS, still offline and high quality
"""

import os
import sys

print("=" * 70)
print("COQUI TTS TEST - Simple Offline Voice")
print("=" * 70)

print("\n1. Installing Coqui TTS...")
import subprocess

result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "TTS", "-q"], capture_output=True
)

if result.returncode == 0:
    print("   ✅ Coqui TTS installed!")
else:
    print("   ⚠️  Installation issues (may already be installed)")

print("\n2. Loading TTS model...")
print("   (First run downloads model ~200MB, then cached)")

try:
    from TTS.api import TTS

    # Use a fast, high-quality English model
    tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")

    print("   ✅ Model loaded!")

    # Test text
    test_text = "Hello! I am Phoenix, your offline voice assistant. This is a test of Coqui TTS. How do I sound?"

    print(f"\n3. Generating speech...")
    print(f'   Text: "{test_text}"')

    output_file = "coqui_test.wav"

    tts.tts_to_file(text=test_text, file_path=output_file)

    file_size = os.path.getsize(output_file) / 1024
    print(f"   ✅ Audio saved: {output_file} ({file_size:.1f} KB)")

    # Play audio
    print("\n4. Playing audio...")

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
        print(f"   Opening in default player...")
        subprocess.run(["start", "", output_file], shell=True)

    print("\n" + "=" * 70)
    print("✅ COQUI TTS WORKS PERFECTLY!")
    print("=" * 70)
    print("\n🎧 Listen to the voice quality!")
    print()
    print("Advantages:")
    print("  ✅ Works offline (after first download)")
    print("  ✅ High quality neural voice")
    print("  ✅ No format issues")
    print("  ✅ Easy integration")
    print("  ✅ No complex setup")
    print()
    print("If it sounds good, I'll integrate it into Phoenix NOW!")
    print("Phoenix will work 100% offline with great voice quality.")
    print("=" * 70)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback

    traceback.print_exc()

    print("\n" + "=" * 70)
    print("TROUBLESHOOTING:")
    print("=" * 70)
    print("If installation failed, try:")
    print("  pip install TTS --upgrade")
    print()
    print("Or use the online Edge TTS for now (requires internet)")
    print("=" * 70)
