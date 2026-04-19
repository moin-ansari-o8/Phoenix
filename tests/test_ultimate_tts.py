import os
import ctypes
import time
import subprocess
import sys

# Absolute path generation to keep things clean
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# New centralized voice directory mapping to 'voice' folder
VOICE_DIR = os.path.join(BASE_DIR, "..", "voice")

# Organize voices by gender.
# Note: Format is (model_name, directory)
GIRLS = [
    ("en_GB-jenny_dioco-medium", VOICE_DIR),
    ("en_GB-alba-medium", VOICE_DIR),
]

BOYS = [
    ("en_US-ryan-medium", VOICE_DIR),
    ("en_US-kusal-medium", VOICE_DIR),
]

test_text = "Hello Master kaly! I hope you are well. This is the test voice, Tell me if you like this voice or not. How are you by the way?"


def mci_play_audio(filepath):
    abs_path = os.path.abspath(filepath)
    alias = "ultimate_voice"
    winmm = ctypes.windll.winmm
    winmm.mciSendStringW(f"close {alias}", None, 0, None)
    winmm.mciSendStringW(f'open "{abs_path}" alias {alias}', None, 0, None)
    winmm.mciSendStringW(f"play {alias} wait", None, 0, None)
    winmm.mciSendStringW(f"close {alias}", None, 0, None)


def test_piper_tts(model_name, directory):
    try:
        model_path = os.path.join(directory, f"{model_name}.onnx")
        output_file = f"temp_ultimate_{model_name}.wav"

        if not os.path.exists(model_path):
            print(f"[!] Warning: Model file {model_path} doesn't exist, skipping...")
            return

        print(f"\n--- Testing Piper: {model_name} ---")
        start = time.time()
        proc = subprocess.run(
            ["piper", "-m", model_path, "-f", output_file],
            input=test_text,
            text=True,
            capture_output=True,
        )
        end = time.time()

        if proc.returncode != 0:
            print(f"Piper error: {proc.stderr}")
            return

        print(f"Generated offline in {end - start:.2f}s locally")
        print(f"Now playing {model_name}...")
        mci_play_audio(output_file)

        # Cleanup
        if os.path.exists(output_file):
            os.remove(output_file)
    except Exception as e:
        print(f"Failed Piper {model_name}: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide 'boy' or 'girl' as an argument! Example:")
        print("  python test_ultimate_tts.py boy")
        print("  python test_ultimate_tts.py girl")
        sys.exit(1)

    gender_arg = sys.argv[1].lower()

    if gender_arg == "girl":
        print("==== RUNNING ALL GIRL VOICES ====")
        for voice, path in GIRLS:
            test_piper_tts(voice, path)
    elif gender_arg == "boy":
        print("==== RUNNING ALL BOY VOICES ====")
        for voice, path in BOYS:
            test_piper_tts(voice, path)
    else:
        print(f"Unknown argument: '{gender_arg}'. Please just use 'boy' or 'girl'.")
