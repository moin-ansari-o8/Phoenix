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

class TimerHandle:
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

class AlarmHandle:
    # Keywords for repetition
    REPEAT_KEYS = [
            "daily", "once", "next", "monday", "tuesday", "wednesday",
            "thursday", "friday", "saturday", "sunday"
        ]
    def getTime(self, query):
        """
        Extracts time information (hour, minute, and period) from the query string.
        """
        # Ensure the query contains the keyword
        if "set alarm for" in query.lower():
            # Extract time in HH:MM format
            time_match = re.search(r"(\d{1,2}):(\d{2})", query)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
            else:
                # Prompt user input if no valid time found
                user_input = input("Time not recognized, please input time in HH:MM format: ")
                hour, minute = map(int, user_input.split(":"))

            # Check for period (a.m./p.m.) after the time
            period_match = re.search(r"(a\.m\.|am|p\.m\.|pm)", query.lower())
            if period_match:
                period = period_match.group(0).replace("am", "a.m.").replace("pm", "p.m.")
            else:
                # Determine period based on 24-hour format
                if hour >= 12:
                    period = "p.m."
                    if hour > 12:
                        hour -= 12
                else:
                    period = "a.m."

            return hour, minute, period

        # If no keyword found
        return None, None, "Keyword 'set alarm for' not found"

    def getRepeat(self, query):
        """
        Extracts repetition information from the query string.
        """
        

        # Search for repetition keyword in query
        for keyword in self.REPEAT_KEYS:
            if keyword in query.lower():
                return keyword
        
        # Default to 'once' if no keyword is found
        return "once"


if __name__ == "__main__":
    # tbf = TimerHandle()
    # tbf.setTimer("Set timer for 10 seconds.")
    # tbf.remove_timer() 
    # tbf.checkTimer()

    # import inspect
    # methods = [func for func, _ in inspect.getmembers(TimeBasedFunctionality, predicate=inspect.isfunction)]
    # print(methods)
    ah=AlarmHandle()
    # print(ah.timeDivider("set alarm for 12:10"))
    query1 = "set alarm for 10:30 a.m."
    query2 = "set alarm for 15:45"
    query3 = "set alarm for 8:00 pm"
    print(ah.getTime(query1))  # Output: (10, 30, 'a.m.')
    print(ah.getTime(query2))  # Output: (3, 45, 'p.m.')
    print(ah.getTime(query3))  # Output: (8, 0, 'p.m.')

    # Test getRepeat
    query4 = "set alarm for 10:30 daily"
    query5 = "set alarm for 7:00 on monday"
    query6 = "set alarm for 9:15 for next day"
    print(ah.getRepeat(query4))  # Output: 'daily'
    print(ah.getRepeat(query5))  # Output: 'monday'
    print(ah.getRepeat(query6))  # Output: 'once'