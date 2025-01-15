import datetime
import time
import json
import os
from HelperPhoenix import SpeechEngine
from TimeBased import TimerHandle, ReminderHandle, AlarmHandle
import subprocess
import os


class HandleTimeBasedFunctions:

    def __init__(self):
        self.time_data_file = os.path.join(
            os.path.dirname(__file__), "data", "TimeData.json"
        )
        self.data = self.load_data()
        self.today_timers = {}
        self.today_reminders = {}
        self.today_alarms = {}
        self.today_schedule_events = {}
        self.timerClass = TimerManager()
        self.reminderClass = ReminderManager()
        self.alarmClass = AlarmManager()
        self.scheduleClass = ScheduleManager()
        self.speech_engine = SpeechEngine()

    def check_alarms(self):
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        updated_alarms = []
        for alarm in self.data["alarms"]:
            alarm_time = f"{alarm['ringAlarm'][0]:02}:{alarm['ringAlarm'][1]:02}"
            if alarm_time == current_time:
                self.speak(f"Ringing Alarm: {alarm['label']}")
                if alarm["repeat"] == "once":
                    continue
            self.today_alarms[alarm["label"]] = alarm_time
            updated_alarms.append(alarm)
        self.data["alarms"] = updated_alarms

    def check_reminders(self):
        now = datetime.datetime.now()
        today_date = now.strftime("%d-%m-%y")
        updated_reminders = []
        for reminder in self.data["reminders"]:
            if reminder["date"] == today_date:
                reminder_time = datetime.datetime.strptime(
                    reminder["time"], "%H:%M"
                ).time()
                if now.time() >= reminder_time:
                    self.speak(f"Reminder: {reminder['message'][0]}")
                else:
                    self.speech_engine.speak(
                        f"You have missed reminder: {', '.join(reminder['message'])}"
                    )
            elif reminder["date"] > today_date:
                updated_reminders.append(reminder)
        self.data["reminders"] = updated_reminders

    def check_schedule(self):
        now = datetime.datetime.now().time()
        for event in self.data["schedule"]:
            event_time = datetime.datetime.strptime(event["time"], "%H:%M").time()
            if now < event_time:
                self.today_schedule_events[event["message"]] = event["time"]

    def load_data(self):
        with open(self.time_data_file, "r") as f:
            return json.load(f)

    def main(self):
        while True:
            self.today_timers = {}
            self.today_reminders = {}
            self.today_alarms = {}
            self.today_schedule_events = {}
            self.timerClass.check_timer()
            self.reminderClass.ring_reminders()
            self.scheduleClass.check_schedule()
            self.alarmClass.check_alarms()
            time.sleep(1)

    def save_data(self):
        with open(self.time_data_file, "w") as f:
            json.dump(self.data, f, indent=4)

    def speak(self, message):
        self.speech_engine.speak(message)


import json
import datetime
import time


class ReminderManager:

    def __init__(self):
        self.reminder_file = os.path.join(
            os.path.dirname(__file__), "data", "TimeData.json"
        )
        self.se = SpeechEngine()

    def filter_reminders(self):
        try:
            with open(self.reminder_file, "r") as file:
                data = json.load(file)
            reminders = data.get("reminders", [])
            current_date = datetime.datetime.now().date()
            filtered_reminders = [
                reminder
                for reminder in reminders
                if not reminder["reminded"]
                and datetime.datetime.strptime(reminder["date"], "%d-%m-%y").date()
                >= current_date
            ]
            data["reminders"] = filtered_reminders
            with open(self.reminder_file, "w") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            print(f"An error occurred during filtering: {e}")

    def ring_reminders(self):
        try:
            with open(self.reminder_file, "r") as file:
                data = json.load(file)
            if not data.get("reminders"):
                return
            reminders = data.get("reminders", [])
            current_datetime = datetime.datetime.now()
            changes = False
            for reminder in reminders:
                reminder_date = datetime.datetime.strptime(reminder["date"], "%d-%m-%y")
                reminder_time = datetime.datetime.strptime(
                    reminder["time"], "%H:%M"
                ).time()
                reminder_datetime = datetime.datetime.combine(
                    reminder_date.date(), reminder_time
                )
                if current_datetime >= reminder_datetime and (not reminder["reminded"]):
                    reminder["reminded"] = True
                    self.speak(
                        f"Sir, got a reminder message, {', '.join(reminder['message'])}"
                    )
                    changes = True
                elif current_datetime > reminder_datetime and (
                    not reminder["reminded"]
                ):
                    print(f"You have missed reminder: {', '.join(reminder['message'])}")
                    reminder["reminded"] = True
                    changes = True
            if changes:
                with open(self.reminder_file, "w") as file:
                    json.dump(data, file, indent=4)
            self.filter_reminders()
            time.sleep(1)
        except Exception as e:
            print(f"An error occurred: {e}")

    def speak(self, query):
        self.se.speak(query)


class TimerManager:

    def __init__(self):
        self.timer_file = os.path.join(
            os.path.dirname(__file__), "data", "TimeData.json"
        )
        self.se = SpeechEngine()

    def _mark_timer_as_ringed(self, timer_id):
        """
        Marks the timer as ringed by updating the JSON file.
        """
        try:
            with open(self.timer_file, "r") as f:
                data = json.load(f)
            for timer in data.get("timers", []):
                if timer["id"] == timer_id:
                    timer["ringed"] = True
                    break
            with open(self.timer_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error marking timer {timer_id} as ringed: {e}")

    def check_timer(self):
        """
        Checks timers for their ring time and alerts when the timer rings.
        """
        try:
            self.remove_expired_timers()
            with open(self.timer_file, "r") as f:
                data = json.load(f)
            if not data.get("timers"):
                return
            current_time = datetime.datetime.now().time()
            for timer in data["timers"]:
                timer_id = timer["id"]
                ring_time = timer.get("ringTime", [])
                if len(ring_time) != 3:
                    print(f"Timer {timer_id} has invalid ringTime, skipping.")
                    continue
                timer_time = datetime.time(*ring_time)
                if current_time == timer_time and (not timer.get("ringed", False)):
                    self._mark_timer_as_ringed(timer_id)
                    self.speak(f"Timer {timer_id} is ringing! Ring time: {ring_time}")
        except Exception as e:
            print(f"Error while checking timers: {e}")

    def remove_expired_timers(self):
        """
        Removes timers that have already rung or have invalid ring times.
        """
        try:
            with open(self.timer_file, "r") as f:
                data = json.load(f)
            current_time = datetime.datetime.now().time()
            valid_timers = []
            for timer in data.get("timers", []):
                ring_time = timer.get("ringTime", [])
                if len(ring_time) == 3:
                    timer_time = datetime.time(*ring_time)
                    if not timer.get("ringed", False) and timer_time >= current_time:
                        valid_timers.append(timer)
                else:
                    print(f"Invalid ringTime for timer {timer['id']}, removing it.")
            data["timers"] = valid_timers
            with open(self.timer_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error removing expired timers: {e}")

    def speak(self, query):
        self.se.speak(query)


import os
import json
import datetime
import time


class ScheduleManager:

    def __init__(self):
        self.schedule_file = os.path.join(
            os.path.dirname(__file__), "data", "TimeData.json"
        )
        self.se = SpeechEngine()
        self.halt = False

    def check_schedule(self):
        """
        Continuously monitors the schedule and triggers messages at the correct time.
        """
        try:
            with open(self.schedule_file, "r") as file:
                data = json.load(file)
            schedules = data.get("schedule", [])
            if not schedules:
                print("No active schedules to check.")
                return
            current_time = datetime.datetime.now().strftime("%H:%M")
            for schedule in schedules:
                try:
                    schedule_time = schedule["time"]
                    if current_time == schedule_time:
                        self.speak(schedule["message"])
                        time.sleep(60)
                except Exception as e:
                    print(f"Error processing schedule entry '{schedule}': {e}")
        except KeyboardInterrupt:
            print("Schedule monitoring stopped by user.")
        except Exception as e:
            print(f"An error occurred while checking the schedule: {e}")

    def speak(self, query):
        self.se.speak(query)


import os
import json
import datetime
import time


class AlarmManager:
    REPEAT_KEYS = [
        "daily",
        "once",
        "next",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    days_mapping = {
        "monday": "MO",
        "tuesday": "TU",
        "wednesday": "WE",
        "thursday": "TH",
        "friday": "FR",
        "saturday": "ST",
        "sunday": "SU",
    }

    def __init__(self):
        self.alarm_file = os.path.join(
            os.path.dirname(__file__), "data", "TimeData.json"
        )
        self.se = SpeechEngine()
        self.al = AlarmHandle()

    def check_alarms(self):
        """
        Continuously monitors alarms and rings them at the correct time.
        """
        self.al.removeDeletedAlarms()
        try:
            with open(self.alarm_file, "r") as file:
                data = json.load(file)
            alarms = data.get("alarms", [])
            if not alarms:
                return
            current_time = datetime.datetime.now()
            current_hour, current_minute, current_second = (
                current_time.hour,
                current_time.minute,
                current_time.second,
            )
            today_date = current_time.date()
            today = datetime.datetime.now().strftime("%A").lower()
            today_abbr = self.days_mapping.get(today)
            if not today_abbr:
                print("Could not determine today's day.")
                return
            for alarm in alarms:
                try:
                    alarm_time = alarm.get("ringAlarm", [])
                    alarm_hour, alarm_minute = alarm_time
                    alarm_day = alarm.get("day", [])
                    repeat = alarm.get("repeat", "once")
                    delete = alarm.get("delete", False)
                    ringed = alarm.get("ringed", 0)
                    if today_abbr in alarm_day or "TODAY" in alarm_day:
                        if delete:
                            return
                        if (
                            current_hour == alarm_hour
                            and current_minute == alarm_minute
                            and (current_second == 0)
                        ):
                            self.speak(f"Alarm!! time for {alarm['label']}")
                            alarm["ringed"] = ringed + 1
                            if repeat == "once":
                                alarm["delete"] = True
                except Exception as e:
                    print(f"Error processing alarm '{alarm.get('id', 'unknown')}': {e}")
            with open(self.alarm_file, "w") as file:
                json.dump(data, file, indent=4)
        except KeyboardInterrupt:
            print("Alarm monitoring stopped by user.")
        except Exception as e:
            print(f"An error occurred while checking alarms: {e}")

    def speak(self, query):
        self.se.speak(query)


if __name__ == "__main__":
    handler = HandleTimeBasedFunctions()
    handler.main()
