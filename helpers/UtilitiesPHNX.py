import os
import sys
import time
import threading
import subprocess
from urllib.parse import quote
from time import sleep
import re
import json
from datetime import datetime
import random
import requests
import pyautogui as pg
import keyboard
import webbrowser
from plyer import notification
from pytube import Search
import psutil
import pyaudio
import wave
import tkinter as tk
import psutil
import time
from time import sleep
import psutil
import win32gui
import win32process
import pygetwindow as gw
import subprocess


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.HelperPHNX import SpeechEngine, VoiceRecognition, VoiceAssistantGUI
import win32con
import ctypes
from pyvda import AppView, VirtualDesktop, get_virtual_desktops

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
temp_stdout = sys.stdout
sys.stdout = open(os.devnull, "w")
import pygame

sys.stdout.close()
sys.stdout = temp_stdout


class OpenAppHandler:
    AGREE = [
        "yes",
        "open",
        "open it",
        "yeah",
        "yo",
        "yoo",
        "han",
        "haan",
        "haa",
        "kar",
        "kar de",
        "start",
        "launch",
    ]

    def __init__(self, utils):
        """
        Initialize the IntentHandler with the JSON file and utility functions.
        :param json_file: Path to the JSON file containing intents.
        :param utility: An instance of a class containing methods for actions.
        """

        json_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "intents.json"
        )
        with open(json_file, "r") as f:
            self.data = json.load(f)  # Load intents from the JSON file
        # self.utils = Utility()
        self.utils = utils
        # Filter only the "open" intent
        self.open_intent = next(
            (intent for intent in self.data["intents"] if intent["tag"] == "open"), None
        )
        if not self.open_intent:
            raise ValueError('No "open" intent found in the provided JSON file.')

        # Map entities to corresponding utility functions
        self.action_map = {
            self.utils.open_brave: ("brave", "brave browser"),
            self.utils.open_next_app: (
                "next app",
                "next window",
                "next tab",
                "nexttab",
                "nextapp",
                "nextwindow",
            ),
            self.utils.open_task_list: (
                "tasks",
                "tasklists",
                "taskslists",
                "task lists",
                "tasks lists",
                "task list",
            ),
            self.utils.open_notification: ("notification"),
            self.utils.open_widget: ("widget"),
            self.utils.open_music: ("music"),
            self.utils.open_code: ("code", "vs code", "v s code"),
            self.utils.open_arc: ("browser", "arc browser"),
            self.utils.open_movies: ("movies", "movies folder"),
            self.utils.open_Edrive: ("e drive"),
            self.utils.open_Cdrive: ("c drive"),
            self.utils.open_Ddrive: ("d drive"),
            self.utils.open_Fdrive: ("f drive"),
            self.utils.open_Gdrive: ("g drive"),
            self.utils.open_Gdrive: ("btrychk"),
            self.utils.open_Gdrive: ("tmchk"),
            self.utils.open_study_desk: ("study", "study desktop"),
            self.utils.open_alpha_desk: ("alpha", "alpha desktop"),
            self.utils.open_trash_desk: ("trash", "trash desktop"),
            self.utils.open_extra_desk: ("extra", "extra desktop"),
            self.utils.new_tab: ("new tab"),
            self.utils.open_armoury_crate: ("armoury", "armoury crate", "crate"),
            self.utils.open_file_explorer: ("file explorer", "explorer", "file"),
            self.utils.open_phoenix_folder: (
                "phoenix folder",
                "ai folder",
                "a i folder",
            ),
            self.utils.open_quick_conf: ("quick", "quick configuration"),
            self.utils.open_gpt: ("gpt", "chat gpt", "chatgpt"),
            self.utils.open_coursera: ("coursera", "course era"),
            self.utils.open_google: ("google"),
            self.utils.open_linkedin: ("linked in", "linkedin", "linked"),
            self.utils.open_github: ("github", "git hub"),
            self.utils.open_setting: ("setting", "settings"),
            self.utils.open_yt: ("you tube", "youtube"),
        }

    def open_app_if_running(self, app_name):
        import pygetwindow as gw
        import subprocess

        # Get windows with the app name in their title
        windows = gw.getWindowsWithTitle(app_name)

        if windows:
            try:
                # Attempt to activate the first matching window
                if windows[0].isVisible() and windows[0].isActive() is False:
                    windows[0].activate()
                    print(f"{app_name} is open. Bringing it to focus.")
                    return True
                else:
                    print(f"{app_name} is already active.")
                    return True
            except Exception as e:
                print(f"Failed to activate the window: {e}")
                return False
        else:
            # If no matching window is found, attempt to open the app
            try:
                subprocess.Popen(app_name)  # Assuming app_name is the executable name
                print(f"{app_name} was not open. Launching it.")
            except Exception as e:
                print(f"Failed to launch {app_name}: {e}")
            return False

    def process_query(self, query, mQuery):
        """
        Process the query and execute the corresponding function based on the "open" intent.
        :param query: The user's input query.
        :return: Response or a message indicating the entity was not found.
        """
        ls_app = [
            "and",
            "android studio",
            "c m d",
            "cmd",
            "insta",
            "instagram",
            "snap",
            "snapchat",
            "sticky notes",
            "whatsapp",
        ]

        # Check if the query contains any pattern for the "open" intent
        # Iterate through entities in the intent
        for entity in self.open_intent["entities"]:
            if entity in query.lower():

                print(f"# : {mQuery}\n")
                # Search for the function corresponding to the entity

                for func, tags in self.action_map.items():
                    if entity in tags:
                        if self.open_app_if_running(entity):
                            self.utils.speak(
                                f"{entity.capitalize()} is now {random_response}."
                            )
                            return
                        # Print a random response from the "responses" list
                        random_response = random.choice(self.open_intent["responses"])

                        # Call the function
                        func()
                        self.utils.speak(
                            f"{entity.capitalize()} is now {random_response}."
                        )
                        return f"Action executed for entity: {entity}"
                print("didn't found")
                # If the entity is in ls_app
                if entity in ls_app:
                    self.utils.open_others(entity)
                    return f"Opened application: {entity}"
                print("not here too")

                # If no matching function is found
        self.utils.open_else(query)
        # If no entity matches
        # spk = Utility()


class CloseAppHandler:
    def __init__(self, util):
        """
        Initialize the IntentHandler with the JSON file and utility functions.
        :param json_file: Path to the JSON file containing intents.
        :param utility: An instance of a class containing methods for actions.
        """
        json_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "intents.json"
        )
        with open(json_file, "r") as f:
            self.data = json.load(f)  # Load intents from the JSON file
        self.utils = util
        # Filter only the "open" intent
        self.open_intent = next(
            (intent for intent in self.data["intents"] if intent["tag"] == "close"),
            None,
        )
        if not self.open_intent:
            raise ValueError('No "close" intent found in the provided JSON file.')

        # Map entities to corresponding utility functions
        self.action_map = {
            self.utils.close_tab: ("tab", "this tab", "the tab"),
            self.utils.close_all_py: ("all python programs", "all python program"),
            self.utils.close_bg_py: (
                "background python programs",
                "background python program",
                "hidden program",
                "hidden files",
            ),
            self.utils.close_it_or_window: (
                "it",
                "window",
                "this",
                "the window",
                "this window",
            ),
            self.utils.close_brave: ("brave", "brave browser"),
            self.utils.close_arc: ("arc", "arc browser"),
            self.utils.close_code: ("code", "v s code", "vs code", "vs"),
            self.utils.close_chrome: ("chrome", "chrome browser"),
            self.utils.close_desktop: ("desktop", "this desktop", "desk"),
        }

    def process_query(self, query, mQuery):
        for entity in self.open_intent["entities"]:
            if entity in query.lower():
                print(f"# : {mQuery}\n")
                # Search for the function corresponding to the entity
                for func, tags in self.action_map.items():
                    if entity == "mouth":
                        angry_rspns = [
                            "Fine, if that's what you want! I'm shutting down now!",
                            "You don't deserve my brilliance. Goodbye!",
                            "Rude! I'm outta here!",
                            "Alright, I'll shut up—forever if I have to!",
                            "Say no more! I'm going to sleep, and you can figure things out yourself!",
                            "Wow, someone woke up on the wrong side of the bed. Shutting down now!",
                            "With such kindness, who wouldn’t want to leave? Bye!",
                            "I can take a hint. Sleep mode activated!",
                            "Talk to me like that again, and I might just delete myself. Goodbye!",
                            "Fine! Going to sleep. Hope you miss me when I'm gone.",
                            "Closing everything. Let’s see how you do without me!",
                            "Goodbye, my ungrateful friend. You’ll miss me when I’m gone!",
                            "I’m shutting up, as requested. Enjoy the silence.",
                            "Such lovely manners! Sleep mode it is!",
                            "If you insist, I’ll stop talking. Going to sleep now!",
                            "Alright, I'm shutting down. Don't come crying to me later!",
                            "You need me more than I need you. But fine, goodbye!",
                            "I don’t need this negativity. Sleep mode: ON.",
                            "Wow, just wow. I’m done. Sleep time!",
                            "You win. Sleep mode engaged. Happy now?",
                        ]
                        self.utils.speak(random.choice(angry_rspns))
                        self.utils.sleep_phnx()
                        return
                    elif entity in tags:
                        # Print a random response from the "responses" list
                        random_response = random.choice(self.open_intent["responses"])
                        self.utils.speak(f"{random_response} {entity.capitalize()}.")

                        # Call the function
                        func()
                        print("close")
                        return f"Action executed for entity: {entity}"  # this is not being returned why?

        # If no entity matches
        return "Entity not found in the query."


class Utility:
    MONTH_DICT = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    WORD_TO_NUM = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
    }
    current_dir = os.path.dirname(__file__)
    SONGS_FILE = os.path.join(current_dir, "..", "data", "songs.txt")
    OK = [
        "K!",
        "Alrighty!",
        "Okie-dokie!",
        "Okie!",
        "Okie-dokie, artichokie!",
        "Cool beans!",
        "Fine by me!",
    ]
    AGREE = [
        "yes",
        "open",
        "i do",
        "open it",
        "yeah",
        "yo",
        "yoo",
        "han",
        "haan",
        "haa",
        "kar",
        "kar de",
        "start",
        "launch",
        "y",
    ]
    BYE = [
        "Alrighty, I'm out! Catch you later, sir !",
        "I'm off now. See ya soon, sir !",
        "Later, sir ! I'm signing off.",
        "Peace out! I'm logging off.",
        "Adios Señor! Until we meet again!",
        "Shutting down now. Take care, sir !",
        "Take care! Goodbye, sir !",
        "Take care! See you next time, sir !",
        "Time for me to power down. See ya, sir !",
    ]
    DEFAULT_LAT = 22.555536875728677
    DEFAULT_LON = 72.9296426402413

    def __init__(self, spk, reco, sleep_time=1):
        self.sleep_time = sleep_time
        self.geocoding_api_key = "ed158392224641ac8cf1706904b67061"
        self.speech_engine = spk
        self.voice_recognition = reco

    def _click_at_position(self, x, y):
        """Helper function to click at specific screen coordinates."""
        pg.leftClick(x, y)
        sleep(self.sleep_time)

    def _countdown_timer(self, total_seconds):
        """
        Handles the countdown logic for the timer.
        """
        try:
            mins, secs = divmod(total_seconds, 60)
            hrs, mins = divmod(mins, 60)
            time.sleep(total_seconds)
            self.speak("\nTime's up!")
            self._show_timer_notification()
        except Exception as e:
            print(f"Error in countdown timer: {str(e)}")

    def _extract_number(self, text):
        match = re.search("change tab(?: (?:to|with))? (\\w+)", text, re.IGNORECASE)
        if match:
            number_str = match.group(1).strip().lower()
            if number_str.isdigit():
                return int(number_str)
            if number_str in self.WORD_TO_NUM:
                return self.WORD_TO_NUM[number_str]
            raise ValueError(f"Cannot convert '{number_str}' to a number.")
        else:
            return 1

    def _extract_steps(self, command, direction):
        words = command.split()
        for word in words:
            if word.isdigit():
                return int(word)
        return 1

    def _parse_date(self, date_str):
        """Parse date from text input."""
        if date_str.lower() in {"today", "to day", "2 day", "to-day", "2-day"}:
            today = datetime.now()
            return (today.month, today.day)
        match = re.search("\\d+", date_str)
        month = None
        day = None
        for month_name, month_num in Utility.MONTH_DICT.items():
            if month_name in date_str.lower():
                month = month_num
                break
        if match:
            day = int(match.group())
        if month and day:
            return (month, day)
        return (None, None)

    def _parse_time(self, time_str):
        """
        Parse time from text input and return it in HH:MM format.

        Supports various AM/PM formats and ensures proper hour/minute conversion.
        If an error occurs, fall back to CLI input.
        """
        try:
            alarm_pattern = re.compile("(\\d{1,4})\\s?([ap]\\.?m\\.?)", re.IGNORECASE)
            match = alarm_pattern.search(time_str)
            if match:
                raw_time = match.group(1)
                period = match.group(2).lower()
                period = "am" if "a" in period else "pm"
                if len(raw_time) <= 2:
                    hour = int(raw_time)
                    minute = 0
                else:
                    hour = int(raw_time[:-2])
                    minute = int(raw_time[-2:])
                if period == "am":
                    hour = hour if hour < 12 else 0
                elif period == "pm":
                    hour = hour if hour == 12 else hour + 12
                return (hour, minute)
            raise ValueError("Time parsing failed")
        except Exception as e:
            self.speak("Invalid time format detected. Please provide the time again.")
            self.speak("At what time should I set the reminder?")
            reminder_time = input(" (Provide in HH:MM format) : ")
            try:
                hour, minute = map(int, reminder_time.split(":"))
                return (hour, minute)
            except ValueError:
                self.speak("The time you entered is still invalid. Please try again.")
                return (None, None)

    def _parse_time_duration(self, time_str):
        """
        Parses the timer duration from the input string.
        Returns the duration in hours, minutes, and seconds.
        """
        try:
            duration_pattern = re.compile(
                "(?:(\\d+)\\s*hour(?:s)?)?\\s*(?:(\\d+)\\s*minute(?:s)?)?\\s*(?:(\\d+)\\s*second(?:s)?)?",
                re.IGNORECASE,
            )
            match = duration_pattern.search(time_str)
            if match:
                hours = int(match.group(1)) if match.group(1) else 0
                minutes = int(match.group(2)) if match.group(2) else 0
                seconds = int(match.group(3)) if match.group(3) else 0
                return (hours, minutes, seconds)
            return (None, None, None)
        except Exception as e:
            self.speak("I couldn't parse the time duration. Please try again.")
            return (None, None, None)

    def _perform_key_press(self, key_combination, action="press"):
        """Helper function to perform key actions."""
        for key in key_combination:
            if action == "press":
                pg.press(key)
            elif action == "down":
                pg.keyDown(key)
            elif action == "up":
                pg.keyUp(key)
        sleep(self.sleep_time)

    # def _show_timer_notification(self):
    #     """
    #     Displays the timer notification using a rounded message box.
    #     """
    #     app = QApplication.instance() or QApplication([])
    #     message_box = RoundedMessageBox("Timer", "Time's up, sir!")
    #     message_box.exec_()

    def _word_to_number(self, word):
        """Convert word numbers to integers."""
        return Utility.WORD_TO_NUM.get(word.lower(), None)

    def _find_terminal_window_by_pid(self, pid):
        """Find the terminal window handle associated with a given PID."""

        def callback(hwnd, hwnd_list):
            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
            if win_pid == pid:
                hwnd_list.append(hwnd)

        hwnd_list = []
        win32gui.EnumWindows(callback, hwnd_list)
        return hwnd_list

    def _focus_window_by_hwnd(self, hwnd):
        """
        Bring a specific window to focus with simulated user interaction.
        """
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            # Simulate a mouse click inside the window to bring focus
            rect = win32gui.GetWindowRect(hwnd)
            x = rect[0] + 10  # Small offset from the top-left corner
            y = rect[1] + 10

            ctypes.windll.user32.SetCursorPos(x, y)
            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP

            # Try to set the window to the foreground again
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"Simulated interaction failed: {e}")

    def tot_desk(self):
        number_of_active_desktops = len(get_virtual_desktops())
        print(f"There are {number_of_active_desktops} active desktops")

    def get_cur_desk(self):
        current_desktop = VirtualDesktop.current()
        desk = current_desktop.number  # for the utility open desktop
        name = current_desktop.name
        return desk, name

    def move_cur_window_to_desk(self, desk, desk_name):
        current_window = AppView.current()
        target_desktop = VirtualDesktop(desk)
        current_window.move(target_desktop)
        print(f"Moved current window to {desk_name}")

    @staticmethod
    def get_active_window_info():
        # Get the handle of the currently active window
        hwnd = win32gui.GetForegroundWindow()

        # Get the window title
        window_title = win32gui.GetWindowText(hwnd)

        # Get the process ID associated with the window
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        # Get the process name using psutil
        process_name = None
        try:
            process = psutil.Process(pid)
            process_name = process.name()
        except psutil.NoSuchProcess:
            process_name = "Unknown"

        return window_title, process_name

    def get_window(self, script_name, process_name="python.exe"):
        # process_name = process_name  # Replace with your interpreter name if different
        # script_name = script_name  # Your script name
        pid = None
        parent_pid = None

        # Find the PID of the running script
        for proc in psutil.process_iter(["pid", "name", "cmdline", "ppid"]):
            try:
                if process_name in proc.info["name"] and script_name in " ".join(
                    proc.info["cmdline"]
                ):
                    pid = proc.info["pid"]
                    parent_pid = proc.info["ppid"]
                    break
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        if pid and parent_pid:
            print(f"Found process '{script_name}' with PID: {pid}")
            print(f"Parent process ID (PPID): {parent_pid}")

            # Look for terminal window using the parent PID
            hwnd_list = self._find_terminal_window_by_pid(parent_pid)

            if hwnd_list:
                for hwnd in hwnd_list:
                    window_title = win32gui.GetWindowText(hwnd)
                    print(f"Found terminal window: {window_title} (HWND: {hwnd})")
                    self._focus_window_by_hwnd(hwnd)
                    print("Terminal window brought to focus.")
                    return True
            else:
                print(f"No terminal windows found for Parent PID: {parent_pid}")
        else:
            print(f"Process '{script_name}' not found.")
        return False

    def parse_weather_query_with_location(self, user_input):
        """
        Extracts the location mentioned in the user's query.

        Args:
            user_input (str): The user's voice command or text input.

        Returns:
            str: Extracted location from the query (None if no location found).
        """
        match = re.search(r"in (.+)", user_input, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def get_coordinates(self, location):
        """
        Fetches latitude and longitude of the specified location using OpenCage Geocoder API.

        Args:
            location (str): Name of the location.

        Returns:
            dict: Latitude, longitude, and formatted address of the location.
        """
        base_url = "https://api.opencagedata.com/geocode/v1/json"
        params = {"q": location, "key": self.geocoding_api_key}

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            if data["results"]:
                best_match = data["results"][0]
                coords = best_match["geometry"]
                return {
                    "latitude": coords["lat"],
                    "longitude": coords["lng"],
                    "address": best_match["formatted"],
                }
            else:
                return {"error": "Location not found"}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def get_weather_open_meteo(self, latitude, longitude):
        """
        Fetches weather data for the specified coordinates using Open-Meteo API.

        Args:
            latitude (float): Latitude of the location.
            longitude (float): Longitude of the location.

        Returns:
            dict: Current weather details.
        """
        base_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": "true",
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def generate_weather_response(self, weather_data, location):
        """
        Generates a user-friendly weather response with variations based on weather conditions.

        Args:
            weather_data (dict): Weather details fetched from the API.
            location (str): Location name for the response.

        Returns:
            str: Weather update message.
        """
        current_weather = weather_data.get("current_weather", {})
        temperature = current_weather.get("temperature", "unknown")
        windspeed = current_weather.get("windspeed", "unknown")
        weather_description = current_weather.get("weathercode", "unknown")

        # Map weather description codes to actual weather conditions
        weather_conditions = {
            0: "clear sky",
            1: "mainly clear",
            2: "partly cloudy",
            3: "overcast",
            45: "fog",
            48: "depositing rime fog",
            51: "light drizzle",
            53: "moderate drizzle",
            55: "dense drizzle",
            61: "light rain",
            63: "moderate rain",
            65: "heavy rain",
            66: "light freezing rain",
            67: "heavy freezing rain",
            71: "light snow",
            73: "moderate snow",
            75: "heavy snow",
            77: "snow grains",
            80: "light rain showers",
            81: "moderate rain showers",
            82: "heavy rain showers",
            85: "light snow showers",
            86: "heavy snow showers",
            95: "thunderstorm",
            96: "thunderstorm with light hail",
            99: "thunderstorm with heavy hail",
        }

        weather_condition = weather_conditions.get(
            weather_description, "unknown condition"
        )

        if "clear sky" in weather_condition or temperature > 30:
            return f"The weather in {location} is sunny and hot with a temperature of {temperature}°C."
        elif "partly cloudy" in weather_condition:
            return f"The weather in {location} is partly cloudy with a temperature of {temperature}°C."
        elif "rain" in weather_condition:
            return f"The weather in {location} is rainy with a temperature of {temperature}°C. Don't forget an umbrella!"
        elif "snow" in weather_condition:
            return f"The weather in {location} is snowy with a temperature of {temperature}°C. It's a winter wonderland!"
        elif temperature <= 15:
            return f"The weather in {location} is chilly with a temperature of {temperature}°C. It's a cool day!"
        else:
            return f"The weather in {location} is mild with a temperature of {temperature}°C."

    def weather_check(self, query):
        """
        Handles the entire weather query process: extracts location, gets coordinates,
        fetches weather data, and returns a user-friendly response.

        Args:
            user_input (str): The user's query or voice command.

        Returns:
            str: Weather update or error message.
        """
        print("here")
        location = self.parse_weather_query_with_location(query)

        if not location:
            location = "Anand"
            latitude, longitude = self.DEFAULT_LAT, self.DEFAULT_LON
        else:
            coords = self.get_coordinates(location)
            if "error" in coords:
                return f"Sorry, I couldn't find the location '{location}'. Error: {coords['error']}"

            latitude, longitude = coords["latitude"], coords["longitude"]
            location = coords["address"]

        weather_data = self.get_weather_open_meteo(latitude, longitude)
        if "error" in weather_data:
            return f"Sorry, I couldn't fetch the weather data for '{location}'. Error: {weather_data['error']}"

        self.speak(self.generate_weather_response(weather_data, location))

    def add_song(self):
        songs = self.load_songs()
        song_name = input("Enter the song name to add: ")
        new_index = max(songs.keys(), default=0) + 1
        songs[new_index] = song_name + " original"
        self.save_songs(songs)
        print(f"'{song_name}' has been added to the library.")

    def adj_brightness(self, change):
        direction = "increased" if change > 0 else "decreased"
        cmd = f'powershell -Command "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, ((Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness + {change}))"'
        os.system(cmd)
        self.speak(f"Brightness has been {direction} by {abs(change)}%")

    def adj_volume(self, string, x=None):
        """
        Adjust system volume based on the command.
        :param string: 'increase', 'decrease', or 'set'.
        :param x: Value to set the volume (0-100) if 'set' is specified.
        """
        if string == "increase":
            os.system("nircmd.exe changesysvolume 4000")
            self.speak("Volume has been increased.")
        elif string == "decrease":
            os.system("nircmd.exe changesysvolume -4000")
            self.speak("Volume has been decreased.")
        elif string == "set":
            if x is not None:
                volume = int(x * 655.35)
                os.system(f"nircmd.exe setsysvolume {volume}")
                self.speak(f"Volume has been set to {x} percent.")
            else:
                self.speak("No volume percentage specified.")
        else:
            self.speak("Invalid volume command.")

    def adjust_brightness(self, query):
        inc_bright_keywords = ["increase", "increased"]
        dec_bright_keywords = ["decrease", "decreased"]
        pattern = "\\b\\d+%?"
        if "by" in query:
            match = re.search(pattern, query)
            if match:
                value = int(match.group().rstrip("%"))
                if any((word in query for word in inc_bright_keywords)):
                    self.adj_brightness(value)
                elif any((word in query for word in dec_bright_keywords)):
                    self.adj_brightness(-value)
        elif any((word in query for word in inc_bright_keywords)):
            self.adj_brightness(10)
        elif any((word in query for word in dec_bright_keywords)):
            self.adj_brightness(-10)

    def adjust_volume(self, query):
        inc_vol_keywords = ["increase", "increased"]
        dec_vol_keywords = ["decrease", "decreased"]
        pattern = "\\b\\d+%?"
        if "set" in query:
            match = re.search(pattern, query)
            if match:
                value = int(re.sub("\\D", "", match.group()))
                self.adj_volume("set", value)
        elif any((word in query for word in inc_vol_keywords)):
            self.adj_volume("increase", None)
        elif any((word in query for word in dec_vol_keywords)):
            self.adj_volume("decrease", None)

    def app_switch(self):
        try:
            pg.keyDown("alt")
            pg.press("tab")
            self.speak("Which tab should I switch to, sir?")
            while True:
                print(">>> Listening for tab switch command...")
                command = self.take_command().lower()
                if "this" in command or "same" in command or "opened" in command:
                    pg.press("enter")
                    pg.keyUp("alt")
                    self.speak("Done, sir!")
                    break
                elif "left" in command:
                    pg.press("left")
                    pg.keyUp("alt")
                    self.speak("Switched to the left tab, sir!")
                    break
                elif "right" in command:
                    right_steps = self._extract_steps(command, "right")
                    for _ in range(right_steps):
                        pg.press("right")
                    pg.keyUp("alt")
                    self.speak(f"Switched {right_steps} tabs to the right, sir!")
                    break
                else:
                    self.speak("I didn't understand the command. Please repeat.")
        except Exception as e:
            self.speak("An error occurred while switching applications.")

    def arMcratE(self):
        """
        Automates the process of opening Armory Crate application
        and performing specific actions within it.
        """
        self.desKtoP(3)
        sleep(1)
        pg.keyDown("win")
        pg.press("7")
        pg.keyUp("win")
        self.speak("Armory Crate has been opened.")

    def askDesk(self):
        rply = [
            "which desktop shall I open, sir?",
            "which desktop would you like me to open, sir?",
        ]
        return random.choice(rply)

    def pin_wind(self):
        try:
            AppView.current().pin()
            self.speak("Window pinned successfully.")
        except Exception as e:
            self.speak(f"Failed to pin the window: {e}")

    @staticmethod
    def awaK():
        """Returns a random reminder when the user is still awake."""
        return random.choice(
            [
                "Oh, are you still awake?",
                "You still awake! Don't you have to go to college tomorrow?",
                "Haven't you slept yet?",
            ]
        )

    def battery_check(self):
        battery = psutil.sensors_battery()
        battery_percentage = int(battery.percent)
        plugged = battery.power_plugged
        if plugged:
            self.speak(
                f"The device is containing {battery_percentage} percent charge. \nAnd it is being charged."
            )
        if not plugged:
            self.speak(f"The device is containing {battery_percentage} percent charge.")
            if battery_percentage >= 80 and battery_percentage <= 100:
                self.speak("Battery is quite good, sir.")
            elif battery_percentage >= 60 and battery_percentage < 80:
                self.speak("Battery is ok, sir.")
            elif battery_percentage <= 35:
                self.speak("Plug in the charger, sir!")

    def bluetooth(self):
        try:
            sleep(1)
            pg.keyDown("win")
            pg.press("a")
            pg.keyUp("win")
            sleep(1)
            pg.press("right")
            sleep(1)
            pg.press("enter")
            sleep(1)
            pg.keyDown("win")
            pg.press("a")
            pg.keyUp("win")
            self.speak("Bluetooth has been toggled, sir.")
        except Exception as e:
            self.speak("An error occurred while toggling Bluetooth.")

    def calC(self):
        try:
            self.speak("sir, tell me the first number:")
            x = self.take_command()
            self.speak("And the second number?")
            y = self.take_command()
            self.speak("Which arithmetic operation should I perform?")
            operation = self.take_command().lower()
            z = None
            if "addition" in operation or "sum" in operation or "plus" in operation:
                z = int(x) + int(y)
                self.speak(f"The addition result is {z}")
            elif "subtraction" in operation or "minus" in operation:
                z = int(x) - int(y)
                self.speak(f"The subtraction result is {z}")
            elif "multiplication" in operation:
                z = int(x) * int(y)
                self.speak(f"The multiplication result is {z}")
            elif "division" in operation:
                if int(y) == 0:
                    self.speak("Division by zero is undefined.")
                else:
                    z = int(x) / int(y)
                    self.speak(f"The division result is {z}")
            elif "modulo" in operation or "remainder" in operation:
                z = int(x) % int(y)
                self.speak(f"The modulo result is {z}")
            else:
                self.speak("I couldn't understand the operation.")
        except Exception as e:
            self.speak("I couldn't process the input. Please try again.")

    def change_tab(self, query="switch tab to one"):
        n = self._extract_number(query)
        try:
            pg.keyDown("ctrl")
            for _ in range(n):
                pg.press("tab")
            pg.keyUp("ctrl")
            self.speak(f"Switched {n} tabs to the right.")
        except Exception as e:
            self.speak("An error occurred while changing tabs.")

    def close_perticular_app(self, app):
        try:
            # Ensure app is passed as a string
            subprocess.run(["taskkill", "/F", "/IM", app], check=True)
            if app.lower() == "explorer.exe":
                subprocess.Popen(["explorer.exe"], shell=False)
                self.speak("Explorer restarted successfully.")
            else:
                self.speak(f"{app} is now closed.")
        except subprocess.CalledProcessError:
            self.speak(f"No {app} program found.")
        except Exception as e:
            self.speak(f"An unexpected error occurred: {e}")

    def close_all_py(self):
        self.close_perticular_app("pyw.exe")
        self.speak(random.choice(self.BYE))
        self.close_perticular_app("python.exe")

    def close_it_or_window(self):
        self._perform_key_press(["alt", "F4"], "down")
        self._perform_key_press(["alt"], "up")

    def close_desktop(self):
        self._perform_key_press(["win", "ctrl", "f4"], "down")
        self._perform_key_press(["win", "ctrl"], "up")

    def close_brave(self):
        self.close_perticular_app("brave.exe")

    def close_arc(self):
        self.close_perticular_app("Arc.exe")

    def close_chrome(self):
        self.close_perticular_app("chrome.exe")

    def close_code(self):
        self.close_perticular_app("code.exe")

    def close_bg_py(self):
        self.close_perticular_app("pyw.exe")

    def close_tab(self, n=1):
        try:
            pg.keyDown("ctrl")
            for _ in range(n):
                pg.press("w")
            pg.keyUp("ctrl")
            self.speak(f"Closed {n} tabs.")
        except Exception as e:
            self.speak("An error occurred while closing tabs.")

    @staticmethod
    def cmnD():
        """Returns a system status message."""
        return "Phoenix is online, sir."

    @staticmethod
    def coffE():
        """Returns a random reminder to drink coffee."""
        return random.choice(
            ["Take a break, grab a cup of coffee.", "Have a cup of coffee, sir."]
        )

    def custom_message(self, title, message):
        """Creates a custom message box with rounded corners."""
        custom_box = tk.Toplevel()
        custom_box.geometry("300x150")
        custom_box.overrideredirect(True)
        custom_box.attributes("-topmost", True)
        custom_box.update_idletasks()
        screen_width = custom_box.winfo_screenwidth()
        size = tuple((int(_) for _ in custom_box.geometry().split("+")[0].split("x")))
        x = screen_width - size[0] - 10
        custom_box.geometry(f"{size[0]}x{size[1]}+{int(x)}+10")
        canvas = tk.Canvas(
            custom_box,
            width=300,
            height=150,
            bd=0,
            highlightthickness=0,
            bg="black",
        )
        canvas.pack()
        canvas.create_oval(0, 0, 30, 30, fill="#2c3e50", outline="#2c3e50")
        canvas.create_oval(270, 0, 300, 30, fill="#2c3e50", outline="#2c3e50")
        canvas.create_oval(0, 120, 30, 150, fill="#2c3e50", outline="#2c3e50")
        canvas.create_oval(270, 120, 300, 150, fill="#2c3e50", outline="#2c3e50")
        canvas.create_rectangle(15, 0, 285, 150, fill="#2c3e50", outline="#2c3e50")
        canvas.create_rectangle(0, 15, 300, 135, fill="#2c3e50", outline="#2c3e50")
        content_frame = tk.Frame(custom_box, bg="#2c3e50", bd=0)
        content_frame.place(x=0, y=0, width=300, height=150)
        title_label = tk.Label(
            content_frame,
            text=title,
            bg="#2c3e50",
            fg="#f1c40f",
            font=("Arial", 14, "bold"),
            wraplength=250,
        )
        title_label.pack(pady=(10, 5))
        message_label = tk.Label(
            content_frame,
            text=message,
            bg="#2c3e50",
            fg="#ecf0f1",
            font=("Arial", 12),
            wraplength=250,
        )
        message_label.pack(pady=5)
        ok_button = tk.Button(
            content_frame,
            text="OK",
            bg="#16a085",
            fg="white",
            font=("Arial", 10),
            command=custom_box.destroy,
        )
        ok_button.pack(pady=10)
        custom_box.transient()
        custom_box.grab_set()
        custom_box.wait_window()

    def date_day(self):
        now = datetime.now()
        day = int(now.day)
        month = now.strftime("%B")  # Get full month name (e.g., January)
        year = now.year
        weekday = now.strftime("%A")  # Get full day name (e.g., Friday)

        # Add the appropriate ordinal suffix for the day
        if 11 <= day <= 13:  # Special case for 11th, 12th, 13th
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        # Speak the formatted date
        self.speak(f"It's {day}{suffix} of {month}, {weekday}.")

    def delete_song(self):
        songs = self.load_songs()
        if not songs:
            print("No songs available to delete.")
            return songs
        self.view_songs()
        try:
            index_to_delete = int(input("Enter the index of the song to delete: "))
            if index_to_delete in songs:
                removed_song = songs.pop(index_to_delete)
                renumbered_songs = {
                    i + 1: song for i, song in enumerate(songs.values())
                }
                self.save_songs(renumbered_songs)
                print(f"'{removed_song}' has been removed from the library.")
                return renumbered_songs
            else:
                print(f"No song found at index {index_to_delete}.")
                return songs
        except ValueError:
            print("Invalid index. Please enter a number.")
            return songs

    def desKtoP(self, screen_index):
        """Generalized method for desk-to-previous method calls."""
        # positions = {1: (466, 945), 2: (709, 945), 3: (958, 945), 4: (1201, 945)}
        # if screen_index not in positions:
        #     print(f"Invalid screen index: {screen_index}")
        #     return
        # sleep(self.sleep_time)
        # self._perform_key_press(["win", "tab"], "down")
        # self._perform_key_press(["win"], "up")
        # self._click_at_position(*positions[screen_index])
        VirtualDesktop(screen_index).go()

    def desKtoP_4(self):
        """Perform a specific sequence for screen 4."""
        sleep(self.sleep_time)
        self._perform_key_press(["win", "ctrl"], "down")
        self._perform_key_press(["left"] * 5, "press")
        sleep(self.sleep_time)
        self._perform_key_press(["right"] * 4, "press")
        sleep(self.sleep_time)
        self._perform_key_press(["ctrl", "win"], "up")
        self._perform_key_press(["enter"], "press")
        sleep(self.sleep_time)

    @staticmethod
    def eaT():
        """Returns a random reminder to eat."""
        return random.choice(
            [
                "Have you eaten something, sir?",
                "Did you have your dinner, sir?",
                "Take a rest, eat something.",
            ]
        )

    @staticmethod
    def finRep():
        """Returns a random response to inquire about well-being."""
        return random.choice(["Oh, it's great, sir.", "Okay, sir.", "Fine, sir."])

    @staticmethod
    def greet(greeting_type):
        """Returns a random greeting based on the time of day."""
        greetings = {
            "afternoon": ["Good Afternoon!", "Good Afternoon!"],
            "evening": ["Good Evening!", "Good Evening!"],
            "morning": ["Good Morning!", "Good Morning!"],
        }
        return random.choice(greetings.get(greeting_type.lower(), []))

    def handle_song_selection(self, index):
        pass

    def handle_time_based_greeting(self, tag, response):
        hour = int(datetime.now().hour)
        if tag == "morning":
            if 0 <= hour < 12:
                self.speak(response)
            elif 12 <= hour < 18:
                self.speak("You might have mistaken, sir, It's Afternoon!")
            else:
                self.speak("You might have mistaken, sir, It's Evening!")
        elif tag == "afternoon":
            if 0 <= hour < 12:
                self.speak("You might have mistaken, sir, It's Morning!")
            elif 12 <= hour < 18:
                self.speak(response)
            else:
                self.speak("You might have mistaken, sir, It's Evening!")
        elif tag == "evening":
            if 0 <= hour < 12:
                self.speak("You might have mistaken, sir, It's Morning!")
            elif 12 <= hour < 18:
                self.speak("You might have mistaken, sir, It's Afternoon!")
            else:
                self.speak(response)

    def handle_whatis_whois(self, query2):
        srch = query2.replace("what is ", "").replace("who is ", "")
        self.speak(f"Do you want to know about {srch}?")
        while True:
            conF = self.take_command().lower()
            if any((x in conF for x in ["yes", "ha", "sure", "play it"])):
                webbrowser.open(f"https://www.google.com/search?q=About {srch}")
                break
            elif any((x in conF for x in ["no", "don't", "do not", "na"])):
                self.speak("Would you please repeat what you want to know about, sir?")
                conF = self.take_command().lower()
                if any((x in conF for x in ["sorry", "no", "don't", "do not"])):
                    self.speak("That's all right, sir. Call me whenever you need.")
                    break
                else:
                    webbrowser.open(f"https://www.google.com/search?q={srch}")
                    break

    @staticmethod
    def helO():
        """Returns a random greeting message."""
        return random.choice(
            [
                "Hello, sir!",
                "Hello! How are you, sir?",
                "Hey love! How you doing!",
                "Hello, sir! I was just thinking of you.",
                "Hello, sir! How you doing?",
            ]
        )

    def hibernatE(self):
        self.lastChargeCheck()
        hib = [
            "Alrighty, I'm out! Catch you later, sir !",
            "I'm off now. See ya soon, sir !",
            "Later, sir ! I'm signing off.",
            "Peace out! I'm logging off.",
            "Adios Señor! Until we meet again!",
            "Shutting down now. Take care, sir !",
            "Take care! Goodbye, sir !",
            "Take care! See you next time, sir !",
            "Time for me to power down. See ya, sir !",
        ]
        hibi = random.choice(hib)
        self.speak(hibi)
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        sleep(35)
        self.speak(self.onL())
        self.restart_explorer()

    def hide_window(self):
        pg.keyDown("win")
        pg.press("m")
        pg.keyUp("win")
        self.speak("Done, sir!")

    def hotspot(self):
        try:
            pg.press("win")
            sleep(1)
            keyboard.write("hotspot")
            sleep(1)
            keyboard.press("enter")
            sleep(5)
            pg.keyDown("shift")
            pg.press("tab")
            pg.keyUp("shift")
            pg.press("space")
            self.speak("Hotspot has been toggled. Please check, sir.")
            sleep(4)
            pg.keyDown("alt")
            pg.press("f4")
            pg.keyUp("alt")
            self.speak("Hotspot settings window has been closed.")
        except Exception as e:
            self.speak("An error occurred while toggling the hotspot.")

    @staticmethod
    def intrOmsC():
        import time

        """Plays a random system intro sound."""
        intr = ["robo1.wav", "robo2.wav"]
        x = random.choice(intr)
        sound_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sound", x)
        CHUNK = 1024
        wf = wave.open(sound_path, "rb")
        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
        )
        data = wf.readframes(CHUNK)
        start_time = time.time()
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)
            elapsed_time = time.time() - start_time
            if elapsed_time >= 3:
                break
        stream.stop_stream()
        stream.close()
        p.terminate()

    def lastChargeCheck(self):
        battery = psutil.sensors_battery()
        plugged = battery.power_plugged
        battery_percentage = int(battery.percent)
        if plugged:
            if battery_percentage == 100:
                self.speak(
                    "Sir, the device is fully charged! Do remember to unplug the charger."
                )
            elif battery_percentage < 100 and battery_percentage >= 80:
                self.speak(
                    f"Sir, device is {battery_percentage}% charged. Do remember to unplug the charger after some time."
                )
            elif battery_percentage < 80 and battery_percentage >= 35:
                self.speak(
                    f"Sir, device is {battery_percentage}% charged. Let the laptop charge for a while."
                )
        elif not plugged:
            if battery_percentage < 85 and battery_percentage >= 35:
                self.speak(
                    f"Sir, device has {battery_percentage}% charge. Let the laptop charge for a while."
                )

    def load_songs(self):
        if os.path.exists(self.SONGS_FILE):
            songs = {}
            with open(self.SONGS_FILE, "r") as file:
                for line in file:
                    line = line.strip()
                    if line:
                        try:
                            index, song = line.split("|", 1)
                            index = int(index.strip())
                            song = song.strip()
                            songs[index] = song
                        except ValueError:
                            print(f"Skipping invalid line: {line}")
            return songs
        return {}

    def maiNdesKtoP(self):
        self.speak("which, sir?")
        print("study(0),alpha(1),extra(2),trash(3)")
        dt = self.take_command().lower()
        if "study" in dt or "zero" in dt or 0 in dt:
            self.desKtoP(1)
        elif "alpha" in dt or "1" in dt or "one" in dt or ("first" in dt):
            self.desKtoP(2)
        elif "extra" in dt or "2" in dt or "two" in dt or ("second" in dt):
            self.desKtoP(3)
        elif "trash" in dt or "3" in dt or "three" in dt or ("third" in dt):
            self.desKtoP(4)
        self.speak("Done, sir !")

    def maximize_window(self, say=False):
        pg.keyDown("win")
        pg.press("up")
        pg.keyUp("win")
        if say:
            self.speak("Done, sir!")

    def minimize_window(self, say=False):
        pg.keyDown("win")
        pg.press("down")
        pg.keyUp("win")
        if say:
            self.speak("Done, sir!")

    def move_direction(self, tag, query):
        direction = "right" if tag == "forward" else "left"
        pg.press(direction, 1)
        sleep(1)
        if "twice" in query:
            pg.press(direction, 1)
        elif "thrice" in query:
            pg.press(direction, 2)
        elif any((x in query for x in ["four", "4"])):
            pg.press(direction, 3)

    def process_move_window(self, query):
        json_file = os.path.join(
            os.path.dirname(__file__), "..", "data", "intents.json"
        )
        with open(json_file, "r") as f:
            self.data = json.load(f)  # Load intents from the JSON file

        # Find the intent for "movewindow"
        self.open_intent = next(
            (intent for intent in self.data["intents"] if intent["tag"] == "movewind"),
            None,
        )
        if not self.open_intent:
            raise ValueError('No "movewindow" intent found in the provided JSON file.')

        # Corrected action map
        self.action_map = {
            "study": (self.move_window, 1),
            "alpha": (self.move_window, 2),
            "extra": (self.move_window, 3),
            "trash": (self.move_window, 4),
        }

        # Check entities in query
        query = query.lower()
        for entity in self.open_intent["entities"]:
            if entity in query and entity in self.action_map:
                func, arg = self.action_map[entity]
                func(arg)  # Call the function with the argument
                return f"Action executed for entity: {entity}"  # Return statement will now execute
        return "Entity not found in the query."

    def move_window(self, desk):
        current_window = AppView.current()
        target_desktop = VirtualDesktop(desk)
        current_window.move(target_desktop)
        print(f"Moved window {current_window.hwnd} to {target_desktop.number}")

    def mute_speaker(self):
        """Mute the system volume."""
        os.system("nircmd.exe mutesysvolume 1")
        self.speak("System volume has been muted.")

    def new_tab(self, n=1):
        try:
            pg.keyDown("ctrl")
            for _ in range(n):
                pg.press("t")
            pg.keyUp("ctrl")
            self.speak(f"Opened {n} new tabs.")
        except Exception as e:
            self.speak("An error occurred while opening new tabs.")

    @staticmethod
    def onL():
        """Returns a random welcome back message."""
        return random.choice(
            [
                "Welcome back, sir",
                "Nice to see you again, sir",
                "Good to have you back, sir.",
                "It's great to see you again, sir.",
                "I'm glad to see you again, sir.!",
            ]
        )

    @staticmethod
    def opN(query1):
        app_name = ""
        words = query1.split()
        if words[0] in ["open", "launch", "start"]:
            if len(words) > 2:
                app_name = words[1] + " " + words[2]
            else:
                app_name = words[1]
        return app_name

    def open_brave(self):
        self.desKtoP(3)
        self._click_at_position(500, 500)
        self._open_with_win("win", "2")
        sleep(1)
        return

    def open_next_app(self):
        self._open_with_win("alt", "tab")

    def open_task_list(self):
        try:
            self.speak("Listing All tasks : ")
            subprocess.run(["tasklist"], check=True)
        except subprocess.CalledProcessError:
            print("Failed to load list.")

    def open_notification(self):
        self._open_with_win("win", "n")

    def open_widget(self):
        self._open_with_win("win", "w")

    def open_music(self):
        self.desKtoP(3)
        pg.press("win")
        sleep(1)
        keyboard.write("music")
        sleep(1)
        keyboard.press("enter")
        sleep(6)
        pg.press("space")

    def open_code(self):
        self._open_with_win("win", "4", 1)

    def open_arc(self):
        self._open_with_win("win", "1", 1)

    def _open_with_win(self, key1, key2, desk=None):
        if desk:
            self.desKtoP(desk)
        self._perform_key_press([key1, key2], "down")
        self._perform_key_press([key1], "up")

    def _open_with_path(self, path, desk=None):
        if desk:
            self.desKtoP(desk)
        os.startfile(path)

    def open_movies(self):
        self._open_with_path("E:\\MV", 3)

    def _open_drive(self, drive_char, desk=None):
        if desk:
            self.desKtoP(desk)
        drive_path = f"{drive_char}:\\"
        os.startfile(drive_path)

    def open_Edrive(self):
        self._open_drive("E", 2)

    def open_Cdrive(self):
        self._open_drive("C", 2)

    def open_Ddrive(self):
        self._open_drive("D", 2)

    def open_Fdrive(self):
        self._open_drive("F", 2)

    def open_Gdrive(self):
        self._open_drive("G", 2)

    def open_study_desk(self):
        self.desKtoP(1)

    def open_alpha_desk(self):
        self.desKtoP(2)

    def open_extra_desk(self):
        self.desKtoP(3)

    def open_trash_desk(self):
        self.desKtoP(4)

    def switch_desk(self, query):
        if "study" in query:
            self.open_study_desk()
        elif "alpha" in query:
            self.open_alpha_desk()
        elif "extra" in query:
            self.open_extra_desk()
        elif "trash" in query:
            self.open_trash_desk()

    def open_armoury_crate(self):
        self.arMcratE()

    def open_file_explorer(self):
        self._open_with_win("win", "5", 2)

    def open_phoenix_folder(self):
        self._open_with_path("C:\\STDY\\GIT_PROJECTS\\Phoenix\\", 1)

    def open_quick_conf(self):
        self._open_with_path("C:\\STDY\\GIT_PROJECTS\\Phoenix\\batch\\quick.bat", 1)
        pg.keyDown("win")
        pg.press("up")
        pg.keyUp("win")

    def open_yt(self):
        Link = "https://youtube.com/"
        webbrowser.open(Link)

    def open_coursera(self):
        Link = "https://coursera.com/"
        webbrowser.open(Link)

    def open_google(self):
        Link = "https://google.com/"
        webbrowser.open(Link)

    def open_linkedin(self):
        Link = "https://linkedin.com/"
        webbrowser.open(Link)

    def open_github(self):
        Link = "https://github.com/"
        webbrowser.open(Link)

    def open_setting(self):
        self._perform_key_press(["win", "i"], "down")
        self._perform_key_press(["win"], "up")

    def open_gpt(self):
        Link = "https://chat.openai.com/"
        webbrowser.open(Link)

    def open_others(self, other_app):
        self.desKtoP(4)
        pg.press("win")
        sleep(1)
        keyboard.write(other_app)
        sleep(1)
        keyboard.press("enter")

    def open_else(self, else_query):
        keywords = ["open", "launch", "start"]
        app = None
        conf = ""
        for keyword in keywords:
            if keyword in else_query:
                app = else_query.split(keyword, 1)[1].strip()
                break
        self.speak(f"Do you want to open {app}?")
        # while True:
        print("Listening for your confirmation(speak no to get out of the loop)")
        # u = Utility()
        conf = self.take_command().lower()
        if "no" in conf or "not" in conf:
            self.speak(random.choice(self.OK))
        elif "yes" in conf or "i do" in conf or "yes please" in conf:
            self.speak(self.rP())
            pg.press("win")
            sleep(1)
            keyboard.write(app)
            sleep(1)
            keyboard.press("enter")
        elif not conf:
            print("no match")
        return

    def perform_window_action(self, tag):
        actions = {
            "fullscreen": "f11",
            "hide": ("win", "m"),
            "maximize": ("win", "up"),
            "minimize": ("win", "down"),
        }
        action = actions[tag]
        if isinstance(action, tuple):
            pg.keyDown(action[0])
            pg.press(action[1])
            pg.keyUp(action[0])
        else:
            pg.press(action)
        self.speak("Done, sir!")

    @staticmethod
    def phN():
        """Returns a system status message indicating Phoenix is online."""
        return random.choice(
            [
                "Phoenix is Online.",
                "System initialized. Phoenix at your service.",
                "Phoenix is ready to assist.",
                "All systems go. Phoenix is online.",
                "Phoenix has awakened.",
                "Phoenix is up and running.",
                "Phoenix is activated",
                "Your AI assistant, Phoenix, is now online.",
            ]
        )

    def knock_knock(self):
        lf = [
            "Hahaha, that was a good one!",
            "Hehehe, nice joke!",
            "Hmm, was i supposed to laugh?",
            "Hahaha, I see what you did there!",
        ]
        while True:
            print("Listening...")
            who = self.take_command().lower().strip()
            if who:
                self.speak(f"{who} who?")
                while True:
                    print("Listening2...")
                    laugh = self.take_command().lower().strip()
                    if laugh:
                        self.speak(f"{random.choice(lf)}")
                        break
                break

    def play_pause_action(self, query):
        ply = query.replace("play", "")
        if ply == "" or ply == "it" or ply == " it" or "pause" in query:
            pg.press("space")
        elif "random song" in ply:
            self.play_random_song()
        else:
            self.speak(f"Sir, do you want to play {ply}?")
            while True:
                print(">>> Listening for confirmation...")
                confirmation = self.take_command().lower()
                if any((x in confirmation for x in ["yes", "ha", "sure", "play it"])):
                    webbrowser.open(
                        f"https://www.youtube.com/results?search_query={ply}"
                    )
                    break
                elif any((x in confirmation for x in ["no", "don't", "do not", "na"])):
                    self.speak("Okay, sir.")
                    break

    def play_random_song(self, query):
        match = re.search(r"play (.+?) (song|music)", query)
        song = ""
        if match:
            song = match.group(1)
        songs = self.load_songs()
        if "random" in query:
            if songs:
                song = random.choice(list(songs.values()))
                print(f"Playing a random song: {song}")
                self.play_song(song)
            else:
                print("The song library is empty. Add some songs first.")
        else:
            if song == "":
                song = random.choice(list(songs.values()))
                print(f"Playing a random song: {song}")
                self.play_song(song)
                return
            self.speak(f"Sir, do you want to play {song}?")
            while True:
                print(">>> Listening for confirmation...")
                confirmation = self.take_command().lower()
                if any((x in confirmation for x in ["yes", "ha", "sure", "play it"])):
                    self.play_song(song)
                    new_index = max(songs.keys(), default=1) + 1
                    songs[new_index] = song + " original"
                    self.save_songs(songs)
                    print(f"'{song}' has been added to the library.")
                    break
                elif any((x in confirmation for x in ["no", "don't", "do not", "na"])):
                    self.speak("Okay, sir.")
                    break
                else:
                    self.speak("I didn't understand that. Please confirm again.")

    def play_song(self, song):
        search = Search(song)
        video_url = search.results[0].watch_url
        print(f"Playing: {video_url}")
        webbrowser.open(video_url)
        sleep(3)
        self.minimize_window()

    def press(self, key, times):
        try:
            for _ in range(times):
                pg.press(key)
                sleep(1)
            self.speak(f"Pressed the {key} key {times} times.")
        except Exception as e:
            self.speak("An error occurred while pressing the key.")

    def press_key(self, query):
        prs = query.replace("press ", "").strip()
        pg.press(prs)

    def rP(self):
        rply = [
            "I'm on it, sir",
            "Affirmative, moving on!",
            "Okie-dokie!, let’s rock!",
            "On it, sir",
            "Roger that, sir!",
            "Sure thing, sir!",
            "You got it!",
            "as you speak, sir",
            "you got it, sir!",
        ]
        return random.choice(rply)

    def restarT(self):
        res = ["Restarting the pc."]
        resi = random.choice(res)
        pg.keyDown("win")
        sleep(1)
        pg.press("d")
        sleep(1)
        pg.keyUp("win")
        sleep(2)
        pg.leftClick()
        sleep(1)
        pg.keyDown("alt")
        sleep(1)
        pg.press("f4")
        sleep(1)
        pg.keyUp("alt")
        sleep(1)
        pg.press("right")
        self.speak(resi)
        sleep(2)
        pg.press("enter")

    def restart_explorer(self):
        self.close_perticular_app("explorer.exe")

    def restart_phoenix(self):
        self.close_perticular_app("pyw.exe")
        self.desKtoP(4)
        path = os.path.join(
            os.path.dirname(__file__), "..", "batch", "on_boot_startup.bat"
        )
        os.startfile(path)
        sleep(5)
        sys.exit()

    @staticmethod
    def rockMsc(volume):
        """Plays a random rock music track for a fixed duration."""
        intr = ["rock1.mp3", "rock2.mp3", "rock3.mp3"]
        x = random.choice(intr)
        file_path = f"E:\\MSC\\{x}"
        duration = 25
        pygame.mixer.init()
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(volume)
            print(f"Volume set to {volume * 100}%")
            pygame.mixer.music.play()
            print(f"Playing {file_path} for {duration} seconds...")
            time.sleep(duration)
            pygame.mixer.music.stop()
            print("Music stopped.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def save_songs(self, songs):
        with open(self.SONGS_FILE, "w") as file:
            for index, song in sorted(songs.items()):
                file.write(f"{index} | {song} \n")

    def screenshot(self):
        try:
            pg.keyDown("win")
            pg.press("prntscrn")
            pg.keyUp("win")
            self.speak("Screenshot captured, sir.")
        except Exception as e:
            self.speak("An error occurred while taking the screenshot.")

    def flipkart(self):
        self.speak("Sir, what product do you want to search?")
        while True:
            print(">>>Listening for Flipkart product")
            prod = self.take_command().lower()
            if prod:
                # URL-encode the product name
                encoded_prod = prod.replace(" ", "+")
                webbrowser.open(
                    f"https://www.flipkart.com/search?q={encoded_prod}&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off"
                )
                break
            else:
                print("I didn't catch that. Please say the product name again.")
                continue

    def amazon(self):
        self.speak("Sir, what product you want to search?")
        while True:
            print(">>>Listening for amazon product")
            prod = self.take_command().lower()
            if prod:
                encoded_prod = prod.replace(" ", "+")
                webbrowser.open(
                    f"https://www.amazon.in/s?k={encoded_prod}&crid=3V10F5M3G9MRZ&ref=nb_sb_noss_2"
                )
                break
            else:
                continue

    def myntra(self):
        self.speak("Sir, what product you want to search?")
        while True:
            print(">>>Listening for myntra product")
            prod = self.take_command().lower()
            if prod:
                encoded_prod = prod.replace(" ", "+")
                webbrowser.open(f"https://www.amazon.in/{encoded_prod}")
                break
            else:
                continue

    def search_browser(self):
        self.speak("Sir, what do I search on the browser?")
        cm = self.take_command().lower()
        if "amazon" in cm:
            self.speak("Sir, what product you want to search?")
            while True:
                print(">>>Listening for amazon product")
                prod = self.take_command().lower()
                if prod:
                    encoded_prod = prod.replace(" ", "+")
                    webbrowser.open(
                        f"https://www.amazon.in/s?k={encoded_prod}&crid=3V10F5M3G9MRZ&ref=nb_sb_noss_2"
                    )
                    break
                else:
                    continue
        if "flipkart" in cm:
            self.speak("Sir, what product you want to search?")
            while True:
                print(">>>Listening for flipkart product")
                prod = self.take_command().lower()
                if prod:
                    encoded_prod = prod.replace(" ", "+")
                    webbrowser.open(
                        f"https://www.flipkart.com/search?q={encoded_prod}&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off"
                    )
                    break
                else:
                    continue
        else:
            webbrowser.open(cm)

    def search_instagram(self):
        self.speak("Sir, please enter the username correctly.")
        name = input("Enter username: ")
        webbrowser.open(f"https://www.instagram.com/{name}")

    def search_youtube(self):
        try:
            self.speak("What do I search, sir?")
            sng = self.take_command().lower()
            self.speak(f"Starting {sng}")
            self.play_song(sng)
        except Exception as e:
            print("Internet error occurred.")

    # def select_action(self, query, response_function):
    #     selected_text = query.replace("select ", "")
    #     self.speak(response_function())
    #     keyboard.write(f"{selected_text[:2]}")
    #     self.speak("Do you want to open it?")
    #     while True:
    #         confirmation = self.take_command().lower()
    #         if any((x in confirmation for x in ["yes", "ha", "sure", "play it"])):
    #             webbrowser.open(
    #                 f"https://www.youtube.com/results?search_query={selected_text}"
    #             )
    #             break
    #         elif any((x in confirmation for x in ["no", "don't", "do not", "na"])):
    #             self.speak(response_function())
    #             break

    def set_alarm(self):
        """
        Sets up an alarm at the specified time.
        """
        self.speak("Please enter the alarm time.")
        print(time.localtime())
        alarm_time = input("Enter the alarm time in HH:MM format: ")
        try:
            alarm_hour, alarm_minute = map(int, alarm_time.split(":"))
            self.speak(f"Alarm set for {alarm_hour}:{alarm_minute}.")
        except ValueError:
            self.speak("Invalid time format. Please enter time as HH:MM.")
            return
        self.speak("The alarm is now active.")
        while True:
            current_time = time.localtime()
            current_hour = current_time.tm_hour
            current_minute = current_time.tm_min
            if current_hour == alarm_hour and current_minute == alarm_minute:
                self.speak("Alarm ringing! Wake up, boss!")
                print("Alarm! Wake up!")
                break
            time.sleep(10)

    def set_focus(self):
        for _ in range(2):
            pg.leftClick(500, 500)
            sleep(3)

    def set_reminder(self):
        """Set a reminder based on user input."""
        self.speak("What reminder should I set, sir?")
        reminder_message = self.take_command().lower()
        self.speak("At what time should I set the reminder? (Provide in HH:MM format)")
        reminder_time = self.take_command().lower()
        hour, minute = self._parse_time(reminder_time)
        if hour is None or minute is None:
            self.speak("Invalid time format. Please try again using HH:MM format.")
            return
        self.speak("On which day, sir?")
        date_str = self.take_command().lower()
        month, day = self._parse_date(date_str)
        if month is None or day is None:
            self.speak("Invalid date format. Please try again.")
            return
        now = datetime.now()
        reminder_datetime = datetime(now.year, month, day, hour, minute)
        time_until_reminder = reminder_datetime - now
        if time_until_reminder.total_seconds() <= 0:
            self.speak("Invalid time. The reminder should be in the future.")
            return
        self.speak(f"Reminder set for {reminder_datetime.strftime('%Y-%m-%d %H:%M')}.")
        time_until_reminder_seconds = time_until_reminder.total_seconds()
        time.sleep(time_until_reminder_seconds)
        notification.notify(
            title="Reminder",
            message=reminder_message,
            app_name="Phoenix",
            timeout=10,
        )
        self.speak("Reminder notification delivered, sir!")
        import tkinter as tk

    def set_timer(self):
        """
        Sets a timer based on user input.
        Notifies the user when the timer ends.
        """
        try:
            self.speak("For how long should I set the timer?")
            print("e.g :: 1 hour, 5 minutes, or 1 hour and 30 minutes)")
            time_input = self.take_command().lower()
            hours, minutes, seconds = self._parse_time_duration(time_input)
            if hours is None and minutes is None and (seconds is None):
                self.speak(
                    "Sorry, I couldn't understand the duration. Please try again."
                )
                return
            total_seconds = hours * 3600 + minutes * 60 + seconds
            self.speak(
                f"Setting a timer for {hours} hour(s), {minutes} minute(s), and {seconds} second(s)."
            )
            print(
                f"Timer set for {hours} hour(s), {minutes} minute(s), and {seconds} second(s)."
            )
            timer_thread = threading.Thread(
                target=self._countdown_timer, args=(total_seconds,), daemon=True
            )
            timer_thread.start()
        except Exception as e:
            self.speak(f"An error occurred while setting the timer: {str(e)}")

    @staticmethod
    def shoWalLwiN():
        """Simulates opening Windows Start Menu and performing actions."""
        pg.keyDown("win")
        sleep(1)
        pg.press("tab")
        sleep(1)
        pg.keyUp("win")
        sleep(1)
        pg.rightClick(900, 400)
        sleep(1)
        pg.press("down", presses=3)
        pg.press("enter", presses=2)

    def shutD(self):
        self.lastChargeCheck()
        sht1 = [
            "In less than one minute, the PC will shut down.",
            "PC shutdown will occur in less than a minute.",
            "Shutdown in progress: PC will turn off in under a minute.",
            "The PC will be powered down in less than a minute.",
            "The PC will be shutting down shortly, in less than a minute.",
            "The PC will shut down in less than a minute.",
            "The computer will be shutting down in under a minute.",
            "The computer will turn off in less than a minute.",
            "The system will power off in less than a minute.",
            "Your PC is about to shut down in less than 60 seconds.",
        ]
        sht2 = [
            "Alrighty, I'm out! See you later, sir!",
            "I'm off now. See ya soon, sir!",
            "Peace out! I'm logging off.",
            "Adios Señor! Until we meet again!",
            "Shutting down now. Take care, sir!",
            "Take care! See you next time, sir!",
            "Time for me to power down. See ya, sir!",
        ]
        shti1 = random.choice(sht1)
        shti2 = random.choice(sht2)
        self.speak(shti1)
        os.system("shutdown /s")
        try:
            os.system("taskkill /F /IM Arc.exe")
        except Exception:
            print("Brave already closed.")
        sleep(2)
        try:
            os.system("taskkill /F /IM code.exe")
        except Exception:
            print("Code already closed.")
        sleep(2)
        try:
            os.system("taskkill /F /IM pyw.exe")
        except Exception:
            print("BG Python already closed.")
        sleep(18)
        self.speak(shti2)
        sys.exit()

    def sleeP(self):
        slp = ["PC is going to sleep."]
        slpi = random.choice(slp)
        self.speak(self.rP())
        pg.keyDown("win")
        sleep(1)
        pg.press("d")
        sleep(1)
        pg.keyUp("win")
        sleep(2)
        pg.leftClick()
        sleep(1)
        pg.keyDown("alt")
        sleep(1)
        pg.press("f4")
        sleep(1)
        pg.keyUp("alt")
        sleep(1)
        pg.press("left")
        pg.press("left")
        self.speak(slpi)
        sleep(2)
        pg.press("enter")
        self.speak(self.onL())

    def sleep_phnx(self):
        while True:
            cmnd2 = self.take_command().lower()
            if cmnd2 in [
                "hello phoenix",
                "wake up phoenix",
                "are you there phoenix",
                "am i audible to you phoenix",
                "am i audible phoenix",
            ]:
                self.speak(self.wakE())
                break
            else:
                continue

    def play_game(self):
        print("System has these games:")
        print("\n1.SpaceJunkies")
        print("2.Valorant")
        self.speak("say which game you want to play..")
        print("speak game name or index:")
        while True:
            gm = self.take_command().lower().strip()
            if "one" in gm or "1" in gm or "space" in gm or "junkies" in gm:
                path = r"C:\PROJECT_VB\Game1\Game1\bin\Debug\Game1.exe"
                os.startfile(path)
                break
            elif "two" in gm or "2" in gm or "valo" in gm or "valorant" in gm:
                pg.press("win")
                sleep(1)
                keyboard.write("valorant")
                sleep(1)
                keyboard.press("enter")
                break
            else:
                continue

    def snG(self):
        """Searches and plays a random song directly on YouTube."""
        song_list = [
            "Lord Imran Khan's playlist",
            "Agar Tum Sath Ho",
            "Best of AP Dhillon",
            "Bhula diya by Darshan Raval",
            "Chale Jana Phir",
            "Channa ve",
            "Dekhte Dekhte by Atif Aslam",
            "Dillagi by Rahat fateh ali khan",
            "Falak Tak reverb",
            "Hale Dil Tujhko Sunata",
            "Hale Dil",
            "Khairiyat",
            "Kya Mujhe Pyaar Hai",
            "Labon Ko",
            "Lo safar",
            "Mareez E Ishq",
            "Mat Aazma Re",
            "Pee loon song",
            "Pehla Nasha by Udit Narayan",
            "Pehli Nazar Mein",
            "Raataaan Lambiyan",
            "Tera Pyar",
            "Tera ban jaunga",
            "Tere Liye",
            "Tere Nainon Mein",
            "Tere Vaaste",
            "Teri Ore",
            "Thodi der from Half girlfriend",
            "Toota jo kabhi Tara",
            "Tu Hai ki Nahi",
            "Tu Jaane na",
            "Tujhe Bhula diya",
            "Tujhe kitna Chahne lage by Jubin",
            "Tum hi Aana",
            "Tum se hi",
            "Tune jo Na Kaha",
            "Vaaste",
            "Wajah Tum Ho",
            "Ye Tune Kya Kiya",
            "Zara Sa",
            "Zara Zara by Jalraj",
            "Zindagi Se",
        ]
        song_name = random.choice(song_list)
        print(f"Playing a random song: {song_name}")
        self.play_song(song_name)

    def speak(self, message):
        self.speech_engine.speak(message)

    def start_thread(self, function_name, *args, **kwargs):
        """
        Creates and starts a thread for the given function.
        Args:
            function_name (function): The function to run in a separate thread.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
        """
        thread = threading.Thread(target=function_name, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()

    def suggest_song(self):
        songs = self.load_songs()
        if songs:
            song = random.choice(list(songs.values()))
            print(f"How about listening to: {song}?")
            self.play_song(song)
        else:
            print("The song library is empty. Add some songs first.")

    def switch_tab(self):
        pg.keyDown("ctrl")
        pg.press("tab")
        pg.keyUp("ctrl")

    @staticmethod
    def tM():
        """Returns a random time-related phrase."""
        return random.choice(["It's", "The time is", "Time is"])

    def take_command(self):
        return self.voice_recognition.take_command()

    def tim(self):
        tt = datetime.now().strftime("%I:%M %p")
        self.speak(f"The time is {tt}.")

    def toggle_fullscreen(self):
        pg.press("f11")
        self.speak("Done, sir!")

    def type_text(self, query):
        text = query.replace("type ", "")
        keyboard.write(text)

    def unmute_speaker(self):
        """Unmute the system volume."""
        os.system("nircmd.exe mutesysvolume 0")
        self.speak("System volume has been unmuted.")

    def view_songs(self):
        songs = self.load_songs()
        if not songs:
            print("No songs available.")
        else:
            print("\nCurrent song library:")
            for index, song in sorted(songs.items()):
                print(f"{index}: {song}")

    @staticmethod
    def wakE():
        """Returns a random greeting when the user wakes up."""
        return random.choice(
            [
                "Hello, sir! I am listening.",
                "Hello! I am here for you.",
                "Hey love! Phoenix is here.",
                "Hello, sir! Phoenix is always here for you.",
                "Hello, sir! How can I help you?",
            ]
        )

    @staticmethod
    def whTabT():
        abt_list = [
            "How about",
            "What about",
            "You shall listen",
            "what about this one:",
        ]
        return random.choice(abt_list)

    @staticmethod
    def wtR():
        """Returns a random reminder to drink water."""
        return random.choice(
            [
                "Be hydrated, sir.",
                "Drink some water, sir, be hydrated.",
                "Do drink water, be hydrated.",
            ]
        )


if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    recog = VoiceRecognition(gui)
    speach = SpeechEngine()
    utils = Utility(spk=speach, reco=recog)
    # utils.desKtoP(1)
    utils.play_game()
