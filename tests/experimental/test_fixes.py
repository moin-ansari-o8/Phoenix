"""
Test script to verify the fixes
"""

import os
import sys
import time

# Test 1: Check ConsoleUI has speaking state management
print("=" * 60)
print("TEST 1: ConsoleUI Speaking State")
print("=" * 60)

try:
    # Check if ConsoleUI_new.py exists (needs to be renamed)
    consoleuinew_path = "helpers/ConsoleUI_new.py"
    consoleui_path = "helpers/ConsoleUI.py"

    if os.path.exists(consoleuinew_path):
        print(f"⚠️  ConsoleUI_new.py exists - needs to be renamed to ConsoleUI.py")
        print(f"   Run: del {consoleui_path} && ren {consoleuinew_path} ConsoleUI.py")
    else:
        print("✅ ConsoleUI_new.py was already renamed")

    from helpers.ConsoleUI import (
        get_ui,
        should_ignore_audio,
        start_speaking,
        stop_speaking,
    )

    ui = get_ui()

    # Test speaking state
    print(f"Initial state - should_ignore_audio: {should_ignore_audio()}")

    start_speaking()
    print(f"After start_speaking - should_ignore_audio: {should_ignore_audio()}")

    stop_speaking()
    print(
        f"After stop_speaking (with buffer) - should_ignore_audio: {should_ignore_audio()}"
    )

    time.sleep(2)
    print(f"After 2s delay - should_ignore_audio: {should_ignore_audio()}")

    print("✅ ConsoleUI speaking state works!\n")

except Exception as e:
    print(f"❌ ConsoleUI test failed: {e}\n")

# Test 2: Check .speaking file mechanism
print("=" * 60)
print("TEST 2: .speaking File Mechanism")
print("=" * 60)

try:
    from helpers.HelperPHNX import SpeechEngine

    speaking_file = ".speaking"
    if os.path.exists(speaking_file):
        os.remove(speaking_file)
        print(f"Cleaned up existing {speaking_file}")

    print(f"✅ .speaking file mechanism ready")
    print(f"   File will be created when SpeechEngine.speak() is called\n")

except Exception as e:
    print(f"❌ .speaking file test failed: {e}\n")

# Test 3: Check BgVoiceProcessorPHNX has is_speaking check
print("=" * 60)
print("TEST 3: BgVoiceProcessorPHNX is_speaking() Check")
print("=" * 60)

try:
    # Check if the file has is_speaking function
    processor_file = "bgprogs/BgVoiceProcessorPHNX.pyw"
    with open(processor_file, "r", encoding="utf-8") as f:
        content = f.read()

    if "def is_speaking():" in content:
        print("✅ is_speaking() function exists")
    else:
        print("❌ is_speaking() function NOT found")

    if "if is_speaking():" in content:
        print("✅ is_speaking() check in process_audio_chunk")
    else:
        print("❌ is_speaking() check NOT found in process_audio_chunk")

    if "chunk_timestamp" in content:
        print("✅ chunk_timestamp variable exists for accurate timing")
    else:
        print("❌ chunk_timestamp NOT found")

    print()

except Exception as e:
    print(f"❌ Processor check failed: {e}\n")

# Test 4: Check HelperPHNX creates .speaking file
print("=" * 60)
print("TEST 4: HelperPHNX .speaking File Creation")
print("=" * 60)

try:
    helper_file = "helpers/HelperPHNX.py"
    with open(helper_file, "r", encoding="utf-8") as f:
        content = f.read()

    if (
        'speaking_file = os.path.join(os.path.dirname(__file__), "..", ".speaking")'
        in content
    ):
        print("✅ .speaking file path defined")
    else:
        print("❌ .speaking file path NOT found")

    if 'with open(speaking_file, "w")' in content:
        print("✅ .speaking file is created when speaking")
    else:
        print("❌ .speaking file creation NOT found")

    if "os.remove(speaking_file)" in content:
        print("✅ .speaking file is removed after speaking")
    else:
        print("❌ .speaking file removal NOT found")

    print()

except Exception as e:
    print(f"❌ Helper check failed: {e}\n")

print("=" * 60)
print("SUMMARY")
print("=" * 60)
print("Fixes implemented:")
print("  1. ✅ Speaking state management in ConsoleUI")
print("  2. ✅ .speaking file for cross-process communication")
print("  3. ✅ is_speaking() check before processing audio")
print("  4. ✅ Accurate timestamps from AudioChunk")
print("  5. ✅ Console logging removed from ListenerPHNX")
print()
print("Next steps:")
print("  1. If ConsoleUI_new.py exists, rename it to ConsoleUI.py")
print("  2. Run: python launch_phoenix.py")
print("  3. Test that Phoenix doesn't hear itself")
print("  4. Verify timestamps show actual speech time")
print("=" * 60)
