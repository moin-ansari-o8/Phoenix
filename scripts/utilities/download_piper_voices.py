"""
Download Piper TTS Voices for Phoenix
Automatically downloads high-quality neural voices
"""

import os
import urllib.request
import json

print("=" * 70)
print("PIPER TTS VOICE DOWNLOADER")
print("=" * 70)

# Create voices directory
voices_dir = "piper_voices"
os.makedirs(voices_dir, exist_ok=True)
print(f"\n✅ Voices will be saved to: {voices_dir}/")

# Recommended voices (high quality, good for assistants)
VOICES = {
    "1": {
        "name": "en_US-lessac-medium (Male, Natural) - RECOMMENDED",
        "model": "https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx",
        "config": "https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-lessac-medium.onnx.json",
        "size": "~63 MB",
        "quality": "⭐⭐⭐⭐⭐",
    },
    "2": {
        "name": "en_US-amy-medium (Female, Clear)",
        "model": "https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-amy-medium.onnx",
        "config": "https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-amy-medium.onnx.json",
        "size": "~63 MB",
        "quality": "⭐⭐⭐⭐⭐",
    },
    "3": {
        "name": "en_US-libritts-high (Male, Very Natural) - HIGH QUALITY",
        "model": "https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-libritts-high.onnx",
        "config": "https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-libritts-high.onnx.json",
        "size": "~100 MB",
        "quality": "⭐⭐⭐⭐⭐",
    },
    "4": {
        "name": "en_US-ryan-medium (Male, Deep Voice)",
        "model": "https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-ryan-medium.onnx",
        "config": "https://github.com/rhasspy/piper/releases/download/v1.2.0/en_US-ryan-medium.onnx.json",
        "size": "~63 MB",
        "quality": "⭐⭐⭐⭐",
    },
}

print("\nAvailable voices:")
for key, voice in VOICES.items():
    print(f"  {key}. {voice['name']}")
    print(f"     Size: {voice['size']}, Quality: {voice['quality']}")
    print()

choice = (
    input("Choose voice to download (1-4, or 'all' for all voices): ").strip().lower()
)


def download_file(url, filename):
    """Download file with progress"""
    try:
        print(f"  Downloading: {os.path.basename(filename)}...", end=" ")
        urllib.request.urlretrieve(url, filename)
        file_size = os.path.getsize(filename) / (1024 * 1024)
        print(f"✅ Done ({file_size:.1f} MB)")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def download_voice(voice_info):
    """Download both model and config for a voice"""
    model_filename = os.path.join(voices_dir, os.path.basename(voice_info["model"]))
    config_filename = os.path.join(voices_dir, os.path.basename(voice_info["config"]))

    print(f"\nDownloading: {voice_info['name']}")
    print(f"  Model: {os.path.basename(model_filename)}")

    # Check if already exists
    if os.path.exists(model_filename) and os.path.exists(config_filename):
        print(f"  ℹ️  Already downloaded! Skipping...")
        return True

    # Download model
    if not download_file(voice_info["model"], model_filename):
        return False

    # Download config
    if not download_file(voice_info["config"], config_filename):
        return False

    return True


# Download selected voice(s)
if choice == "all":
    print("\n📥 Downloading all voices...")
    for voice_info in VOICES.values():
        download_voice(voice_info)
elif choice in VOICES:
    print(f"\n📥 Downloading voice {choice}...")
    download_voice(VOICES[choice])
else:
    print("❌ Invalid choice!")
    exit(1)

print("\n" + "=" * 70)
print("✅ DOWNLOAD COMPLETE!")
print("=" * 70)

# List downloaded files
print(f"\nDownloaded voices in {voices_dir}/:")
for file in os.listdir(voices_dir):
    if file.endswith(".onnx"):
        size = os.path.getsize(os.path.join(voices_dir, file)) / (1024 * 1024)
        print(f"  ✅ {file} ({size:.1f} MB)")

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print("1. Test the voice:")
print(f"   python test_piper_voice.py")
print()
print("2. Or integrate into Phoenix:")
print("   I can update HelperPHNX.py to use Piper TTS instead of Edge TTS")
print()
print("   Piper TTS = Offline + Fast + High Quality! 🎤")
print("=" * 70)
