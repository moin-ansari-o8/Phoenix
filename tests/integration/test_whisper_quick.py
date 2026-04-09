"""Quick test to verify Faster-Whisper integration"""

import tkinter as tk
import sys

print("=" * 50)
print("Testing Faster-Whisper Integration")
print("=" * 50)

# Test import
try:
    from faster_whisper import WhisperModel

    print("✅ faster-whisper imported successfully")
except ImportError as e:
    print(f"❌ faster-whisper not found: {e}")
    sys.exit(1)

# Test helpers import
try:
    from utils.helpers.assistant_io import VoiceAssistantGUI, VoiceRecognition

    print("✅ HelperPHNX imported successfully")
except Exception as e:
    print(f"❌ HelperPHNX import failed: {e}")
    sys.exit(1)

# Test initialization
print("\n" + "=" * 50)
print("Initializing VoiceRecognition...")
print("=" * 50)

root = tk.Tk()
gui = VoiceAssistantGUI(root)
recog = VoiceRecognition(gui)

print("\n" + "=" * 50)
if recog.whisper_model is not None:
    print("✅ SUCCESS! Faster-Whisper is loaded and ready!")
    print("   - Offline mode enabled")
    print("   - No internet needed for speech recognition")
else:
    print("⚠️  Whisper model not loaded")
    print("   - Will use Google Speech Recognition (needs internet)")

print("=" * 50)
print("\nTo test voice recognition, run:")
print("  python test_voice_command.py")
