"""
Download Piper TTS Voices for Phoenix - FIXED URLS
Automatically downloads high-quality neural voices from HuggingFace
"""

import os
import urllib.request

print("=" * 70)
print("PIPER TTS VOICE DOWNLOADER (HuggingFace)")
print("=" * 70)

# Create voices directory
voices_dir = "piper_voices"
os.makedirs(voices_dir, exist_ok=True)
print(f"\n✅ Voices will be saved to: {voices_dir}/")

# HuggingFace base URL
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US"

# Recommended voices (high quality, good for assistants)
VOICES = {
    "1": {
        "name": "en_US-lessac-medium (Male, Natural) - RECOMMENDED",
        "model": f"{HF_BASE}/lessac/medium/en_US-lessac-medium.onnx",
        "config": f"{HF_BASE}/lessac/medium/en_US-lessac-medium.onnx.json",
        "size": "~63 MB",
        "quality": "⭐⭐⭐⭐⭐",
    },
    "2": {
        "name": "en_US-amy-medium (Female, Clear)",
        "model": f"{HF_BASE}/amy/medium/en_US-amy-medium.onnx",
        "config": f"{HF_BASE}/amy/medium/en_US-amy-medium.onnx.json",
        "size": "~63 MB",
        "quality": "⭐⭐⭐⭐⭐",
    },
    "3": {
        "name": "en_US-libritts_r-medium (Male, Very Natural)",
        "model": f"{HF_BASE}/libritts_r/medium/en_US-libritts_r-medium.onnx",
        "config": f"{HF_BASE}/libritts_r/medium/en_US-libritts_r-medium.onnx.json",
        "size": "~63 MB",
        "quality": "⭐⭐⭐⭐⭐",
    },
    "4": {
        "name": "en_US-ryan-medium (Male, Deep Voice)",
        "model": f"{HF_BASE}/ryan/medium/en_US-ryan-medium.onnx",
        "config": f"{HF_BASE}/ryan/medium/en_US-ryan-medium.onnx.json",
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
        print(f"  Downloading: {os.path.basename(filename)}...", end=" ", flush=True)
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
        file_size = os.path.getsize(model_filename) / (1024 * 1024)
        print(f"  ℹ️  Already downloaded! ({file_size:.1f} MB) Skipping...")
        return True

    # Download model
    if not download_file(voice_info["model"], model_filename):
        return False

    # Download config
    if not download_file(voice_info["config"], config_filename):
        return False

    return True


# Download selected voice(s)
success_count = 0
if choice == "all":
    print("\n📥 Downloading all voices...")
    for voice_info in VOICES.values():
        if download_voice(voice_info):
            success_count += 1
elif choice in VOICES:
    print(f"\n📥 Downloading voice {choice}...")
    if download_voice(VOICES[choice]):
        success_count += 1
else:
    print("❌ Invalid choice!")
    exit(1)

print("\n" + "=" * 70)
if success_count > 0:
    print(f"✅ DOWNLOAD COMPLETE! ({success_count} voice(s))")
else:
    print("⚠️  No voices downloaded successfully")
print("=" * 70)

# List downloaded files
print(f"\nDownloaded voices in {voices_dir}/:")
voices_found = False
for file in os.listdir(voices_dir):
    if file.endswith(".onnx"):
        voices_found = True
        size = os.path.getsize(os.path.join(voices_dir, file)) / (1024 * 1024)
        print(f"  ✅ {file} ({size:.1f} MB)")

if not voices_found:
    print("  (No voices downloaded yet)")

print("\n" + "=" * 70)
print("NEXT STEPS:")
print("=" * 70)
print("1. Test the voice:")
print(f"   python test_piper_voice.py")
print()
print("2. Or I can integrate into Phoenix:")
print("   Replace Edge TTS with Piper TTS (offline)")
print()
print("   Piper TTS = Offline + Fast + High Quality! 🎤")
print("=" * 70)
