import sys
import os
import datetime
import time
import tkinter as tk

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
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


class HandleBgProcess:
    def __init__(self, time_based_all, personal_manager, utility):
        self.tm = time_based_all
        self.pm = personal_manager
        self.utils = utility
        self.last_check_hour = None

    def startup_reminders(self):
        """Announce pending items on startup"""
        try:
            # First: Announce current time
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            self.utils.speak(f"{self.utils.tM()} {current_time}.")

            # Second: Announce personal manager items (todos, goals, projects)
            summary = self.pm.get_startup_summary()
            message = self.pm.format_startup_message(summary)
            if message:
                self.utils.speak(message)

            # Third: Wait 10 seconds then announce water reminder
            time.sleep(10)
            self.utils.speak(self.utils.wtR())
        except Exception as e:
            print(f"Error in startup_reminders: {e}")

    def periodic_checks(self, current_hour):
        """Check for reminders periodically (every 6 hours)"""
        try:
            # Check every 6 hours (0, 6, 12, 18)
            if current_hour % 6 == 0 and self.last_check_hour != current_hour:
                self.last_check_hour = current_hour

                # Check stale projects
                stale = self.pm.projects.check_stale_projects(
                    self.pm.settings.get("reminder_threshold_days", 3)
                )
                if stale:
                    project = stale[0]
                    self.utils.speak(
                        f"Sir, no update on {project['name']} project in {project['days_since_update']} days."
                    )
        except Exception as e:
            print(f"Error in periodic_checks: {e}")

    def main(self):
        previous_hour = datetime.datetime.now().hour
        self.tm.clear_time_data()

        # Startup announcement
        self.startup_reminders()

        while True:
            self.tm.main_time()
            previous_hour = self.tm.spk_time(previous_hour)

            # Periodic checks
            current_hour = datetime.datetime.now().hour
            self.periodic_checks(current_hour)

            time.sleep(1)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the GUI window since it's not needed for background process
    gui = VoiceAssistantGUI(root)
    recog = VoiceRecognition(gui)
    spk = SpeechEngine()
    asutils = Utility(spk=spk, reco=recog)

    time_based_all = HandleTimeBasedFunctions(
        utility=asutils,
        timer_manager=TimerManager(spk),
        alarm_manager=AlarmManager(spk, alarm_handle=AlarmHandle(asutils)),
        schedule_manager=ScheduleManager(spk),
        reminder_manager=ReminderManager(asutils),
    )

    # Initialize Personal Manager
    personal_manager = PersonalManager()

    bg_process = HandleBgProcess(time_based_all, personal_manager, asutils)
    bg_process.main()
