"""
Quick test of BgTmPHNX.pyw startup (without infinite loop)
Tests that the new Personal Manager integration doesn't break anything
"""

import sys
import os
import datetime
import tkinter as tk

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from helpers.TimeBasedHandlePHNX import AlarmHandle
from helpers.UtilitiesPHNX import Utility
from helpers.HelperPHNX import (
    VoiceAssistantGUI,
    VoiceRecognition,
    SpeechEngine,
)
from helpers.TimeBasedRunPHNX import (
    HandleTimeBasedFunctions,
    TimerManager,
    AlarmManager,
    ReminderManager,
    ScheduleManager,
)
from helpers.PersonalManagerPHNX import PersonalManager

print("=" * 70)
print("BACKGROUND PROCESS STARTUP TEST")
print("=" * 70)

try:
    print("\n[1/6] Initializing GUI...")
    root = tk.Tk()
    root.withdraw()
    gui = VoiceAssistantGUI(root)
    print("✓ GUI initialized")

    print("\n[2/6] Initializing speech components...")
    recog = VoiceRecognition(gui)
    spk = SpeechEngine()
    asutils = Utility(reco=recog, spk=spk)
    print("✓ Speech components ready")

    print("\n[3/6] Initializing time-based functions...")
    time_based_all = HandleTimeBasedFunctions(
        utility=asutils,
        timer_manager=TimerManager(spk),
        alarm_manager=AlarmManager(spk, alarm_handle=AlarmHandle(asutils)),
        schedule_manager=ScheduleManager(spk),
        reminder_manager=ReminderManager(asutils),
    )
    print("✓ Time-based functions ready")

    print("\n[4/6] Initializing Personal Manager...")
    personal_manager = PersonalManager()
    print("✓ Personal Manager ready")
    print(f"  - Settings: {personal_manager.settings}")

    print("\n[5/6] Creating background process handler...")
    from bgprogs.BgTmPHNX import HandleBgProcess

    bg_process = HandleBgProcess(time_based_all, personal_manager, asutils)
    print("✓ Background process handler created")

    print("\n[6/6] Testing startup reminders...")
    print("  Note: This will speak through your speakers!")
    bg_process.startup_reminders()
    print("✓ Startup reminders executed")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\nYour background process is ready to run!")
    print("\nTo start it normally:")
    print("  python bgprogs\\BgTmPHNX.pyw")
    print("\nIt will:")
    print("  ✓ Announce pending items on startup")
    print("  ✓ Speak time every hour")
    print("  ✓ Remind you to drink water every hour")
    print("  ✓ Check stale projects every 6 hours")
    print("  ✓ Handle alarms, timers, reminders, schedule")
    print("=" * 70)

except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
finally:
    if "root" in locals():
        root.destroy()

print("\nTest completed successfully!")
