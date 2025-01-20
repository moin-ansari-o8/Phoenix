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


class HandleBgProcess:
    def __init__(self, time_based_all):
        self.tm = time_based_all

    def main(self):
        previous_hour = datetime.datetime.now().hour
        while True:
            self.tm.main_time()
            previous_hour = self.tm.spk_time(previous_hour)
            time.sleep(1)


if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    recog = VoiceRecognition(gui)
    spk = SpeechEngine()
    asutils = Utility(reco=recog, spk=spk)

    time_based_all = HandleTimeBasedFunctions(
        utility=asutils,
        timer_manager=TimerManager(spk),
        alarm_manager=AlarmManager(spk, alarm_handle=AlarmHandle(asutils)),
        schedule_manager=ScheduleManager(spk),
        reminder_manager=ReminderManager(spk),
    )
    bg_process = HandleBgProcess(time_based_all)
    bg_process.main()
