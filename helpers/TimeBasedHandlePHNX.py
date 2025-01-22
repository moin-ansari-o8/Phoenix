import os
import threading
from time import sleep
import re
import json
from datetime import datetime, timedelta
import random
import uuid
from tabulate import tabulate
from collections import defaultdict
from time import sleep


class TimerHandle:

    def __init__(self, utility):
        self.timer_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "TimeData.json"
        )
        self._initialize_timer_file()
        self.utils = utility

    def _assign_thread_to_timer(self, timer):
        """
        Assigns a thread to a timer that continuously checks the current time against the ringTime.
        """

        def timer_thread_logic(timer):
            timer_id = timer["id"]
            ring_time = timer.get("ringTime", [])
            if len(ring_time) != 3:
                print(f"Invalid ring time for timer {timer_id}: {ring_time}")
                return
            hour, minute, second = ring_time
            now = datetime.now()
            try:
                alarm_time = now.replace(
                    hour=hour, minute=minute, second=second, microsecond=0
                )
                if alarm_time < now:
                    alarm_time += timedelta(days=1)
                time_difference = (alarm_time - now).total_seconds()
                print(f"Timer {timer_id} will ring in {time_difference:.2f} seconds.")
                sleep(time_difference)
                self._mark_timer_as_ringed(timer_id)
                print(f"Timer {timer_id} is ringing! Ring time: {ring_time}")
            except Exception as e:
                print(f"Error in timer {timer_id}: {e}")

        timer_thread = threading.Thread(target=timer_thread_logic, args=(timer,))
        timer_thread.start()

    def _extract_time_timer(self, query):
        """Extract hours, minutes, and seconds from the query string."""
        hours, minutes, seconds = (0, 0, 0)
        patterns = {
            "hours": r"(\d+)\s*hours?",
            "minutes": r"(\d+)\s*minutes?",
            "seconds": r"(\d+)\s*seconds?",
        }
        if match := re.search(patterns["hours"], query):
            hours = int(match.group(1))
        if match := re.search(patterns["minutes"], query):
            minutes = int(match.group(1))
        if match := re.search(patterns["seconds"], query):
            seconds = int(match.group(1))
        return (hours, minutes, seconds)

    def _initialize_timer_file(self):
        """Initialize the timer file if it doesn't exist."""
        try:
            with open(self.timer_file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"timers": []}
            with open(self.timer_file, "w") as f:
                json.dump(data, f, indent=4)

    def _mark_timer_as_ringed(self, timer_id):
        """Mark a specific timer as ringed in the JSON file."""
        with open(self.timer_file, "r+") as f:
            data = json.load(f)
            for timer in data["timers"]:
                if timer["id"] == timer_id:
                    timer["ringed"] = True
                    break
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=4)

    def checkTimer(self):
        """
        Remove old timers, then assign threads for active timers to monitor ringTime.
        """
        self.remove_timer()
        with open(self.timer_file, "r") as f:
            data = json.load(f)
            if not data["timers"]:
                print("No active timers to check.")
                return
            for timer in data["timers"]:
                timer_id = timer["id"]
                ring_time = timer.get("ringTime", [])
                if len(ring_time) != 3:
                    print(f"Time's up, sir. ")
                    return
                hour, minute, second = ring_time
                now = datetime.now()
                try:
                    if (
                        now.hour == hour
                        and now.minute == minute
                        and (now.second == second)
                    ):
                        self._mark_timer_as_ringed(timer_id)
                        self.se.speak(
                            f"Timer {timer_id} is ringing! Ring time: {ring_time}"
                        )
                except Exception as e:
                    print(f"Error in timer {timer_id}: {e}")

    def remove_timer(self):
        """
        Remove timers from timer.json where ringed=true.
        """
        with open(self.timer_file, "r+") as f:
            data = json.load(f)
            today = datetime.now().strftime("%d-%m-%y")
            timers_before = len(data["timers"])
            data["timers"] = [
                timer
                for timer in data["timers"]
                if not (
                    timer.get("ringed", False)
                    or datetime.strptime(timer["createDate"], "%d-%m-%y")
                    < datetime.strptime(today, "%d-%m-%y")
                )
            ]
            timers_after = len(data["timers"])
            removed_timers = timers_before - timers_after
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=4)

    def setTimer(self, query):
        """
        Set a timer based on the input query string and save it to timer.json.
        """
        hours, minutes, seconds = self._extract_time_timer(query)
        if hours == 0 and minutes == 0 and (seconds == 0):
            print("No valid time duration found in the query.")
            return
        current_time = datetime.now()
        ring_time = current_time + timedelta(
            hours=hours, minutes=minutes, seconds=seconds
        )
        timer_id = (
            f"t{int(datetime.timestamp(current_time))}_{random.randint(1000, 9999)}"
        )
        set_time = (current_time.hour, current_time.minute, current_time.second)
        ring_time_tuple = (ring_time.hour, ring_time.minute, ring_time.second)
        create_date = current_time.strftime("%d-%m-%y")
        diff = round((ring_time - current_time).total_seconds() / 60, 2)
        timer_details = {
            "id": timer_id,
            "createDate": create_date,
            "setTime": set_time,
            "ringTime": ring_time_tuple,
            "ringed": False,
        }
        with open(self.timer_file, "r+") as f:
            data = json.load(f)
            data["timers"].append(timer_details)
            f.seek(0)
            json.dump(data, f, indent=4)
        self.utils.speak(f"Timer set successfully for {diff} minutes.")

    def viewTimer(self):
        """
        Displays the schedule from schedule.json in a readable format.
        """
        try:
            with open(self.timer_file, "r") as file:
                data = json.load(file)
            if "timers" not in data or not data["timers"]:
                print("No schedules found in the file.")
                return
            print("\nExisting Timers :")
            print("-" * 40)
            for i, timer in enumerate(data["timers"], start=1):
                print(f"{i}. Id: {timer['id']} | RingTime: {timer['ringTime']}")
                print("-" * 40)
        except FileNotFoundError:
            print("schedule.json file not found. Please create a schedule first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


class AlarmHandle:
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

    def __init__(self, utility):
        self.alarm_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "TimeData.json"
        )
        self._initialize_alarm_file()
        self.utils = utility

    def _initialize_alarm_file(self):
        """Initialize the timer file if it doesn't exist."""
        try:
            with open(self.alarm_file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"alarms": []}
            with open(self.alarm_file, "w") as f:
                json.dump(data, f, indent=4)

    def chkAlarm(self):
        """Checks and schedules alarms for today if their ring time is in the future."""
        self.removeDeletedAlarms()
        try:
            with open(self.alarm_file, "r") as file:
                data = json.load(file)
                alarms = data.get("alarms", [])
        except (FileNotFoundError, json.JSONDecodeError):
            print("Error loading alarms. Please check the file.")
            return
        today = datetime.now().strftime("%A").lower()
        today_abbr = self.days_mapping.get(today)
        if not today_abbr:
            print("Could not determine today's day.")
            return
        for alarm in alarms:
            alarm_days = alarm.get("day", [])
            ring_time = alarm.get("ringAlarm", [])
            if today_abbr in alarm_days or (
                "TODAY" in alarm_days and len(ring_time) < 3
            ):
                hour, minute = ring_time
                now = datetime.now()
                current_time = now.hour * 60 + now.minute
                alarm_time_in_minutes = hour * 60 + minute
                if alarm_time_in_minutes > current_time:
                    print(f"Scheduling alarm for label: {alarm.get('label')}")
                    self.startAlarm(alarm)

    def deleteAlarm(self):
        """
        Displays existing alarms with an index number, asks the user which alarm to delete,
        marks the "delete" key of the selected alarm as True, and then calls removeDeletedAlarm.
        """
        try:
            with open(self.alarm_file, "r") as file:
                data = json.load(file)
            # Check if there is only one alarm
            if len(data["alarms"]) == 1:
                alarm_time = f"{data['alarms'][0]['ringAlarm'][0]:02}:{data['alarms'][0]['ringAlarm'][1]:02}"
                self.utils.speak(
                    f"There is only one alarm at {alarm_time}. It will be marked for deletion."
                )
                data["alarms"][0]["delete"] = True
                with open(self.alarm_file, "w") as file:
                    json.dump(data, file, indent=4)
                print(f"The only alarm at {alarm_time} has been marked for deletion.")
                self.removeDeletedAlarms()
                return

            self.utils.speak("just a second, sir.")
            idx, dsk_nm = self.utils.get_cur_desk()
            print(idx, dsk_nm)
            self.utils.get_window("MainPHNX.py")
            self.viewAlarm()
            sleep(2)
            self.utils.maximize_window()
            self.utils.speak("Enter the Index number for the alarm you want to delete.")
            try:
                alarm_index = int(input("\nEnter index to delete: ")) - 1
                if 0 <= alarm_index < len(data["alarms"]):
                    data["alarms"][alarm_index]["delete"] = True
                    with open(self.alarm_file, "w") as file:
                        json.dump(data, file, indent=4)
                    print(f"Alarm at index {alarm_index + 1} marked for deletion.")
                    self.removeDeletedAlarms()
                else:
                    print("Invalid index. Please enter a valid index number.")
            except ValueError:
                print("Invalid input. Please enter a number.")
        except FileNotFoundError:
            print("alarms.json file not found. Please create a schedule first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            sleep(2)
            self.utils.minimize_window()
            self.utils.speak(f"Going back to {dsk_nm}")
            self.utils.desKtoP(idx)

    def getRepeat(self, query):
        """
        Extracts the repeat pattern and associated days from the query.

        Args:
            query (str): The input query string.

        Returns:
            dict: A dictionary with 'repeat' as the key and a list of days as the value.
        """
        query = query.lower().strip()
        repeat = "once"
        days = ["TODAY"]
        if "daily" in query:
            repeat = "daily"
            days = ["TODAY"]
        elif "today" in query:
            repeat = "once"
            days = ["TODAY"]
        elif "tomorrow" in query:
            repeat = "once"
            today_index = datetime.now().weekday()
            tomorrow_index = (today_index + 1) % 7
            days = [list(self.days_mapping.values())[tomorrow_index]]
        elif "every" in query:
            for day in self.days_mapping:
                if day in query:
                    repeat = "weekly"
                    days = [self.days_mapping[day]]
                    break
        else:
            self.utils.speak(
                "Do you want the alarm for a specific day, weekly, or something else? please enter"
            )
            user_input = self.utils.take_command().lower()
            if user_input == "daily":
                repeat = "daily"
                days = ["TODAY"]
            elif user_input == "weekly":
                repeat = "weekly"

                self.utils.speak("Enter the days properly.")
                days_input = (
                    input("Enter the days (e.g., monday tuesday friday): ")
                    .strip()
                    .lower()
                    .split()
                )
                sleep(3)
                days = [
                    self.days_mapping[day]
                    for day in days_input
                    if day in self.days_mapping
                ]
                if not days:
                    self.utils.speak(
                        "No valid days entered. Setting to default 'once' for 'TODAY'."
                    )
                    repeat = "once"
                    days = ["TODAY"]
            else:
                self.utils.speak("Defaulting to 'once' for 'TODAY'.")
                repeat = "once"
                days = ["TODAY"]
        return {repeat: days}

    def getTime(self, query):
        """
        Extracts time information (hour and minute) from the query string in 24-hour format.
        """
        query = query.lower().strip()
        if (
            "add alarm" in query
            or "delete alarm" in query
            or "make alarm" in query
            or ("set alarm" in query)
        ):
            time_match = re.search("(\\d{1,2}):(\\d{2})", query)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
            else:
                self.utils.speak("Time not recognized. Please enter time as shown. ")
                while True:
                    print("Type 'exit' to go out of the loop.")
                    user_input = input("HH:MM (24H) format (e.g., 23:45) : ").strip()
                    if "exit" in user_input:
                        return (None, None)
                    try:
                        hour, minute = map(int, user_input.split(":"))
                        if 0 <= hour < 24 and 0 <= minute < 60:
                            break
                        else:
                            print(
                                "Invalid time range. Ensure hours are between 0-23 and minutes between 0-59."
                            )
                    except ValueError:
                        print(
                            "Invalid format. Please enter time in HH:MM format (e.g., 23:45)."
                        )
            return (hour, minute)
        return (None, None)

    def setAlarm(self, query):
        """
        Handles the alarm setup process, prompts for confirmation, and updates the alarm JSON file.

        Args:
            query (str): The input query for setting the alarm.
        """
        hour, minute = self.getTime(query)
        if hour is None or minute is None:
            print("Invalid time format. Exiting schedule addition process.")
            return
        repeat_dict = self.getRepeat(query)
        repeat = list(repeat_dict.keys())[0]
        days = repeat_dict[repeat]
        self.utils.speak(f"What label should i give, sir?")
        while True:
            print(f">>> Listening for Label:")
            lbl = self.utils.take_command().lower()
            if lbl:
                lbl = lbl.lower().strip()
                if "no" in lbl or "don't" in lbl:
                    lbl = "alarm"
                    break
                elif lbl == "":
                    continue
                else:
                    break
        unique_id = f"A_{uuid.uuid4().hex[:6]}"
        alarm_data = {
            "id": unique_id,
            "ringAlarm": [hour, minute],
            "label": lbl,
            "day": days,
            "repeat": repeat,
            "ringed": 0,
            "delete": False,
        }
        try:
            with open(self.alarm_file, "r") as file:
                alarms = json.load(file)
        except FileNotFoundError:
            alarms = {"alarms": []}
        alarms["alarms"].append(alarm_data)
        with open(self.alarm_file, "w") as file:
            json.dump(alarms, file, indent=4)
        self.utils.speak(f"Alarm successfully set for {hour} hour {minute} minutes.")

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

    def ringAlarm(self, alarm, sleep_seconds):
        """Rings the alarm."""
        sleep(sleep_seconds)
        try:
            with open(self.alarm_file, "r") as file:
                data = json.load(file)
            for item in data["alarms"]:
                if item["id"] == alarm["id"]:
                    item["ringed"] = item.get("ringed", 0) + 1
                    break
            with open(self.alarm_file, "w") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            print(f"Error updating alarm: {e}")
        label = alarm.get("label", "No Label")
        print(f"*** Alarm '{label}' is ringing! ***")

    def startAlarm(self, alarm):
        """Starts the alarm thread and rings it when the time comes."""
        ring_time = alarm.get("ringAlarm", [])
        label = alarm.get("label", "")
        if len(ring_time) < 3:
            hour, minute = ring_time
            now = datetime.now()
            alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            time_difference = (alarm_time - now).total_seconds()
            if time_difference > 0:
                threading.Thread(
                    target=self.ringAlarm, args=(alarm, time_difference)
                ).start()
                print(
                    f"Alarm '{label}' scheduled to ring in {time_difference // 60:.0f} minutes."
                )

    def viewAlarm(self):
        """
        Displays the alarms from alarms.json in a table format.
        """
        try:
            with open(self.alarm_file, "r") as file:
                data = json.load(file)
            if "alarms" not in data or not data["alarms"]:
                print("No alarms found in the file.")
                return
            table_data = []
            for idx, alarm in enumerate(data["alarms"], start=1):
                row = [
                    idx,
                    alarm.get("label", "N/A"),
                    alarm.get("repeat", "N/A"),
                    ", ".join(alarm.get("day", [])),
                    alarm.get("ringed", "N/A"),
                    alarm.get("delete", False),
                    " ".join(map(str, alarm.get("ringAlarm", ["N/A"]))),
                ]
                table_data.append(row)
            headers = [
                "Index",
                "Label",
                "Repeat",
                "Day",
                "Ringed",
                "Delete",
                "RingAlarm",
            ]
            idx, dsk_nm = self.utils.get_cur_desk()
            print(idx, dsk_nm)
            self.utils.get_window("MainPHNX.py")
            sleep(2)
            self.utils.maximize_window()
            self.utils.speak("here are the Existing Alarms:")
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        except FileNotFoundError:
            print("alarms.json file not found. Please create a schedule first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        finally:
            print("keeping window for 10 seconds")
            sleep(10)
            self.utils.minimize_window()
            self.utils.speak(f"Going back to {dsk_nm}")
            self.utils.desKtoP(idx)


class ReminderHandle:
    def __init__(self, utility):
        self.reminder_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "TimeData.json"
        )
        self.utils = utility

    def deleteReminder(self):
        """
        Deletes a reminder based on the index provided by the user.
        """
        try:
            with open(self.reminder_file, "r") as file:
                data = json.load(file)
            if "reminders" not in data or not data["reminders"]:
                print("No reminders found in the file.")
                return
            idx, dsk_nm = self.utils.get_cur_desk()
            print(idx, dsk_nm)
            self.utils.get_window("MainPHNX.py")
            sleep(2)
            self.utils.maximize_window()
            self.viewReminders()
            try:
                reminder_index = (
                    int(input("\nEnter the index of the reminder to delete: ")) - 1
                )
                if 0 <= reminder_index < len(data["reminders"]):
                    removed_reminder = data["reminders"].pop(reminder_index)
                    with open(self.reminder_file, "w") as file:
                        json.dump(data, file, indent=4)
                    print(f"Reminder '{removed_reminder['message']}' has been deleted.")
                else:
                    print("Invalid index. Please enter a valid index number.")
            except ValueError:
                print("Invalid input. Please enter a number.")
        except FileNotFoundError:
            print("reminder.json file not found. Please create a reminder first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            sleep(10)
            self.utils.minimize_window()
            self.utils.speak(f"Going back to {dsk_nm}")
            self.utils.desKtoP(idx)

    def editReminder(self):
        """
        Allows the user to edit a reminder entry by specifying the index.
        The user can edit the date, time, message, or all attributes.
        """
        try:
            with open(self.reminder_file, "r") as file:
                data = json.load(file)
            if "reminders" not in data or not data["reminders"]:
                self.utils.speak("No reminders found in the file.")
                return
            idx, dsk_nm = self.utils.get_cur_desk()
            print(idx, dsk_nm)
            self.utils.get_window("MainPHNX.py")
            sleep(2)
            self.utils.maximize_window()
            self.viewReminders()
            try:
                self.utils.speak("Enter the index of the reminder to edit: ")
                reminder_index = int(input()) - 1
                if 0 <= reminder_index < len(data["reminders"]):
                    reminder = data["reminders"][reminder_index]
                else:
                    print("Invalid index. Please enter a valid index number.")
                    return
            except ValueError:
                print("Invalid input. Please enter a number.")
                return
            print(
                "What would you like to edit? \n1. Date\n2. Time\n3. Message\nYou can enter multiple choices separated by space (e.g., '1 2' to edit Date and Time): "
            )
            edit_choices = input("\nEnter your choices: ").strip().split()
            if not all((choice in ["1", "2", "3"] for choice in edit_choices)):
                print("Invalid choices. Please choose from '1', '2', or '3'.")
                return
            if "1" in edit_choices:
                while not new_date:
                    new_date = input("Enter the new date (DD-MM-YY): ").strip()
                    if "break" in new_date:
                        break
                    elif not re.match("^\\d{2}-\\d{2}-\\d{2}$", new_date):
                        print("Invalid date format. Please use DD-MM-YY format.")
                        new_date = ""
                    reminder["date"] = new_date
            if "2" in edit_choices:
                new_time = ""
                while not new_time:
                    new_time = input(
                        "Enter the new time (HH:MM, 24-hour format): "
                    ).strip()
                    if "break" in new_time:
                        break
                    elif not re.match("^\\d{2}:\\d{2}$", new_time):
                        print("Invalid time format. Please use HH:MM format.")
                        new_time = ""
                    reminder["time"] = new_time
            if "3" in edit_choices:
                new_message = ""
                while not new_message:
                    new_message = input("Enter the new message: ").strip()
                    if "break" in new_message:
                        break
                    if not new_message:
                        print("Message cannot be empty.")
                        return
                    reminder["message"] = new_message
            with open(self.reminder_file, "w") as file:
                json.dump(data, file, indent=4)
            print("Reminder updated successfully.")
        except FileNotFoundError:
            print("reminder.json file not found. Please create a reminder first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:
            sleep(10)
            self.utils.minimize_window()
            self.utils.speak(f"Going back to {dsk_nm}")
            self.utils.desKtoP(idx)

    def filter_reminders(self):
        try:
            with open(self.reminder_file, "r") as file:
                data = json.load(file)
            reminders = data.get("reminders", [])
            filtered_reminders = [r for r in reminders if not r.get("reminded", False)]
            current_date = datetime.now().date()
            filtered_reminders = [
                r
                for r in filtered_reminders
                if datetime.strptime(r["date"], "%d-%m-%y").date() >= current_date
            ]
            unique_reminders = defaultdict(
                lambda: {
                    "id": None,
                    "date": None,
                    "day": None,
                    "time": None,
                    "message": [],
                    "reminded": False,
                }
            )
            for reminder in filtered_reminders:
                key = (reminder["date"], reminder["time"])
                if not unique_reminders[key]["id"]:
                    unique_reminders[key]["id"] = reminder["id"]
                    unique_reminders[key]["date"] = reminder["date"]
                    unique_reminders[key]["day"] = reminder["day"]
                    unique_reminders[key]["time"] = reminder["time"]
                    unique_reminders[key]["reminded"] = reminder["reminded"]
                if isinstance(reminder["message"], list):
                    unique_reminders[key]["message"].extend(reminder["message"])
                else:
                    unique_reminders[key]["message"].append(reminder["message"])
            final_reminders = []
            for key, value in unique_reminders.items():
                value["message"] = list(set(value["message"]))
                final_reminders.append(value)
            data["reminders"] = final_reminders
            with open(self.reminder_file, "w") as file:
                json.dump(data, file, indent=4)
            print("Reminders have been successfully filtered and updated.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def get_next_day(self, day_name):
        """
        Calculate the next date for the given day name.
        """
        today = datetime.now()
        target_day = list(self.days_mapping.keys()).index(day_name.lower())
        current_day = today.weekday()
        days_ahead = (target_day - current_day) % 7 or 7
        next_day = today + datetime.timedelta(days=days_ahead)
        return next_day.strftime("%d-%m-%y")

    def get_time(self):
        """
        Prompt the user to input time in HH:MM format and return it in 24-hour format.
        """
        self.utils.speak("Enter time properly")
        while True:
            user_input = input(
                "Please input time in HH:MM (24H) format (e.g., 23:45) (type exit to get out of the loop): "
            ).strip()
            try:
                if "exit" in user_input:
                    return (None, None)
                hour, minute = map(int, user_input.split(":"))
                if 0 <= hour < 24 and 0 <= minute < 60:
                    return (hour, minute)
                else:
                    print(
                        "Invalid time range. Ensure hours are between 0-23 and minutes between 0-59."
                    )
            except ValueError:
                print(
                    "Invalid format. Please enter time in HH:MM format (e.g., 23:45)."
                )

    def ring_reminder(self):
        try:
            with open(self.reminder_file, "r") as file:
                data = json.load(file)
            reminders = data.get("reminders", [])
            current_datetime = datetime.now()
            changes = False
            for reminder in reminders:
                reminder_date = datetime.strptime(reminder["date"], "%d-%m-%y")
                reminder_time = datetime.strptime(reminder["time"], "%H:%M").time()
                reminder_datetime = datetime.combine(
                    reminder_date.date(), reminder_time
                )
                if current_datetime >= reminder_datetime and (not reminder["reminded"]):
                    reminder["reminded"] = True
                    self.speak(
                        f"Sir, got a reminder message, time to: {', '.join(reminder['message'])}"
                    )
                    changes = True
                elif current_datetime > reminder_datetime and (
                    not reminder["reminded"]
                ):
                    self.speak(
                        f"You have missed reminder: {', '.join(reminder['message'])}"
                    )
                    reminder["reminded"] = True
                    changes = True
            if changes:
                with open(self.reminder_file, "w") as file:
                    json.dump(data, file, indent=4)
            self.filter_reminders()
            sleep(1)
        except Exception as e:
            print(f"An error occurred: {e}")

    def save_to_json(self, reminder):
        """
        Save the reminder to the reminders.json file.
        """
        try:
            try:
                with open(self.reminder_file, "r") as file:
                    data = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {"reminders": []}
            data["reminders"].append(reminder)
            with open(self.reminder_file, "w") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            print(f"Error saving reminder: {e}")

    def setReminder(self, query):
        """
        Args:
            query (str): The query string containing the reminder details.
                        The query should include the time in HH:MM format and
                        optionally the day (e.g., "tomorrow" or "next Monday")
                        and the message for the reminder.

        This method parses the query to extract the reminder time, date, and message.
        If the date or time is not specified, it defaults to the next day at 09:00 AM.
        The reminder is then saved to a JSON file with a unique ID.
        """
        days_mapping = {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "next",
            "tomorrow",
        }

        query = query.lower()
        today = datetime.now()
        reminder_date = None
        reminder_day = None
        reminder_time = None
        message = None

        # Extract time from the query
        time_match = re.search(r"(\d{1,2}):(\d{2})", query)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            reminder_time = f"{hour:02}:{minute:02}"
        if not reminder_time:
            hour, minute = self.get_time()
            reminder_time = f"{hour:02}:{minute:02}"
        if not reminder_time:
            reminder_time = "09:00"

        # Check for the word 'for' in the query
        if "for" in query:
            queries = query.split("for", 1)
            after_for = queries[1].strip()

            # Check for days in days_mapping after 'for'
            # found_day = None
            for day in days_mapping:
                if day in after_for:
                    found_day = day
                    break
            found_day = None
            if found_day:
                if "tomorrow" in after_for:
                    next_day = today + timedelta(days=1)
                    reminder_date = next_day.strftime("%d-%m-%y")
                    reminder_day = next_day.strftime("%A").lower()
                elif "next" in after_for:
                    reminder_date = self.get_next_day(found_day)
                    reminder_day = found_day
                elif "yesterday" in after_for:
                    ls = [
                        "Are you a dumb?",
                        "You have a time machine or what!!!",
                        "You trying to check my abilities or what!!",
                    ]
                    rp = random.choice(ls)
                    self.utils.speak(f"{rp}")
                    return
                else:
                    reminder_date = self.get_next_day(found_day)
                    reminder_day = found_day
            else:
                # If no day is found, treat it as a message
                message = after_for.strip()

        # Check for the word 'to' in the query
        to_match = re.search(r"to (.*?)$", query)
        if to_match:
            potential_message = to_match.group(1).strip()
            if potential_message:
                message = potential_message

        # If no valid date is found, ask the user for the date
        if not reminder_date:
            self.utils.speak("Enter date properly")
        while not reminder_date:
            new_date = input("Enter the new date (DD-MM-YY): ").strip()
            if "break" in new_date:
                print("Exiting reminder setup.")
                return
            elif not re.match(r"^\d{2}-\d{2}-\d{2}$", new_date):
                print("Invalid date format. Please use DD-MM-YY format.")
            else:
                try:
                    # Validate the date
                    datetime.strptime(new_date, "%d-%m-%y")
                    reminder_date = new_date
                    reminder_day = (
                        datetime.strptime(new_date, "%d-%m-%y").strftime("%A").lower()
                    )
                except ValueError:
                    print("Invalid date. Please enter a valid date in DD-MM-YY format.")

        # If no message is provided, ask for it
        while not message:
            self.utils.speak("What is the message, sir?")
            while True:
                print(">>> Listening for Message:")
                message = self.utils.take_command().lower()
                if message:
                    message = message.lower().strip()
                    if "no" in message or "don't" in message:
                        message = "reminder"
                        break
                    elif message == "":
                        continue
                    else:
                        break

        # Generate a unique ID and save the reminder
        id = f"R_{random.randint(100000, 999999)}"
        reminder = {
            "id": id,
            "day": reminder_day,
            "date": reminder_date,
            "message": message,
            "time": reminder_time,
            "reminded": False,
        }
        self.save_to_json(reminder)
        spoken_date = self.format_spoken_date(reminder_date)
        self.utils.speak(
            f"Reminder set for '{message}'. I will remind you on {spoken_date} at {reminder_time}."
        )

    def viewReminders(self):
        """
        Displays the reminders from reminder.json in a readable format.
        """
        try:
            with open(self.reminder_file, "r") as file:
                data = json.load(file)
            if "reminders" not in data or not data["reminders"]:
                print("No reminders found in the file.")
                return
            table_data = []
            for idx, reminder in enumerate(data["reminders"], start=1):
                row = [
                    idx,
                    reminder.get("date", "N/A"),
                    reminder.get("message", "N/A"),
                    reminder.get("reminded", False),
                    reminder.get("time", "N/A"),
                ]
                table_data.append(row)
            headers = ["Index", "Date", "Message", "Reminded", "Time"]
            idx, dsk_nm = self.utils.get_cur_desk()
            print(idx, dsk_nm)
            self.utils.get_window("MainPHNX.py")
            sleep(2)
            self.utils.maximize_window()
            self.utils.speak("Here are the Existing Reminders:")
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        except FileNotFoundError:
            print("reminder.json file not found. Please create a reminder first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        finally:
            sleep(10)
            self.utils.minimize_window()
            self.utils.speak(f"Going back to {dsk_nm}")
            self.utils.desKtoP(idx)

    def format_spoken_date(self, date_str):
        """
        Converts a date in DD-MM-YY format to a natural spoken format.
        Args:
            date_str (str): The date string in DD-MM-YY format.
        Returns:
            str: A natural spoken date, e.g., "2nd January".
        """
        date_obj = datetime.strptime(date_str, "%d-%m-%y")
        day = date_obj.day
        month = date_obj.strftime("%B")
        suffix = (
            "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        )
        return f"{day}{suffix} {month}"


class ScheduleHandle:

    def __init__(self, utility):
        self.schedule_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "schedule.json"
        )
        self.utils = utility

    def addSchedule(self, query):
        """
        Adds or updates a schedule in the JSON file.
        If the time already exists, it prompts the user to update its message.
        """
        try:
            with open(self.schedule_file, "r") as file:
                data = json.load(file)
            hour, minute = self.getTime(query)
            if hour is None or minute is None:
                print("Invalid time format. Exiting schedule addition process.")
                return
            msg = self.getMessage(query)
            if msg is None:
                print("Exiting schedule addition process.")
                return
            time_str = f"{hour:02}:{minute:02}"
            for schedule in data["schedule"]:
                if schedule["time"] == time_str:
                    print(
                        f"A schedule already exists for {time_str}: {schedule['message']}"
                    )
                    user_input = (
                        input("Do you want to update this message? (y/n): ")
                        .strip()
                        .lower()
                    )
                    if user_input == "y":
                        schedule["message"] = msg
                        print(f"Message for {time_str} has been updated.")
                    else:
                        print("No changes made to the schedule.")
                    break
            else:
                data["schedule"].append({"time": time_str, "message": msg})
                print(f"New schedule added for {time_str}: {msg}")
            with open(self.schedule_file, "w") as file:
                json.dump(data, file, indent=4)
                print("Schedule saved successfully.")
        except FileNotFoundError:
            print("self.schedule_file file not found. Creating a new file...")
            data = {"schedule": [{"time": f"{hour:02}:{minute:02}", "message": msg}]}
            with open(self.schedule_file, "w") as file:
                json.dump(data, file, indent=4)
            print(f"New schedule added for {hour:02}:{minute:02}: {msg}")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def deleteSchedule(self, query):
        """
        Deletes a schedule entry based on hour and minute provided in the query.
        """
        try:
            with open(self.schedule_file, "r") as file:
                data = json.load(file)
            if "schedule" not in data or not data["schedule"]:
                print("No schedules found to delete.")
                return
            hour, minute = self.getTime(query)
            if hour is None or minute is None:
                print("Invalid time. Deletion process aborted.")
                return
            time_to_delete = f"{hour:02d}:{minute:02d}"
            for entry in data["schedule"]:
                if entry["time"] == time_to_delete:
                    confirmation = input(
                        f"Are you sure you want to delete the schedule for {time_to_delete}? (y/n): "
                    ).lower()
                    if confirmation == "y":
                        data["schedule"].remove(entry)
                        with open(self.schedule_file, "w") as file:
                            json.dump(data, file, indent=4)
                        print(f"Schedule for {time_to_delete} has been deleted.")
                    else:
                        print("Deletion canceled.")
                    return
            print(f"No schedule found for time {time_to_delete}.")
        except FileNotFoundError:
            print(f"{self.schedule_file} not found. Please create a schedule first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def editSchedule(self):
        """
        Allows the user to edit a schedule entry by specifying the index.
        The user can edit the time, the message, or both.
        """
        try:
            with open(self.schedule_file, "r") as file:
                data = json.load(file)
            if "schedule" not in data or not data["schedule"]:
                print("No schedules found in the file.")
                return
            self.viewSchedule()
            try:
                index = (
                    int(input("Enter the index of the schedule you want to edit: ")) - 1
                )
                if index < 0 or index >= len(data["schedule"]):
                    print("Invalid index. Please try again.")
                    return
            except ValueError:
                print("Invalid input. Please enter a valid number.")
                return
            print("What would you like to edit? \n1.time\n2.message\n3.both): ")
            edit_choice = input("\nEnter index-(1/2/3): ").strip().lower()
            if edit_choice not in ["time", "message", "both", "1", "2", "3"]:
                print("Invalid choice. Please choose 'time', 'message', or 'both'.")
                return
            if edit_choice in ["time", "both", "1", "3"]:
                new_time = input("Enter the new time (HH:MM, 24-hour format): ").strip()
                if not re.match("^\\d{2}:\\d{2}$", new_time):
                    print("Invalid time format. Please use HH:MM format.")
                    return
                data["schedule"][index]["time"] = new_time
            if edit_choice in ["message", "both", "2", "3"]:
                new_message = input("Enter the new message: ").strip()
                if not new_message:
                    print("Message cannot be empty.")
                    return
                data["schedule"][index]["message"] = new_message
            with open(self.schedule_file, "w") as file:
                json.dump(data, file, indent=4)
            print("Schedule updated successfully.")
        except FileNotFoundError:
            print("schedule.json file not found. Please create a schedule first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def getMessage(self, query):
        """
        Continuously takes input from the user until they type 'exit' or enter a valid message.
        """
        queries = query.split("for")
        if queries[1]:
            msg = queries[1]
            return msg
        else:
            while True:
                msg = input("Enter your message (type 'exit' to quit): ").strip()
                if msg.lower() == "exit":
                    print("Exiting message input...")
                    return None
                elif msg:
                    return msg
                else:
                    print("Message cannot be empty. Please try again.")

    def getTime(self, query):
        """
        Extracts time information (hour and minute) from the query string in 24-hour format.
        """
        query = query.lower().strip()
        if (
            "add schedule" in query
            or "delete schedule" in query
            or "make schedule" in query
        ):
            time_match = re.search("(\\d{1,2}):(\\d{2})", query)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
            else:
                while True:
                    user_input = input(
                        "Time not recognized. Please input time in HH:MM (24H) format (e.g., 23:45): "
                    ).strip()
                    print("Type 'exit' to go out of the loop.")
                    if "exit" in user_input:
                        return (None, None)
                    try:
                        hour, minute = map(int, user_input.split(":"))
                        if 0 <= hour < 24 and 0 <= minute < 60:
                            break
                        else:
                            print(
                                "Invalid time range. Ensure hours are between 0-23 and minutes between 0-59."
                            )
                    except ValueError:
                        print(
                            "Invalid format. Please enter time in HH:MM format (e.g., 23:45)."
                        )
            return (hour, minute)
        return (None, None)

    def viewSchedule(self):
        """
        Displays the schedule from schedule.json in a readable format.
        """
        try:
            with open(self.schedule_file, "r") as file:
                data = json.load(file)
            if "schedule" not in data or not data["schedule"]:
                print("No schedules found in the file.")
                return
            table_data = []
            for idx, entry in enumerate(data["schedule"], start=1):
                row = [entry.get("message", "N/A"), entry.get("time", "N/A"), idx]
                table_data.append(row)
            headers = ["Index", "Message", "Time"]
            print("\nCurrent Schedule:")
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        except FileNotFoundError:
            print("schedule.json file not found. Please create a schedule first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
