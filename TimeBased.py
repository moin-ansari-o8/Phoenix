import os
import sys
import time
import threading
import datetime
import subprocess
from time import sleep
import re
import json
from datetime import datetime, timedelta
# Third-party libraries
import random

class TimeBasedFunctionality:
    def __init__(self):
        # Set the timer.json path
        self.timer_file = os.path.join(os.path.dirname(__file__), "data", "timer.json")
        self._initialize_timer_file()
        self.alarm_file = os.path.join(os.path.dirname(__file__), "data", "alarm.json")
        self._initialize_alarm_file()

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
            "seconds": r"(\d+)\s*second"
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
            ring_time = timer["ringTime"]

            while True:
                now = datetime.now()
                current_time_tuple = (now.hour, now.minute, now.second)

                if current_time_tuple >= tuple(ring_time):
                    print(f"Timer {timer_id} is ringing! Ring time: {ring_time}")
                    
                    # Mark the timer as ringed
                    self._mark_timer_as_ringed(timer_id)
                    break

                sleep(1)  # Check every second

        # Create and start a thread
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

            # Filter out timers with ringed=true
            timers_before = len(data["timers"])
            data["timers"] = [timer for timer in data["timers"] if not timer.get("ringed", False)]

            timers_after = len(data["timers"])
            removed_timers = timers_before - timers_after

            # Overwrite the JSON file with updated data
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=4)

        print(f"Removed {removed_timers} timers where ringed=true.")

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
        ring_time = current_time + timedelta(hours=hours, minutes=minutes, seconds=seconds)

        # Prepare the timer details
        timer_id = f"t{int(datetime.timestamp(current_time))}_{random.randint(1000, 9999)}"
        set_time = (current_time.hour, current_time.minute, current_time.second)
        ring_time_tuple = (ring_time.hour, ring_time.minute, ring_time.second)

        timer_details = {
            "id": timer_id,
            "setTime": set_time,
            "ringTime": ring_time_tuple,
            "ringed": False
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
#------------------TIMER FINISH-----------------------------------------------------
    def _initialize_alarm_file(self):
        """Initialize the alarm file if it doesn't exist."""
        try:
            with open(self.alarm_file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create an empty structure if the file doesn't exist or is corrupted
            data = {"alarms": []}
            with open(self.alarm_file, "w") as f:
                json.dump(data, f, indent=4)

    def _extract_time(self, query):
        """Extract hours and minutes from the query string."""
        hours, minutes = 0, 0

        # Regex to extract time components
        patterns = {
            "hours": r"(\d+)\s*hour",
            "minutes": r"(\d+)\s*minute",
            "time": r"(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)",  # 12:30 pm or 12:30 a.m.
        }

        # Extract time using regex for 12-hour format
        match = re.search(patterns["time"], query, re.IGNORECASE)
        if match:
            hours, minutes = int(match.group(1)), int(match.group(2))
            # Convert to 24-hour format if necessary
            am_pm = match.group(3).lower()
            if am_pm in ['pm', 'p.m.'] and hours != 12:
                hours += 12
            elif am_pm in ['am', 'a.m.'] and hours == 12:
                hours = 0
        else:
            # Handle 24-hour format or other case
            if match := re.search(patterns["hours"], query):
                hours = int(match.group(1))
            if match := re.search(patterns["minutes"], query):
                minutes = int(match.group(1))

        return hours, minutes

    def _ask_for_details(self, query):
        """Ask the user for additional details like label and repeat schedule."""
        # Ask for the alarm label
        label = input("Please provide a label for the alarm: ")

        # Ask for the repeat schedule
        repeat = input("Should the alarm repeat? (daily, once, or a day of the week): ").lower()

        # Validate repeat input
        valid_repeats = {"", "daily", "once", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        if repeat not in valid_repeats:
            print("Invalid repeat schedule. Defaulting to 'once'.")
            repeat = "once"

        return label, repeat

    def setAlarm(self, query):
        """
        Set an alarm based on the input query string and save it to alarm.json.
        """
        # Extract the time (hours and minutes) from the query
        hours, minutes = self._extract_time(query)
        if hours == 0 and minutes == 0:
            print("No valid time duration found in the query.")
            return

        # Ask for other details if needed
        label, repeat = self._ask_for_details(query)

        # Get the current time
        current_time = datetime.now()

        # Calculate the alarm time based on the current time
        alarm_time = current_time.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        
        # If the alarm time is in the past, set it for the next day (tomorrow)
        if alarm_time < current_time:
            alarm_time += timedelta(days=1)

        # Prepare the alarm details
        alarm_id = f"a{random.randint(1, 1000)}"  # Generate a random ID for the alarm
        alarm_details = {
            "id": alarm_id,
            "setAlarm": [alarm_time.hour, alarm_time.minute],
            "ringAlarm": [alarm_time.hour, alarm_time.minute],  # For simplicity, same as setAlarm
            "label": label,
            "repeat": repeat,
            "delete": False
        }

        # Save to alarm.json
        with open(self.alarm_file, "r+") as f:
            data = json.load(f)
            data["alarms"].append(alarm_details)
            f.seek(0)
            json.dump(data, f, indent=4)

        print(f"Alarm set successfully! Alarm-ID:{alarm_id}.")

    def checkAlarm(self):
        """
        Check for alarms and print details of the upcoming alarms.
        """
        with open(self.alarm_file, "r") as f:
            data = json.load(f)

            if not data["alarms"]:
                print("No alarms set.")
                return

            for alarm in data["alarms"]:
                print(f"Alarm ID: {alarm['id']}, Time: {alarm['setAlarm'][0]}:{alarm['setAlarm'][1]}, Label: {alarm['label']}, Repeat: {alarm['repeat']}")
if __name__ == "__main__":
    tbf = TimeBasedFunctionality()
    # tbf.setTimer("Set timer for 10 seconds.")
    # tbf.remove_timer() 
    # tbf.checkTimer()
    tbf.setAlarm("set alarm for 1")

    # import inspect
    # methods = [func for func, _ in inspect.getmembers(TimeBasedFunctionality, predicate=inspect.isfunction)]
    # print(methods)