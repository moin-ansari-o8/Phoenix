import os
import time
import threading
from time import sleep
import json
from datetime import datetime
import time
from time import sleep


class HandleTimeBasedFunctions:

    def __init__(
        self, timer_manager, alarm_manager, schedule_manager, reminder_manager, utility
    ):
        self.time_data_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "TimeData.json"
        )
        self.data = self.load_data()
        self.today_timers = {}
        self.today_reminders = {}
        self.today_alarms = {}
        self.today_schedule_events = {}
        self.timerClass = timer_manager
        self.reminderClass = reminder_manager
        self.alarmClass = alarm_manager
        self.scheduleClass = schedule_manager
        self.utils = utility

    def spk_time(self, previous_hour):
        """
        Announce the time and weather report when the hour changes.
        """
        current_time = datetime.now()
        current_hour = current_time.hour

        if current_hour != previous_hour:
            tt = datetime.now().strftime(
                "%I:%M %p"
            )  # Format current time as hh:mm AM/PM
            self.utils.speak(f"{self.utils.tM()} {tt}.")
            sleep(15)  # Pause before announcing the weather report
            self.utils.speak(self.utils.wtR())
            return current_hour  # Update the previous_hour
        return previous_hour  # No change in hour, return the same previous_hour

    def load_data(self):
        with open(self.time_data_file, "r") as f:
            return json.load(f)

    def clear_time_data(self):
        self.timerClass.remove_expired_timers()
        self.alarmClass.removeDeletedAlarms()
        self.reminderClass.filter_reminders()

    def main_time(self):
        # self.today_timers = {}
        # self.today_reminders = {}
        # self.today_alarms = {}
        # self.today_schedule_events = {}
        self.timerClass.check_timer()
        self.alarmClass.check_alarms()
        self.reminderClass.ring_reminders()
        self.scheduleClass.check_schedule()

    def save_data(self):
        with open(self.time_data_file, "w") as f:
            json.dump(self.data, f, indent=4)

    def speak(self, message, speed=174):
        self.speech_engine.speak(message, speed)


class ReminderManager:

    def __init__(self, util):
        self.reminder_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "TimeData.json"
        )
        self.ringing = False
        self.utils = util

    def filter_reminders(self):
        try:
            with open(self.reminder_file, "r") as file:
                data = json.load(file)
            reminders = data.get("reminders", [])
            current_date = datetime.now().date()
            filtered_reminders = [
                reminder
                for reminder in reminders
                if not reminder["reminded"]
                and datetime.strptime(reminder["date"], "%d-%m-%y").date()
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
            current_datetime = datetime.now()
            changes = False
            for reminder in reminders:
                reminder_date = datetime.strptime(reminder["date"], "%d-%m-%y")
                reminder_time = datetime.strptime(reminder["time"], "%H:%M").time()
                reminder_datetime = datetime.combine(
                    reminder_date.date(), reminder_time
                )
                if current_datetime.date() == reminder_date.date():
                    if (
                        reminder_time.hour > current_datetime.hour
                        and reminder_time.minute > current_datetime.minute
                        and not reminder["reminded"]
                        and self.ringing == False
                    ):
                        reminder["reminded"] = True
                        self.utils.speak(
                            f"You have missed reminder: {(reminder['message'])}"
                        )
                        changes = True
                        threading.Thread(target=self.ringing_reminder).start()

                    elif (
                        reminder_time.hour == current_datetime.hour
                        and reminder_time.minute == current_datetime.minute
                        and not reminder["reminded"]
                        and self.ringing == False
                    ):
                        self.utils.speak(
                            f"Sir, here's your reminder for today {reminder_time.hour}:{reminder_time.minute} to {reminder['message']}"
                        )
                        reminder["reminded"] = True
                        changes = True
                        threading.Thread(target=self.ringing_reminder).start()
            if changes:
                with open(self.reminder_file, "w") as file:
                    json.dump(data, file, indent=4)
                self.filter_reminders()
        except Exception as e:
            print(f"An error occurred: {e}")

    def ringing_reminder(self):
        self.ringing == True
        sleep(65)
        self.ringing == False


from datetime import time


class TimerManager:
    def __init__(self, spk):
        self.timer_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "TimeData.json"
        )
        self.se = spk

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
            with open(self.timer_file, "r") as f:
                data = json.load(f)
            if not data.get("timers"):
                return
            for timer in data["timers"]:
                timer_id = timer["id"]
                set_time = timer.get("setTime", [])
                ring_time = timer.get("ringTime", [])

                # Ensure setTime and ringTime are valid
                if (
                    len(set_time) != 3
                    or len(ring_time) != 3
                    or not all(isinstance(x, int) for x in set_time + ring_time)
                ):
                    print(
                        f"Timer {timer_id} has invalid setTime or ringTime, skipping."
                    )
                    continue

                # Calculate the difference in minutes
                try:
                    set_time_obj = time(*set_time)
                    ring_time_obj = time(*ring_time)
                    set_datetime = datetime.combine(datetime.today(), set_time_obj)
                    ring_datetime = datetime.combine(datetime.today(), ring_time_obj)
                    diff = round((ring_datetime - set_datetime).total_seconds() / 60, 2)

                    # Check if the timer should ring
                    current_time = datetime.now().time()
                    if current_time >= ring_time_obj and not timer.get("ringed", False):
                        self._mark_timer_as_ringed(timer_id)
                        self.speak(f"Timer set for {diff} minutes has ended.")
                except ValueError as e:
                    print(f"Invalid time format for timer {timer_id}: {e}")
        except Exception as e:
            print(f"Error while checking timers: {e}")
        self.remove_expired_timers()

    def remove_expired_timers(self):
        """
        Removes timers that have already rung or have invalid ring times.
        """
        try:
            with open(self.timer_file, "r") as f:
                data = json.load(f)
            current_time = datetime.now().time()  # Current time as a time object
            valid_timers = []

            for timer in data.get("timers", []):
                ring_time = timer.get("ringTime", [])
                if len(ring_time) == 3 and all(isinstance(x, int) for x in ring_time):
                    try:
                        timer_time = time(*ring_time)  # Convert to a time object
                        if (
                            not timer.get("ringed", False)
                            and timer_time >= current_time
                        ):
                            valid_timers.append(timer)
                    except ValueError as e:
                        print(
                            f"Invalid ringTime format for timer {timer['id']}: {e}, removing it."
                        )
                else:
                    print(
                        f"Invalid ringTime for timer {timer.get('id', 'unknown')}: {ring_time}, removing it."
                    )

            data["timers"] = valid_timers
            with open(self.timer_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error removing expired timers: {e}")

    def speak(self, query, sp=174):
        self.se.speak(query, sp)


class ScheduleManager:

    def __init__(self, spk):
        self.schedule_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "TimeData.json"
        )
        self.se = spk
        self.halt = False

    def _do_halt(self):
        self.halt = True
        sleep(60)
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
            current_time = datetime.now().strftime("%H:%M")
            # print(current_time)
            for schedule in schedules:
                try:
                    schedule_time = schedule["time"]
                    # print(current_time, schedule_time)
                    if (current_time == schedule_time) and (self.halt == False):
                        self.speak(f"Time to {(schedule['message'])}")
                        threading.Thread(target=self._do_halt).start()
                except Exception as e:
                    print(f"Error processing schedule entry '{schedule}': {e}")
        except KeyboardInterrupt:
            print("Schedule monitoring stopped by user.")
        except Exception as e:
            print(f"An error occurred while checking the schedule: {e}")

    def speak(self, query, sp=174):
        self.se.speak(query, sp)


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

    def __init__(self, spk, alarm_handle):
        self.alarm_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "TimeData.json"
        )
        self.se = spk
        self.al = alarm_handle
        self.ringing = False

    def ring_thread(self):
        self.ringing = True
        sleep(65)
        self.ringing = False

    def check_alarms(self):
        """
        Continuously monitors alarms and rings them at the correct time.
        """
        try:
            # Load alarms from file
            with open(self.alarm_file, "r") as file:
                data = json.load(file)
            alarms = data.get("alarms", [])
            if not alarms:
                return  # No alarms to process

            current_time = datetime.now()
            current_hour = current_time.hour
            current_minute = current_time.minute
            today = current_time.strftime("%A").lower()
            today_abbr = self.days_mapping.get(today)

            if not today_abbr:
                print("Could not determine today's day.")
                return

            # Track changes to the alarm data
            data_changed = False
            # print(today_abbr)
            for alarm in alarms:
                try:
                    # Extract alarm details
                    alarm_time = alarm.get("ringAlarm", [])
                    if len(alarm_time) != 2:
                        continue  # Skip invalid alarm times
                    alarm_hour, alarm_minute = alarm_time  #
                    alarm_day = alarm.get("day", [])
                    # print(alarm_day)
                    repeat = alarm.get("repeat", "once").lower()
                    delete = alarm.get("delete", False)
                    ringed = alarm.get("ringed", 0)
                    # Check if the alarm should ring today
                    if today_abbr in alarm_day or "TODAY" in alarm_day:
                        if delete:
                            continue  # Skip deleted alarms

                        if (
                            current_hour == alarm_hour
                            and current_minute == alarm_minute
                            and self.ringing == False
                        ):
                            # Alarm triggered
                            self.speak(
                                f"Alarm!! Time for {alarm.get('label', 'an event')}"
                            )
                            alarm["ringed"] = ringed + 1
                            data_changed = True
                            # Mark non-repeating alarms for deletion
                            if repeat == "once":
                                alarm["delete"] = True
                            threading.Thread(target=self.ring_thread).start()

                except Exception as e:
                    print(f"Error processing alarm '{alarm.get('id', 'unknown')}': {e}")

            # Write back to the file if any data has changed
            if data_changed:
                with open(self.alarm_file, "w") as file:
                    json.dump(data, file, indent=4)

        except KeyboardInterrupt:
            print("Alarm monitoring stopped by user.")
        except Exception as e:
            print(f"An error occurred while checking alarms: {e}")

    def speak(self, query, sp=174):
        self.se.speak(query, sp)

    def removeDeletedAlarms(self):
        """
        Removes alarms marked for deletion (delete=true) from the JSON file
        and prints the label of each deleted alarm.
        """
        try:
            with open(self.alarm_file, "r") as file:
                alarms = json.load(file)
        except FileNotFoundError:
            print("Alarm file not found. Nothing to remove.")
            return
        except json.JSONDecodeError:
            print("Error reading the alarm file. Please check the file structure.")
            return
        updated_alarms = []
        for alarm in alarms.get("alarms", []):
            if alarm.get("delete", False):
                continue
            elif alarm.get("repeat", "") == "once" and alarm.get("ringed", 0) > 0:
                continue
            else:
                updated_alarms.append(alarm)
        alarms["alarms"] = updated_alarms
        try:
            with open(self.alarm_file, "w") as file:
                json.dump(alarms, file, indent=4)
        except IOError:
            print("Error writing to the alarm file. Please check file permissions.")
