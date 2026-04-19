import os
import ctypes
import time
from TTS.api import TTS

# Coqui model: Tacotron2-DDC is generally high quality, good balance, auto-downloads
# This provides a realistic comparison to Piper/Edge
VOICE_MODEL = "tts_models/en/ljspeech/tacotron2-DDC"
VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coqui_output")


def mci_play_audio(filepath):
    abs_path = os.path.abspath(filepath)
    alias = "coqui_voice"
    winmm = ctypes.windll.winmm
    # Clean previous audio
    winmm.mciSendStringW(f"close {alias}", None, 0, None)
    # Open and play natively natively perfectly wait locks until audio exactly ends
    winmm.mciSendStringW(f'open "{abs_path}" alias {alias}', None, 0, None)
    winmm.mciSendStringW(f"play {alias} wait", None, 0, None)
    winmm.mciSendStringW(f"close {alias}", None, 0, None)


def generate_and_play():
    os.makedirs(VOICES_DIR, exist_ok=True)
    out_wav = os.path.join(VOICES_DIR, "coqui_test.wav")

    print(f"📦 Loading Coqui Model: {VOICE_MODEL}")
    print("   (This will auto-download on first run. It may take a while...)")
    start_load = time.time()
    tts = TTS(model_name=VOICE_MODEL)
    print(f"✅ Loaded in {time.time() - start_load:.2f} seconds.\n")

    text = "Hello, I am testing Coqui's local neural speech. This might take a bit longer but the quality should be excellent."

    print("⚙️ Generating speech...")
    start_gen = time.time()
    tts.tts_to_file(text=text, file_path=out_wav)
    print(f"⚡ Generation took {time.time() - start_gen:.2f} seconds.\n")

    print("▶️ Playing Coqui voice natively...")
    mci_play_audio(out_wav)
    print("✅ Finished playing.")


if __name__ == "__main__":
    print("--- 🚀 Coqui TTS Local Test ---")
    try:
        generate_and_play()
        print("\n🎉 Coqui Test Complete!")
    except Exception as e:
        print(f"❌ Error running Coqui TTS: {e}")
        print(
            "\nNote: Coqui requires heavy dependencies. If it crashed here, it might be due to missing Visual Studio C++ libraries or Python version incompatibility (it usually prefers Py 3.9/3.10 and specific PyTorch versions)."
        )
