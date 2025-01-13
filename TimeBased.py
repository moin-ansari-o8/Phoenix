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
import datetime
from HelperPhoenix import VoiceRecognition,VoiceAssistantGUI,SpeechEngine
import tkinter as tk
# Third-party librariesk
import random
import uuid

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
    days_mapping = {
            "monday": "MO", "tuesday": "TU", "wednesday": "WE",
            "thursday": "TH", "friday": "FR", "saturday": "ST", "sunday": "SU"
        }
    
    def __init__(self,recognizer,speech_engine):
        self.alarm_file = os.path.join(os.path.dirname(__file__), "data", "alarm.json")
        self._initialize_alarm_file()
        self.recognizer = recognizer
        self.speech_engine = speech_engine
    
    def take_command(self):
        return self.recognizer.take_command()

    def speak(self,query):
        self.speech_engine.speak(query)

    def _initialize_alarm_file(self):
        """Initialize the timer file if it doesn't exist."""
        try:
            with open(self.alarm_file, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create an empty structure if the file doesn't exist or is corrupted
            data = {"timers": []}
            with open(self.alarm_file, "w") as f:
                json.dump(data, f, indent=4)

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
                while True:  # Keep prompting until valid input is provided
                    user_input = input("Time not recognized. Please input time in HH:MM (24H) format (e.g., 23:45): ").strip()
                    print("type exit to go out of the loop")
                    if "exit" in user_input:
                        return None, None, "not found"
                    try:
                        # Split the input and validate the format
                        hour, minute = map(int, user_input.split(":"))
                        if 0 <= hour < 24 and 0 <= minute < 60:  # Check if the time is within valid range
                            break  # Return the validated hour and minute
                        else:
                            print("Invalid time range. Ensure hours are between 0-23 and minutes between 0-59.")
                    except ValueError:
                        print("Invalid format. Please enter time in HH:MM format (e.g., 23:45).")

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
        return None, None, "not found"

    def getRepeat(self,query):
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
            print("Do you want the alarm for a specific day, weekly, or something else?")
            user_input = input("Type 'weekly', 'daily', or leave blank for default (once today): ").strip().lower()
            if user_input == "daily":
                repeat = "daily"
                days = ["TODAY"]
            elif user_input == "weekly":
                repeat = "weekly"
                days_input = input("Enter the days (e.g., monday tuesday friday): ").strip().lower().split()
                days = [self.days_mapping[day] for day in days_input if day in self.days_mapping]
                if not days:
                    print("No valid days entered. Setting to default 'once' for 'TODAY'.")
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
                print(f"One-time alarm deleted for label: {alarm.get('label', 'unknown')}")
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

    def handleAlarmPrompt(self, query):
        """
        Handles the alarm setup process, prompts for confirmation, and updates the alarm JSON file.

        Args:
            query (str): The input query for setting the alarm.
        """
        # Get time details from query using getTime method
        hour, minute, period = self.getTime(query)  # Assuming getTime is already implemented
        if period == "not found":
            print("String not suitable for alarm setup.")
            return
        elif period == "loop out":
            return

        # Get repeat details from query using getRepeat method
        repeat_dict = self.getRepeat(query)  # Assuming getRepeat is already implemented
        repeat = list(repeat_dict.keys())[0]  # Extract the key ("once", "weekly", etc.)
        days = repeat_dict[repeat]  # Extract the list of days

        # Loop to get the label
        while True:
            print(f"Speak the label name or 'no' to just come out of the loop for: {hour}:{minute} {period}:")  # Don't change
            lbl = self.take_command()  # Don't change this line
            if lbl:  # Check if input is valid
                lbl = lbl.lower().strip()  # Convert to lowercase and strip whitespace
                if "no" in lbl:  # If input contains "no", set label to "alarm"
                    lbl = "alarm"
                break  # Exit loop as lbl is processed

        # Generate a unique ID
        unique_id = f"A_{uuid.uuid4().hex[:6]}"

        # Confirm details with the user
        print(f"Please confirm the details:\nTime: {hour}:{minute} {period}\nRepeat: {repeat}\nDays: {days}\nLabel: {lbl}")
        confirmation = input("Type 'Y' to confirm, anything else to cancel: ").strip().lower()
        if confirmation != "y":
            print("Operation cancelled.")
            return  # Exit the method

        # Prepare alarm data
        alarm_data = {
            "id": unique_id,
            "ringAlarm": [hour, minute, period],
            "label": lbl,
            "day": days,  # Use the days list extracted from the repeat dictionary
            "repeat": repeat,  # Use the repeat key
            "ringed": 0,  
            "delete": False  
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
        print(f"Alarm successfully set for {hour}:{minute} {period} with repeat: {repeat} and days: {days}.")

    def startAlarm(self, alarm):
        """Starts the alarm thread and rings it when the time comes."""
        ring_time = alarm.get("ringAlarm", [])
        label = alarm.get("label", "")

        if len(ring_time) >= 3:
            hour, minute, period = ring_time
            now = datetime.datetime.now()

            # Convert 12-hour format to 24-hour format
            if period.lower() == "p.m." and hour != 12:
                hour += 12
            elif period.lower() == "a.m." and hour == 12:
                hour = 0

            # Calculate the difference between current time and alarm time
            alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            time_difference = (alarm_time - now).total_seconds()

            if time_difference > 0:
                # threading.Timer(time_difference, self.ringAlarm, args=(alarm,)).start()
                threading.Thread(target=self.ringAlarm,args=(alarm,time_difference)).start()
                print(f"Alarm '{label}' scheduled to ring in {time_difference // 60:.0f} minutes.")

    def ringAlarm(self, alarm,sleep_seconds):
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
        # while True:
        #     end_alarminput
        threading.Thread(target=self.speech_engine.threadedSpeak, args=(f"*** Alarm '{label}' is ringing! ***",)).start()
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
        today = datetime.datetime.now().strftime("%A").lower()
        today_abbr = self.days_mapping.get(today)
        if not today_abbr:
            print("Could not determine today's day.")
            return

        # Iterate through alarms
        for alarm in alarms:
            alarm_days = alarm.get("day", [])
            ring_time = alarm.get("ringAlarm", [])

            # Check if the alarm is set for today and has a valid ring time
            if today_abbr in alarm_days or "TODAY" in alarm_days and len(ring_time) >= 3:
                hour, minute, period = ring_time
                now = datetime.datetime.now()

                # Convert 12-hour format to 24-hour format
                if period.lower() == "p.m." and hour != 12:
                    hour += 12
                elif period.lower() == "a.m." and hour == 12:
                    hour = 0

                current_time = now.hour * 60 + now.minute
                alarm_time_in_minutes = hour * 60 + minute

                if alarm_time_in_minutes > current_time:
                    print(f"Scheduling alarm for label: {alarm.get('label')}")
                    self.startAlarm(alarm)

if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    recognizer = VoiceRecognition(gui)
    # tbf = TimerHandle()
    # tbf.setTimer("Set timer for 10 seconds.")
    # tbf.remove_timer() 
    # tbf.checkTimer()

    # import inspect
    # methods = [func for func, _ in inspect.getmembers(TimeBasedFunctionality, predicate=inspect.isfunction)]
    # print(methods)
    ah=AlarmHandle(recognizer,speech_engine=SpeechEngine())
    # print(ah.timeDivider("set alarm for 12:10"))
    # query1 = "set alarm for 10:30 a.m."
    query2 = "set alarm for 14:30"
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
    # query6 = "set alarm for 9:15 for next day"
    # # print(ah.getRepeat(query4))  # Output: 'daily'
    # print(ah.getRepeat(query5))  # Output: 'monday'
    # print(ah.handleAlarmPrompt(query5))  # Output: 'once'
    # print(ah.handleAlarmPrompt(query6))  # Output: 'once'
    
        # Call chkAlarm to start checking and scheduling alarms
    print("Checking and scheduling alarms...")
    ah.chkAlarm()

    # Prevent the program from exiting
    print("Program is running. Press Ctrl+C to exit.")
        