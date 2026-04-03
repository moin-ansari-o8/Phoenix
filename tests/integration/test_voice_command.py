"""Test voice command with Faster-Whisper"""

import tkinter as tk
from helpers.HelperPHNX import VoiceAssistantGUI, VoiceRecognition

print("\n" + "=" * 60)
print("🎤 Voice Command Test - Faster-Whisper")
print("=" * 60)

root = tk.Tk()
gui = VoiceAssistantGUI(root)
recog = VoiceRecognition(gui)

if recog.whisper_model is not None:
    print("✅ Using Faster-Whisper (OFFLINE)")
else:
    print("⚠️  Using Google Speech Recognition (ONLINE)")

print("\n🎤 Listening... Say something!")
print("-" * 60)

result = recog.take_command()

print("-" * 60)
if result:
    print(f'✅ Recognized: "{result}"')
else:
    print("❌ No speech detected or recognition failed")
print("=" * 60)
