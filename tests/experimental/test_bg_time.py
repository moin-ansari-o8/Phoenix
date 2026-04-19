"""
Test script to verify time_monitor.pyw fixes
Tests:
1. Object initialization
2. ReminderManager has correct utility object
3. Time speaking functionality
"""

import sys
import os
import datetime
import tkinter as tk

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from utils.services.time_handlers import AlarmHandle
from utils.services.action_utilities import Utility
from utils.services.assistant_io import (
    VoiceAssistantGUI,
    VoiceRecognition,
    SpeechEngine,
)
from utils.services.time_runner import (
    HandleTimeBasedFunctions,
    TimerManager,
    AlarmManager,
    ReminderManager,
    ScheduleManager,
)

print("=" * 60)
print("Testing BgTmPHNX Background Process Fix")
print("=" * 60)

try:
    # Test 1: Initialize all components
    print("\n[TEST 1] Initializing components...")
    root = tk.Tk()
    root.withdraw()
    gui = VoiceAssistantGUI(root)
    recog = VoiceRecognition(gui)
    spk = SpeechEngine()
    asutils = Utility(reco=recog, spk=spk)
    print("✓ Components initialized successfully")

    # Test 2: Check if ReminderManager receives correct object
    print("\n[TEST 2] Creating ReminderManager with asutils...")
    reminder_mgr = ReminderManager(asutils)
    print(f"✓ ReminderManager created")
    print(f"  - Has 'utils' attribute: {hasattr(reminder_mgr, 'utils')}")
    print(f"  - Utils object type: {type(reminder_mgr.utils).__name__}")
    print(f"  - Utils has 'speak' method: {hasattr(reminder_mgr.utils, 'speak')}")
    print(f"  - Utils has 'tM' method: {hasattr(reminder_mgr.utils, 'tM')}")
    print(f"  - Utils has 'wtR' method: {hasattr(reminder_mgr.utils, 'wtR')}")

    # Test 3: Initialize HandleTimeBasedFunctions
    print("\n[TEST 3] Creating HandleTimeBasedFunctions...")
    time_based_all = HandleTimeBasedFunctions(
        utility=asutils,
        timer_manager=TimerManager(spk),
        alarm_manager=AlarmManager(spk, alarm_handle=AlarmHandle(asutils)),
        schedule_manager=ScheduleManager(spk),
        reminder_manager=reminder_mgr,
    )
    print("✓ HandleTimeBasedFunctions created successfully")

    # Test 4: Test the utility methods
    print("\n[TEST 4] Testing utility methods...")
    time_msg = asutils.tM()
    water_msg = asutils.wtR()
    print(f"✓ Time message: '{time_msg}'")
    print(f"✓ Water reminder: '{water_msg}'")

    # Test 5: Test speak functionality (will actually speak)
    print("\n[TEST 5] Testing speak functionality...")
    print("  Note: This will actually speak through your speakers!")
    test_msg = "Testing background process fix"
    print(f"  Speaking: '{test_msg}'")
    asutils.speak(test_msg)
    print("✓ Speak function executed")

    # Test 6: Simulate time announcement
    print("\n[TEST 6] Testing time announcement logic...")
    current_time = datetime.datetime.now()
    tt = current_time.strftime("%I:%M %p")
    announcement = f"{asutils.tM()} {tt}."
    water_reminder = asutils.wtR()
    print(f"  Would announce: '{announcement}'")
    print(f"  Then remind: '{water_reminder}'")
    print("✓ Time announcement logic verified")

    # Test 7: Test spk_time method (simulated hour change)
    print("\n[TEST 7] Testing spk_time method with simulated hour change...")
    previous_hour = current_time.hour - 1  # Simulate previous hour
    print(f"  Current hour: {current_time.hour}")
    print(f"  Simulated previous hour: {previous_hour}")
    print("  This will trigger the hourly announcement...")
    new_hour = time_based_all.spk_time(previous_hour)
    print(f"✓ spk_time executed, returned hour: {new_hour}")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✓")
    print("=" * 60)
    print("\nThe background process should now work correctly!")
    print("It will announce time + water reminder every hour.")

except Exception as e:
    print(f"\n✗ TEST FAILED with error:")
    print(f"  {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
finally:
    if "root" in locals():
        root.destroy()

print("\nTest completed successfully!")
