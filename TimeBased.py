import os
import sys
import time
import threading
import datetime
import subprocess
from time import sleep
import re
from tabulate import tabulate
import json
from collections import defaultdict
from datetime import datetime, timedelta
import tkinter as tk
from HelperPhoenix import speak

# Third-party librariesk
import random
import uuid


class TimerHandle:
    def __init__(self):
        # Set the timer.json path
        self.timer_file = os.path.join(os.path.dirname(__file__), "data", "timer.json")
        self._initialize_timer_file()

    def _initialize_timer_file(self):
        """Initialize the timer file if it doesn't exist."""
        try:
            with open(self.timer_file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create an empty structure if the file doesn't exist or is corrupted
            data = {"timers": []}
            with open(self.timer_file, "w") as f:
                json.dump(data, f, indent=4)

    def _extract_time_timer(self, query):
        """Extract hours, minutes, and seconds from the query string."""
        hours, minutes, seconds = 0, 0, 0

        # Regex to extract time components
        patterns = {
            "hours": r"(\d+)\s*hour",
            "minutes": r"(\d+)\s*minute",
            "seconds": r"(\d+)\s*second",
        }

        # Extract hours, minutes, and seconds
        if match := re.search(patterns["hours"], query):
            hours = int(match.group(1))
        if match := re.search(patterns["minutes"], query):
            minutes = int(match.group(1))
        if match := re.search(patterns["seconds"], query):
            seconds = int(match.group(1))

        return hours, minutes, seconds

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
                # Set the alarm time to today with the provided ring time
                alarm_time = now.replace(
                    hour=hour, minute=minute, second=second, microsecond=0
                )

                # If the alarm time is in the past, schedule it for the next day
                if alarm_time < now:
                    alarm_time += timedelta(days=1)

                # Calculate the time difference in seconds
                time_difference = (alarm_time - now).total_seconds()

                print(f"Timer {timer_id} will ring in {time_difference:.2f} seconds.")

                # Sleep until the alarm time
                sleep(time_difference)

                # Mark the timer as ringed and notify the user
                self._mark_timer_as_ringed(timer_id)
                print(f"Timer {timer_id} is ringing! Ring time: {ring_time}")

            except Exception as e:
                print(f"Error in timer {timer_id}: {e}")

        # Create and start a thread for the timer
        timer_thread = threading.Thread(target=timer_thread_logic, args=(timer,))
        timer_thread.start()

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

    def remove_timer(self):
        """
        Remove timers from timer.json where ringed=true.
        """
        with open(self.timer_file, "r+") as f:
            data = json.load(f)
            # Get today's date in DD-MM-YY format
            today = datetime.now().strftime("%d-%m-%y")

            # Filter out timers based on conditions
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

            # Overwrite the JSON file with updated data
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=4)

        print(
            f"Removed {removed_timers} timers where ringed=true or createDate is earlier than today's date.."
        )

    def viewTimer(self):
        """
        Displays the schedule from schedule.json in a readable format.
        """
        try:
            # Load data from the JSON file
            with open(self.timer_file, "r") as file:
                data = json.load(file)

            # Check if the file has a "schedule" key
            if "timers" not in data or not data["timers"]:
                print("No schedules found in the file.")
                return

            # Display the current schedule
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

    def setTimer(self, query):
        """
        Set a timer based on the input query string and save it to timer.json.
        """
        # Extract hours, minutes, and seconds
        hours, minutes, seconds = self._extract_time_timer(query)
        if hours == 0 and minutes == 0 and seconds == 0:
            print("No valid time duration found in the query.")
            return

        # Get the current time and calculate the ring time
        current_time = datetime.now()
        ring_time = current_time + timedelta(
            hours=hours, minutes=minutes, seconds=seconds
        )

        # Prepare the timer details
        timer_id = (
            f"t{int(datetime.timestamp(current_time))}_{random.randint(1000, 9999)}"
        )
        set_time = (current_time.hour, current_time.minute, current_time.second)
        ring_time_tuple = (ring_time.hour, ring_time.minute, ring_time.second)
        create_date = current_time.strftime("%d-%m-%y")  # Format date as "DD-MM-YY"

        timer_details = {
            "id": timer_id,
            "setTime": set_time,
            "ringTime": ring_time_tuple,
            "createDate": create_date,  # Add the creation date
            "ringed": False,
        }

        # Save to timer.json
        with open(self.timer_file, "r+") as f:
            data = json.load(f)
            data["timers"].append(timer_details)
            f.seek(0)
            json.dump(data, f, indent=4)

        print(f"Timer set successfully! Timer-ID:{timer_id}.")

    def checkTimer(self):
        """
        Remove old timers, then assign threads for active timers to monitor ringTime.
        """
        # Step 1: Remove timers with ringed=true
        self.remove_timer()

        # Step 2: Assign threads to active timers
        with open(self.timer_file, "r") as f:
            data = json.load(f)

            if not data["timers"]:
                print("No active timers to check.")
                return

            print(f"Starting threads for {len(data['timers'])} timers...")
            for timer in data["timers"]:
                self._assign_thread_to_timer(timer)


class AlarmHandle:
    # Keywords for repetition
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
        self.alarm_file = os.path.join(os.path.dirname(__file__), "data", "alarm.json")
        self._initialize_alarm_file()

    def _initialize_alarm_file(self):
        """Initialize the timer file if it doesn't exist."""
        try:
            with open(self.alarm_file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create an empty structure if the file doesn't exist or is corrupted
            data = {"alarms": []}
            with open(self.alarm_file, "w") as f:
                json.dump(data, f, indent=4)

    def getTime(self, query):
        """
        Extracts time information (hour and minute) from the query string in 24-hour format.
        """
        query = query.lower().strip()
        # Ensure the query contains the keyword
        if (
            "add alarm" in query
            or "delete alarm" in query
            or "make alarm" in query
            or "set alarm" in query
        ):
            # Extract time in HH:MM format
            time_match = re.search(r"(\d{1,2}):(\d{2})", query)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
            else:
                while True:  # Keep prompting until valid input is provided
                    user_input = input(
                        "Time not recognized. Please input time in HH:MM (24H) format (e.g., 23:45): "
                    ).strip()
                    print("Type 'exit' to go out of the loop.")
                    if "exit" in user_input:
                        return None, None
                    try:
                        # Split the input and validate the format
                        hour, minute = map(int, user_input.split(":"))
                        if 0 <= hour < 24 and 0 <= minute < 60:  # Check valid range
                            break  # Return the validated hour and minute
                        else:
                            print(
                                "Invalid time range. Ensure hours are between 0-23 and minutes between 0-59."
                            )
                    except ValueError:
                        print(
                            "Invalid format. Please enter time in HH:MM format (e.g., 23:45)."
                        )

            return hour, minute

        # If no keyword found
        return None, None

    def getRepeat(self, query):
        """
        Extracts the repeat pattern and associated days from the query.

        Args:
            query (str): The input query string.

        Returns:
            dict: A dictionary with 'repeat' as the key and a list of days as the value.
        """
        query = query.lower().strip()

        # Default values
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
            print(
                "Do you want the alarm for a specific day, weekly, or something else?"
            )
            user_input = (
                input(
                    "Type 'weekly', 'daily', or leave blank for default (once today): "
                )
                .strip()
                .lower()
            )
            if user_input == "daily":
                repeat = "daily"
                days = ["TODAY"]
            elif user_input == "weekly":
                repeat = "weekly"
                days_input = (
                    input("Enter the days (e.g., monday tuesday friday): ")
                    .strip()
                    .lower()
                    .split()
                )
                days = [
                    self.days_mapping[day]
                    for day in days_input
                    if day in self.days_mapping
                ]
                if not days:
                    print(
                        "No valid days entered. Setting to default 'once' for 'TODAY'."
                    )
                    repeat = "once"
                    days = ["TODAY"]
            else:
                print("Defaulting to 'once' for 'TODAY'.")
                repeat = "once"
                days = ["TODAY"]

        return {repeat: days}

    def removeDeletedAlarms(self):
        """
        Removes alarms marked for deletion (delete=true) from the JSON file
        and prints the label of each deleted alarm.
        """
        try:
            # Load existing alarms from the file
            with open(self.alarm_file, "r") as file:
                alarms = json.load(file)
        except FileNotFoundError:
            print("Alarm file not found. Nothing to remove.")
            return
        except json.JSONDecodeError:
            print("Error reading the alarm file. Please check the file structure.")
            return

        # Initialize a list to hold the alarms that are not marked for deletion
        updated_alarms = []

        # Iterate over existing alarms and remove those marked for deletion
        for alarm in alarms.get("alarms", []):
            if alarm.get("delete", False):
                # Print the label of the deleted alarm
                print(f"Alarm deleted for label: {alarm.get('label', 'unknown')}")
            elif alarm.get("repeat", "") == "once" and alarm.get("ringed", 0) > 0:
                # Delete one-time alarms that have already rung
                print(
                    f"One-time alarm deleted for label: {alarm.get('label', 'unknown')}"
                )
            else:
                # Keep alarms that are not marked for deletion
                updated_alarms.append(alarm)

        # Update the alarms structure with the remaining alarms
        alarms["alarms"] = updated_alarms

        # Save the updated structure back to the file
        try:
            with open(self.alarm_file, "w") as file:
                json.dump(alarms, file, indent=4)
            print("Alarms updated successfully.")
        except IOError:
            print("Error writing to the alarm file. Please check file permissions.")

    def viewAlarm(self):
        """
        Displays the alarms from alarms.json in a table format.
        """
        try:
            # Load data from the JSON file
            with open(self.alarm_file, "r") as file:
                data = json.load(file)

            # Check if the file has an "alarms" key and is not empty
            if "alarms" not in data or not data["alarms"]:
                print("No alarms found in the file.")
                return

            # Prepare data for tabular display
            table_data = []
            for idx, alarm in enumerate(data["alarms"], start=1):
                row = [
                    idx,  # Index
                    alarm.get("label", "N/A"),  # Column: Label
                    " ".join(
                        map(str, alarm.get("ringAlarm", ["N/A"]))
                    ),  # Column: RingAlarm
                    ", ".join(alarm.get("day", [])),  # Column: Day
                    alarm.get("repeat", "N/A"),  # Column: Repeat
                    alarm.get("ringed", "N/A"),  # Column: Ringed
                    alarm.get("delete", False),  # Column: Delete
                ]
                table_data.append(row)

            # Define table headers
            headers = [
                "Index",
                "Label",
                "RingAlarm",
                "Day",
                "Repeat",
                "Ringed",
                "Delete",
            ]

            # Print the table
            print("\nExisting Alarms:")
            print(tabulate(table_data, headers=headers, tablefmt="grid"))

        except FileNotFoundError:
            print("alarms.json file not found. Please create a schedule first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")

    def deleteAlarm(self):
        """
        Displays existing alarms with an index number, asks the user which alarm to delete,
        marks the "delete" key of the selected alarm as True, and then calls removeDeletedAlarm.
        """
        try:
            # Load data from the JSON file
            with open(self.alarm_file, "r") as file:
                data = json.load(file)
            self.viewAlarm()
            # Ask the user for the index of the alarm to delete
            try:
                alarm_index = (
                    int(input("\nEnter the index of the alarm to delete: ")) - 1
                )

                if 0 <= alarm_index < len(data["alarms"]):
                    # Mark the selected alarm's "delete" key as True
                    data["alarms"][alarm_index]["delete"] = True

                    # Save the updated data back to the JSON file
                    with open(self.alarm_file, "w") as file:
                        json.dump(data, file, indent=4)

                    print(f"Alarm at index {alarm_index + 1} marked for deletion.")

                    # Call the removeDeletedAlarm method
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

    def handleAlarmPrompt(self, query):
        """
        Handles the alarm setup process, prompts for confirmation, and updates the alarm JSON file.

        Args:
            query (str): The input query for setting the alarm.
        """
        # Get time details from query using getTime method
        hour, minute = self.getTime(query)  # Assuming getTime is already implemented
        if hour is None or minute is None:
            print("Invalid time format. Exiting schedule addition process.")
            return

        # Get repeat details from query using getRepeat method
        repeat_dict = self.getRepeat(query)  # Assuming getRepeat is already implemented
        repeat = list(repeat_dict.keys())[0]  # Extract the key ("once", "weekly", etc.)
        days = repeat_dict[repeat]  # Extract the list of days

        # Loop to get the label
        while True:
            print(
                f"Enter label name or 'no' to just come out of the loop for: {hour}:{minute}:"
            )  # Don't change
            lbl = input()  # Don't change this line
            if lbl:  # Check if input is valid
                lbl = lbl.lower().strip()  # Convert to lowercase and strip whitespace
                if "no" in lbl:  # If input contains "no", set label to "alarm"
                    lbl = "alarm"
                break  # Exit loop as lbl is processed

        # Generate a unique ID
        unique_id = f"A_{uuid.uuid4().hex[:6]}"

        # Confirm details with the user
        print(
            f"Please confirm the details:\nTime: {hour}:{minute} \nRepeat: {repeat}\nDays: {days}\nLabel: {lbl}"
        )
        confirmation = (
            input("Type 'Y' to confirm, anything else to cancel: ").strip().lower()
        )
        if confirmation != "y":
            print("Operation cancelled.")
            return  # Exit the method

        # Prepare alarm data
        alarm_data = {
            "id": unique_id,
            "ringAlarm": [hour, minute],
            "label": lbl,
            "day": days,  # Use the days list extracted from the repeat dictionary
            "repeat": repeat,  # Use the repeat key
            "ringed": 0,
            "delete": False,
        }

        # Load existing alarms from file or create a new structure
        try:
            with open(self.alarm_file, "r") as file:
                alarms = json.load(file)
        except FileNotFoundError:
            alarms = {"alarms": []}

        # Add the new alarm
        alarms["alarms"].append(alarm_data)

        # Save updated alarms back to the file
        with open(self.alarm_file, "w") as file:
            json.dump(alarms, file, indent=4)

        # Confirm alarm set
        print(
            f"Alarm successfully set for {hour}:{minute} with repeat: {repeat} and days: {days}."
        )

    def startAlarm(self, alarm):
        """Starts the alarm thread and rings it when the time comes."""
        ring_time = alarm.get("ringAlarm", [])
        label = alarm.get("label", "")

        if len(ring_time) < 3:
            hour, minute = ring_time
            now = datetime.now()

            # Calculate the difference between current time and alarm time
            alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            time_difference = (alarm_time - now).total_seconds()

            if time_difference > 0:
                # threading.Timer(time_difference, self.ringAlarm, args=(alarm,)).start()
                threading.Thread(
                    target=self.ringAlarm, args=(alarm, time_difference)
                ).start()
                print(
                    f"Alarm '{label}' scheduled to ring in {time_difference // 60:.0f} minutes."
                )

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

            # Write the updated JSON back to the file
            with open(self.alarm_file, "w") as file:
                json.dump(data, file, indent=4)

        except Exception as e:
            print(f"Error updating alarm: {e}")

        label = alarm.get("label", "No Label")
        print(f"*** Alarm '{label}' is ringing! ***")

    def chkAlarm(self):
        """Checks and schedules alarms for today if their ring time is in the future."""
        self.removeDeletedAlarms()

        # Load alarms from the file
        try:
            with open(self.alarm_file, "r") as file:
                data = json.load(file)
                alarms = data.get("alarms", [])
        except (FileNotFoundError, json.JSONDecodeError):
            print("Error loading alarms. Please check the file.")
            return

        # Get today's day in abbreviated form (e.g., "MO" for Monday)
        today = datetime.now().strftime("%A").lower()
        today_abbr = self.days_mapping.get(today)
        if not today_abbr:
            print("Could not determine today's day.")
            return

        # Iterate through alarms
        for alarm in alarms:
            alarm_days = alarm.get("day", [])
            ring_time = alarm.get("ringAlarm", [])

            # Check if the alarm is set for today and has a valid ring time
            if today_abbr in alarm_days or "TODAY" in alarm_days and len(ring_time) < 3:
                hour, minute = ring_time
                now = datetime.now()

                current_time = now.hour * 60 + now.minute
                alarm_time_in_minutes = hour * 60 + minute

                if alarm_time_in_minutes > current_time:
                    print(f"Scheduling alarm for label: {alarm.get('label')}")
                    self.startAlarm(alarm)


class ReminderHandle:
    days_mapping = {
        "monday": "MO",
        "tuesday": "TU",
        "wednesday": "WE",
        "thursday": "TH",
        "friday": "FR",
        "saturday": "ST",
        "sunday": "SU",
    }

    def __init__(self, recognizer, speech_engine):
        self.reminder_file = os.path.join(
            os.path.dirname(__file__), "data", "reminder.json"
        )
        self.recognizer = recognizer
        self.speech_engine = speech_engine

    def take_command(self):
        return self.recognizer.take_command()

    def speak(self, query):
        self.speech_engine.speak(query)

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
        while True:
            user_input = input(
                "Please input time in HH:MM (24H) format (e.g., 23:45) (type exit to get out of the loop): "
            ).strip()
            try:
                if "exit" in user_input:
                    return None, None
                hour, minute = map(int, user_input.split(":"))
                if 0 <= hour < 24 and 0 <= minute < 60:
                    return hour, minute
                else:
                    print(
                        "Invalid time range. Ensure hours are between 0-23 and minutes between 0-59."
                    )
            except ValueError:
                print(
                    "Invalid format. Please enter time in HH:MM format (e.g., 23:45)."
                )

    def setReminder(self, query):
        """
        Set a reminder based on the query and save it to a JSON file.
        """
        # Default reminder details
        message = ""
        reminder_date = ""
        reminder_day = ""
        reminder_time = "09:00"  # Default time if not provided in the query

        # Parse query for date, day, and message
        query = query.lower()
        today = datetime.now()

        # Split query by "for"
        queries = query.split("for")

        # Initialize variables
        reminder_date = None
        reminder_day = None
        message = None

        if len(queries) > 1:  # Ensure there's at least a date/day part after "for"
            condition = queries[1].strip()

            if "tomorrow" in condition:
                next_day = today + datetime.timedelta(days=1)
                reminder_date = next_day.strftime("%d-%m-%y")
                reminder_day = self.days_mapping[next_day.strftime("%A").lower()]

            elif "next" in condition:
                for day in self.days_mapping.keys():
                    if day in condition:
                        reminder_date = self.get_next_day(day)
                        reminder_day = self.days_mapping[day]
                        break

        if len(queries) > 2:  # Check if a message exists
            message = queries[2].strip()

        # Fallback to prompt the user if message is still None or empty
        if not message:
            while True:
                message = input("What should I remind you about? ").strip()
                if message:
                    break

        # Print confirmation (optional)
        # print(f"Reminder set for '{message}', on {reminder_day} ({reminder_date}).")

        # If date or day is still missing, set it to tomorrow as default
        if not reminder_date or not reminder_day:
            next_day = today + datetime.timedelta(days=1)
            reminder_date = next_day.strftime("%d-%m-%y")
            reminder_day = self.days_mapping[next_day.strftime("%A").lower()]
        hr, min = self.get_time()
        if hr is not None and min is not None:
            reminder_time = f"{hr:02}:{min:02}"
        # If message is not set, prompt user to provide it
        while not message:
            message = input("What is the reminder for? ").strip()

        id = f"R_{random.randint(100000, 999999)}"
        # Create the reminder entry
        reminder = {
            "id": id,
            "date": reminder_date,
            "day": reminder_day,
            "time": reminder_time,
            "message": message,
            "reminded": False,
        }

        # Save the reminder to the JSON file
        self.save_to_json(reminder)

        # Inform the user
        print(
            f"Reminder set for '{message}'. I will remind you on {reminder_date.replace('-', ' ')}."
        )

    def save_to_json(self, reminder):
        """
        Save the reminder to the reminders.json file.
        """
        try:
            # Load existing reminders
            try:
                with open(self.reminder_file, "r") as file:
                    data = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {"reminders": []}

            # Add the new reminder
            data["reminders"].append(reminder)

            # Write back to the file
            with open(self.reminder_file, "w") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            print(f"Error saving reminder: {e}")

    def filter_reminders(self):
        try:
            # Step 1: Load the JSON file
            with open(self.reminder_file, "r") as file:
                data = json.load(file)

            reminders = data.get("reminders", [])

            # Step 2: Remove reminders where "reminded" is true
            filtered_reminders = [r for r in reminders if not r.get("reminded", False)]

            # Step 3: Remove reminders with past dates
            current_date = datetime.now().date()
            filtered_reminders = [
                r
                for r in filtered_reminders
                if datetime.strptime(r["date"], "%d-%m-%y").date() >= current_date
            ]

            # Step 4: Filter duplicates and handle the message aggregation
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
                key = (reminder["date"], reminder["time"])  # Group by date and time
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

            # Convert defaultdict to a list of reminders with combined messages
            final_reminders = []
            for key, value in unique_reminders.items():
                value["message"] = list(
                    set(value["message"])
                )  # Remove duplicate messages within the list
                final_reminders.append(value)

            # Step 5: Update the JSON file with filtered reminders
            data["reminders"] = final_reminders

            with open(self.reminder_file, "w") as file:
                json.dump(data, file, indent=4)

            print("Reminders have been successfully filtered and updated.")

        except Exception as e:
            print(f"An error occurred: {e}")

    def ring_reminder(self):
        self.filter_reminders()
        try:
            # Load reminders from the file
            with open(self.reminder_file, "r") as file:
                data = json.load(file)

            reminders = data.get("reminders", [])

            current_datetime = datetime.now()

            def reminder_ringer(reminder):
                print(f"Reminder: {', '.join(reminder['message'])}")
                reminder["reminded"] = True

            for reminder in reminders:
                reminder_date = datetime.strptime(reminder["date"], "%d-%m-%y")
                reminder_time = datetime.strptime(reminder["time"], "%H:%M").time()
                reminder_datetime = datetime.combine(
                    reminder_date.date(), reminder_time
                )

                if reminder_datetime > current_datetime:
                    delay = (reminder_datetime - current_datetime).total_seconds()
                    threading.Timer(delay, reminder_ringer, [reminder]).start()
                elif not reminder["reminded"]:
                    print(f"You have missed reminder: {', '.join(reminder['message'])}")

            # Save updated reminders back to the file
            with open(self.reminder_file, "w") as file:
                json.dump(data, file, indent=4)

        except Exception as e:
            print(f"An error occurred: {e}")


class ScheduleHandle:
    def __init__(self, recognizer, speech_engine):
        self.schedule_file = os.path.join(
            os.path.dirname(__file__), "data", "schedule.json"
        )
        self.recognizer = recognizer
        self.speech_engine = speech_engine

    def getTime(self, query):
        """
        Extracts time information (hour and minute) from the query string in 24-hour format.
        """
        query = query.lower().strip()
        # Ensure the query contains the keyword
        if (
            "add schedule" in query
            or "delete schedule" in query
            or "make schedule" in query
        ):
            # Extract time in HH:MM format
            time_match = re.search(r"(\d{1,2}):(\d{2})", query)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
            else:
                while True:  # Keep prompting until valid input is provided
                    user_input = input(
                        "Time not recognized. Please input time in HH:MM (24H) format (e.g., 23:45): "
                    ).strip()
                    print("Type 'exit' to go out of the loop.")
                    if "exit" in user_input:
                        return None, None
                    try:
                        # Split the input and validate the format
                        hour, minute = map(int, user_input.split(":"))
                        if 0 <= hour < 24 and 0 <= minute < 60:  # Check valid range
                            break  # Return the validated hour and minute
                        else:
                            print(
                                "Invalid time range. Ensure hours are between 0-23 and minutes between 0-59."
                            )
                    except ValueError:
                        print(
                            "Invalid format. Please enter time in HH:MM format (e.g., 23:45)."
                        )

            return hour, minute

        # If no keyword found
        return None, None

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
                    return None  # Return None to indicate the user exited
                elif msg:  # If the user enters a non-empty message
                    return msg
                else:
                    print("Message cannot be empty. Please try again.")

    def addSchedule(self, query):
        """
        Adds or updates a schedule in the JSON file.
        If the time already exists, it prompts the user to update its message.
        """
        try:
            # Load data from the JSON file
            with open(self.schedule_file, "r") as file:
                data = json.load(file)

            # Extract time and message
            hour, minute = self.getTime(query)
            if hour is None or minute is None:
                print("Invalid time format. Exiting schedule addition process.")
                return

            msg = self.getMessage(query)
            if msg is None:  # Exit the process if the user types 'exit'
                print("Exiting schedule addition process.")
                return

            # Convert hour and minute to "HH:MM" format
            time_str = f"{hour:02}:{minute:02}"

            # Check if the time already exists in the schedule
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
                        # Update the existing message
                        schedule["message"] = msg
                        print(f"Message for {time_str} has been updated.")
                    else:
                        print("No changes made to the schedule.")
                    break
            else:
                # Add new schedule if time does not exist
                data["schedule"].append({"time": time_str, "message": msg})
                print(f"New schedule added for {time_str}: {msg}")

            # Save the updated data back to the JSON file
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

    def viewSchedule(self):
        """
        Displays the schedule from schedule.json in a readable format.
        """
        try:
            # Load data from the JSON file
            with open(self.schedule_file, "r") as file:
                data = json.load(file)

            # Check if the file has a "schedule" key
            if "schedule" not in data or not data["schedule"]:
                print("No schedules found in the file.")
                return

            # Display the current schedule
            print("\nCurrent Schedule:")
            print("-" * 40)
            for i, entry in enumerate(data["schedule"], start=1):
                print(f"{i}. Time: {entry['time']} | Message: {entry['message']}")
                print("-" * 40)

        except FileNotFoundError:
            print("schedule.json file not found. Please create a schedule first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def deleteSchedule(self, query):
        """
        Deletes a schedule entry based on hour and minute provided in the query.
        """
        try:
            # Load the JSON data from the file
            with open(self.schedule_file, "r") as file:
                data = json.load(file)

            # Ensure the schedule exists in the JSON file
            if "schedule" not in data or not data["schedule"]:
                print("No schedules found to delete.")
                return

            # Get the hour and minute from the query
            hour, minute = self.getTime(query)

            if hour is None or minute is None:  # Handle invalid time
                print("Invalid time. Deletion process aborted.")
                return

            # Format the time in HH:MM format for comparison
            time_to_delete = f"{hour:02d}:{minute:02d}"

            # Validate if the time exists in the schedule
            for entry in data["schedule"]:
                if entry["time"] == time_to_delete:
                    # Confirm deletion
                    confirmation = input(
                        f"Are you sure you want to delete the schedule for {time_to_delete}? (y/n): "
                    ).lower()
                    if confirmation == "y":
                        data["schedule"].remove(entry)
                        # Save the updated data back to the file
                        with open(self.schedule_file, "w") as file:
                            json.dump(data, file, indent=4)
                        print(f"Schedule for {time_to_delete} has been deleted.")
                    else:
                        print("Deletion canceled.")
                    return

            # If no matching time was found
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
            # Load data from the JSON file
            with open(self.schedule_file, "r") as file:
                data = json.load(file)

            # Check if the file has a "schedule" key
            if "schedule" not in data or not data["schedule"]:
                print("No schedules found in the file.")
                return

            # Display the current schedule
            print("\nCurrent Schedule:")
            print("-" * 40)
            for i, entry in enumerate(data["schedule"], start=1):
                print(f"{i}. Time: {entry['time']} | Message: {entry['message']}")
                print("-" * 40)

            # Ask the user to choose the schedule to edit
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

            # Ask what the user wants to edit
            print("What would you like to edit? \n1.time\n2.message\n3.both): ")
            edit_choice = input("\nEnter index-(1/2/3): ").strip().lower()

            if edit_choice not in ["time", "message", "both", "1", "2", "3"]:
                print("Invalid choice. Please choose 'time', 'message', or 'both'.")
                return

            # Edit the selected fields
            if edit_choice in ["time", "both", "1", "3"]:
                new_time = input("Enter the new time (HH:MM, 24-hour format): ").strip()
                if not re.match(r"^\d{2}:\d{2}$", new_time):
                    print("Invalid time format. Please use HH:MM format.")
                    return
                data["schedule"][index]["time"] = new_time

            if edit_choice in ["message", "both", "2", "3"]:
                new_message = input("Enter the new message: ").strip()
                if not new_message:
                    print("Message cannot be empty.")
                    return
                data["schedule"][index]["message"] = new_message

            # Save the updated data back to the file
            with open(self.schedule_file, "w") as file:
                json.dump(data, file, indent=4)

            print("Schedule updated successfully.")

        except FileNotFoundError:
            print("schedule.json file not found. Please create a schedule first.")
        except json.JSONDecodeError:
            print("Error decoding the JSON file. Please check the file format.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":

    tbf = TimerHandle()
    tbf.setTimer("Set timer for 10 seconds.")
    tbf.setTimer("Set timer for 15 seconds.")
    tbf.setTimer("Set timer for 20 seconds.")
    # tbf.viewTimer()
    # tbf.remove_timer()
    # tbf.viewTimer()
    tbf.checkTimer()
    # import inspect
    # methods = [func for func, _ in inspect.getmembers(TimeBasedFunctionality, predicate=inspect.isfunction)]
    # print(methods)
    # ah = AlarmHandle()
    # ah.chkAlarm()
    # print(ah.timeDivider("set alarm for 12:10"))
    # query1 = "set alarm for 10:30 a.m."
    # query2 = "set alarm for 14:30"
    # ah.speak("alarm management is starting")
    # query3 = "set alarm for 8:00 pm"
    # print(ah.getTime(query1))  # Output: (10, 30, 'a.m.')
    # ah.handleAlarmPrompt(query2)# Output: (3, 45, 'p.m.')
    # ah.removeDeletedAlarms()
    # ah.chkAlarm()

    # print(ah.getTime(query3))  # Output: (8, 0, 'p.m.')
    # while True:
    #     query=recognizer.take_command()
    #     print(ah.handleAlarmPrompt(query))  # Output: 'once'

    # # Test getRepeat
    # query4 = "set alarm for 10:30 daily"
    # query5 = "set alarm for 7:00 on monday"
    # query6 = "set alarm for 21:15 for next day"
    # # print(ah.getRepeat(query4))  # Output: 'daily'
    # print(ah.getRepeat(query5))  # Output: 'monday'
    # print(ah.handleAlarmPrompt(query5))  # Output: 'once'
    # print(ah.handleAlarmPrompt(query6))  # Output: 'once'

    # Call chkAlarm to start checking and scheduling alarms
    # print("Checking and scheduling alarms...")
    # ah.chkAlarm()

    # # Prevent the program from exiting
    # print("Program is running. Press Ctrl+C to exit.")
    # print(dir(AlarmHandle))
    # methods = [
    #     method
    #     for method in dir(AlarmHandle)
    #     if callable(getattr(AlarmHandle, method)) and not method.startswith("__")
    # ]

    # print(methods)
    # rm = ReminderHandle(recognizer, speech_engine=SpeechEngine())
    # rm.setReminder("set reminder for tomorrow")
    # rm.setReminder("set reminder for next saturday for chilling")
    # rm.setReminder("set reminder for next saturday for chilling")
    # rm.setReminder("set reminder for next saturday for chilling")
    # rm.filter_reminders()
    # schd = ScheduleHandle(recognizer, speech_engine=SpeechEngine())
    # schd.addSchedule("add schedule at 9:30 for koleg time")
    # schd.viewSchedule()
    # schd.editSchedule()
    # schd.deleteSchedule("delete schedule for")
    # rm.setReminder("set reminder for filling up form")
