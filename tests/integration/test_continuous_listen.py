"""
Test Continuous Listening with Faster-Whisper
- No timeouts
- No delays
- Speak as long as you want
- Processes on 0.8s silence
"""

import tkinter as tk
from Utils.limbs.assistant_io import VoiceAssistantGUI, VoiceRecognition

print("\n" + "=" * 70)
print("🎤 CONTINUOUS LISTENING TEST - Faster-Whisper + VAD")
print("=" * 70)

root = tk.Tk()
gui = VoiceAssistantGUI(root)
recog = VoiceRecognition(gui)

if recog.whisper_model is not None:
    print("✅ Whisper loaded - OFFLINE mode")
    print("✅ VAD enabled - Detects voice automatically")
    print("\n📌 How it works:")
    print("   - Always listening (no timeouts)")
    print("   - Speak as long as you want")
    print("   - Pauses 0.8s → processes speech")
    print("   - Ignores non-voice noise")
else:
    print("⚠️  Fallback to Google (8-second timeout)")

print("\n" + "-" * 70)
print("🎤 Start speaking... (0.8s pause to process)")
print("-" * 70)

result = recog.take_command()

print("-" * 70)
if result:
    print(f'✅ You said: "{result}"')
    print(f"📊 Words: {len(result.split())}")
else:
    print("❌ No speech detected")
print("=" * 70)
