import os
import ctypes
import time
import subprocess
import urllib.request

# Define Voices for Piper
# Phoenix equivalent (British/Irish/English Female) -> Alba
# Igris equivalent (North American Male) -> Ryan
VOICES = {
    "Phoenix_Alba": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx.json",
        "filename": "en_GB-alba-medium.onnx",
    },
    "Igris_Ryan": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx.json",
        "filename": "en_US-ryan-medium.onnx",
    },
}

VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "piper_models")


def mci_play_audio(filepath):
    abs_path = os.path.abspath(filepath)
    alias = "piper_voice"
    winmm = ctypes.windll.winmm
    # Clean previous audio
    winmm.mciSendStringW(f"close {alias}", None, 0, None)
    # Open and play natively
    winmm.mciSendStringW(f'open "{abs_path}" alias {alias}', None, 0, None)
    winmm.mciSendStringW(f"play {alias} wait", None, 0, None)
    winmm.mciSendStringW(f"close {alias}", None, 0, None)


def download_file(url, dest):
    if not os.path.exists(dest):
        print(f"    ⬇️ Downloading {os.path.basename(dest)}...")
        urllib.request.urlretrieve(url, dest)
        print("    ✅ Downloaded.")


def download_models():
    os.makedirs(VOICES_DIR, exist_ok=True)
    print("📦 Checking/Downloading Piper Models...")
    for voice_name, urls in VOICES.items():
        print(f"  -> {voice_name}")
        base_path = os.path.join(VOICES_DIR, urls["filename"])
        download_file(urls["onnx"], base_path)
        download_file(urls["json"], base_path + ".json")


def generate_and_play(text, voice_name):
    model_path = os.path.join(VOICES_DIR, VOICES[voice_name]["filename"])
    out_wav = os.path.join(VOICES_DIR, f"out_{voice_name}.wav")

    print(f"⚙️ Generating speech for {voice_name}...")
    start_time = time.time()

    # Run Piper via CLI
    process = subprocess.run(
        ["piper", "--model", model_path, "--output_file", out_wav],
        input=text.encode("utf-8"),
        capture_output=True,
    )

    if process.returncode != 0:
        print(f"❌ Error generating Piper TTS: {process.stderr.decode('utf-8')}")
        return

    elapsed = time.time() - start_time
    print(f"⚡ Generation took {elapsed:.2f} seconds.")

    print(f"▶️ Playing {voice_name}...")
    mci_play_audio(out_wav)
    print("✅ Finished playing.\n")


if __name__ == "__main__":
    print("--- 🚀 Piper TTS Local Test ---")
    download_models()

    generate_and_play(
        "Hello, I am Phoenix. This is a purely local neural playback, functioning offline without stutter.",
        "Phoenix_Alba",
    )

    generate_and_play(
        "And I am Igris. Ready for deployment with real-time local processing.",
        "Igris_Ryan",
    )

    print("🎉 Piper Test Complete!")
