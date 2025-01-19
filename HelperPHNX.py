import os
import sys
import time
import threading
import subprocess
from time import sleep
import re
import json
from datetime import datetime, timedelta
import random
import pyttsx3
import speech_recognition as sr
import pyautogui as pg
import keyboard
import webbrowser
from plyer import notification
from pytube import Search
import psutil
from difflib import SequenceMatcher
import pyaudio
import wave
import uuid
from tabulate import tabulate
from collections import defaultdict
import tkinter as tk
from PIL import Image, ImageTk
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QColor
import psutil
import time
from time import sleep
import psutil
import win32gui
import win32process
import win32con
import win32api
import ctypes
from pyvda import AppView, get_apps_by_z_order, VirtualDesktop, get_virtual_desktops

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
temp_stdout = sys.stdout
sys.stdout = open(os.devnull, "w")
import pygame

sys.stdout.close()
sys.stdout = temp_stdout


class SpeechEngine:

    def __init__(self):
        self.engine = pyttsx3.init("sapi5")
        voices = self.engine.getProperty("voices")
        self.engine.setProperty("voice", voices[1].id)
        self.engine.setProperty("rate", 174)
        # self.lock = threading.Lock()
        self.honorifics = True

    def _manage_honorifics(self):
        self.honorifics = False
        sleep(30)
        self.honorifics = True

    def speak(self, audio):
        """
        Thread-safe method to handle text-to-speech.
        """
        # with self.lock:
        replacements = [
            "boss",
            "captain",
            "commander",
            "my lord",
            "your highness",
            "your majesty",
            "my liege",
            "your grace",
        ]

        for punctuation in ["", "?", "!", ".", " "]:
            if f"sir{punctuation}" in audio:
                if self.honorifics:
                    replacement = random.choice(replacements)
                    audio = audio.replace(
                        f"sir{punctuation}", f"{replacement}{punctuation}"
                    )
                    threading.Thread(target=self._manage_honorifics).start()
                    break
                else:
                    audio = audio.replace(f"sir{punctuation}", "")
        self.engine.say(audio)
        print(f"$ : {audio}")
        self.engine.runAndWait()
        return

    def threadedSpeak(self, audio):
        """
        Starts a thread to call the `speak` method.
        """
        threading.Thread(target=self.speak, args=(audio,)).start()


class VoiceAssistantGUI:

    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.9)
        self.root.attributes("-topmost", True)
        self.setup_transparency()
        self.mic_label = tk.Label(self.root, bg="white")
        self.mic_label.pack()
        current_dir = os.path.dirname(__file__)
        self.listen_img_path = os.path.join(current_dir, "assets", "img", "green.png")
        self.recognize_img_path = os.path.join(current_dir, "assets", "img", "red.png")
        if not os.path.exists(self.listen_img_path):
            print("Error: Listen image not found!")
        if not os.path.exists(self.recognize_img_path):
            print("Error: Recognize image not found!")
        self.listen_img = Image.open(self.listen_img_path)
        self.recognize_img = Image.open(self.recognize_img_path)
        max_width = max(4, 4)
        max_height = max(30, 30)
        x_offset = self.root.winfo_screenwidth() - max_width
        y_offset = self.root.winfo_screenheight() - max_height
        self.root.geometry(f"{max_width}x{max_height}+{x_offset}+{y_offset}")

    def hide_listen_image(self):
        self.mic_label.config(image=None)

    def hide_recognize_image(self):
        self.mic_label.config(image=None)

    def setup_transparency(self):
        if self.root.tk.call("tk", "windowingsystem") == "win32":
            self.root.attributes("-topmost", 1)
        elif self.root.tk.call("tk", "windowingsystem") == "x11":
            self.root.attributes("-type", "dock")
        elif self.root.tk.call("tk", "windowingsystem") == "aqua":
            self.root.call(
                "::tk::unsupported::MacWindowStyle",
                "style",
                self.root._w,
                "help",
                "none",
            )
        self.root.wm_attributes("-transparentcolor", "white")

    def show_listen_image(self):
        self.mic_label.config(image=None)
        mic_img = Image.open(self.listen_img_path).convert("RGBA")
        mic_img = mic_img.resize((40, 40), Image.LANCZOS)
        mic_img = ImageTk.PhotoImage(mic_img)  # Convert to Tkinter-compatible image
        self.mic_label.config(image=mic_img)
        self.mic_label.image = mic_img  # Keep a reference to the image object
        self.root.update()

    def show_recognize_image(self):
        self.mic_label.config(image=None)
        recognize_img = self.recognize_img.resize((40, 40), Image.LANCZOS).convert(
            "RGBA"
        )
        recognize_img = ImageTk.PhotoImage(recognize_img)
        self.mic_label.config(image=recognize_img)
        self.mic_label.image = recognize_img  # Keep a reference to the image object
        self.root.update()


class VoiceRecognition:

    def __init__(self, gui):
        self.recognizer = sr.Recognizer()
        self.gui = gui

    def take_command(self):
        with sr.Microphone() as source:
            self.gui.show_listen_image()
            print(">>>", end="\r")
            audio = self.recognizer.listen(source, 0, 5)
        try:
            self.recognizer.pause_threshold = 1
            self.gui.show_recognize_image()
            print("<<<", end="\r")
            query = self.recognizer.recognize_google(audio, language="en-in")
            print(f"# : {query}\n")
        except Exception as e:
            print("<!>", end="\r")
            self.gui.hide_listen_image()
            return ""
        return query


"---------------UTILITIES---------------"


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

        json_file = os.path.join(os.path.dirname(__file__), "data", "intents.json")
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

    def process_query(self, query):
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
                print("here")
                # Search for the function corresponding to the entity
                for func, tags in self.action_map.items():
                    if entity in tags:
                        # Print a random response from the "responses" list
                        random_response = random.choice(self.open_intent["responses"])
                        self.utils.speak(f"{random_response} {entity.capitalize()}.")

                        # Call the function
                        func()
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
        json_file = os.path.join(os.path.dirname(__file__), "data", "intents.json")
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

    def process_query(self, query):
        for entity in self.open_intent["entities"]:
            if entity in query.lower():
                print("here")
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
    SONGS_FILE = os.path.join(current_dir, "data", "songs.txt")
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

    def __init__(self, spk, reco, sleep_time=1):
        self.sleep_time = sleep_time

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

    def _show_timer_notification(self):
        """
        Displays the timer notification using a rounded message box.
        """
        app = QApplication.instance() or QApplication([])
        message_box = RoundedMessageBox("Timer", "Time's up, sir!")
        message_box.exec_()

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
        desk = current_desktop.number - 1  # for the utility open desktop
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
        positions = {0: (466, 945), 1: (709, 945), 2: (958, 945), 3: (1201, 945)}
        if screen_index not in positions:
            print(f"Invalid screen index: {screen_index}")
            return
        sleep(self.sleep_time)
        self._perform_key_press(["win", "tab"], "down")
        self._perform_key_press(["win"], "up")
        self._click_at_position(*positions[screen_index])

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
        sleep(40)
        self.restart_explorer()
        self.speak(self.onL())

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
        """Plays a random system intro sound."""
        intr = ["robo1.wav", "robo2.wav"]
        x = random.choice(intr)
        sound_path = os.path.join(os.path.dirname(__file__), "assets", "sound", x)
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
                self.speak("Sir, the device is fully charged!")
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
        if "study" in dt or "zero" in dt or "0" in dt:
            self.desKtoP(0)
        elif "alpha" in dt or "1" in dt or "one" in dt or ("first" in dt):
            self.desKtoP(0)
        elif "extra" in dt or "2" in dt or "two" in dt or ("second" in dt):
            self.desKtoP(2)
        elif "trash" in dt or "3" in dt or "three" in dt or ("third" in dt):
            self.desKtoP(3)
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
                "I'm glad to see you again, sir. Let's get started!",
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
        self.desKtoP(2)
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
        self.desKtoP(2)
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
        self._open_with_win("win", "1", 0)

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
        self.desKtoP(0)

    def open_alpha_desk(self):
        self.desKtoP(1)

    def open_extra_desk(self):
        self.desKtoP(2)

    def open_trash_desk(self):
        self.desKtoP(3)

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
        self.desKtoP(3)
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

    def play_pause_action(self, query):
        ply = query.replace("play", "")
        if ply == "":
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
            self.speak(f"Sir, do you want to play {song}?")
            while True:
                print(">>> Listening for confirmation...")
                confirmation = self.take_command().lower()
                if any((x in confirmation for x in ["yes", "ha", "sure", "play it"])):
                    self.play_song(song)
                    new_index = max(songs.keys(), default=0) + 1
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
        self.desKtoP(3)
        path = os.path.join(os.path.dirname(__file__), "batch", "main.bat")
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

    def search_browser(self):
        self.speak("Sir, what do I search on the browser?")
        cm = self.take_command().lower()
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

    def select_action(self, query, response_function):
        selected_text = query.replace("select ", "")
        self.speak(response_function())
        keyboard.write(f"{selected_text[:2]}")
        self.speak("Do you want to open it?")
        while True:
            confirmation = self.take_command().lower()
            if any((x in confirmation for x in ["yes", "ha", "sure", "play it"])):
                webbrowser.open(
                    f"https://www.youtube.com/results?search_query={selected_text}"
                )
                break
            elif any((x in confirmation for x in ["no", "don't", "do not", "na"])):
                self.speak(response_function())
                break

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
            if cmnd2 in ["hello phoenix", "wake up phoenix"]:
                self.speak(self.wakE())
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


"---------------MSGBOX-PYQT5---------------"


class RoundedMessageBox(QDialog):

    def __init__(self, title, message):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 150)
        self.init_ui(title, message)

    def init_ui(self, title, message):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        title_label = QLabel(title, self)
        title_label.setStyleSheet("color: #f1c40f; font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        message_label = QLabel(message, self)
        message_label.setStyleSheet("color: #ecf0f1; font-size: 14px;")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(message_label)
        ok_button = QPushButton("OK", self)
        ok_button.setStyleSheet(
            "\n            QPushButton {\n                background-color: #16a085;\n                color: white;\n                font-size: 12px;\n                border-radius: 5px;\n                padding: 5px 15px;\n            }\n            QPushButton:hover {\n                background-color: #1abc9c;\n            }\n            "
        )
        ok_button.clicked.connect(self.accept)
        ok_button.setFixedWidth(80)
        ok_button.setFixedHeight(30)
        ok_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(ok_button, alignment=Qt.AlignCenter)

    def paintEvent(self, event):
        """Draw rounded corners and background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush(QColor("#2c3e50"))
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 15, 15)


"---------------TIMER-EX.-WITH MSGBOX---------------"


class TimeBasedFunctionality:

    def __init__(self):
        self.timer_file = os.path.join(os.path.dirname(__file__), "data", "timer.json")
        self._initialize_timer_file()

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
                    self._mark_timer_as_ringed(timer_id)
                    break
                sleep(1)

        timer_thread = threading.Thread(target=timer_thread_logic, args=(timer,))
        timer_thread.start()

    def _extract_time(self, query):
        """Extract hours, minutes, and seconds from the query string."""
        hours, minutes, seconds = (0, 0, 0)
        patterns = {
            "hours": "(\\d+)\\s*hour",
            "minutes": "(\\d+)\\s*minute",
            "seconds": "(\\d+)\\s*second",
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
            print(f"Starting threads for {len(data['timers'])} timers...")
            for timer in data["timers"]:
                self._assign_thread_to_timer(timer)

    def remove_timer(self):
        """
        Remove timers from timer.json where ringed=true.
        """
        with open(self.timer_file, "r+") as f:
            data = json.load(f)
            timers_before = len(data["timers"])
            data["timers"] = [
                timer for timer in data["timers"] if not timer.get("ringed", False)
            ]
            timers_after = len(data["timers"])
            removed_timers = timers_before - timers_after
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=4)
        print(f"Removed {removed_timers} timers where ringed=true.")

    def setTimer(self, query):
        """
        Set a timer based on the input query string and save it to timer.json.
        """
        hours, minutes, seconds = self._extract_time(query)
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
        timer_details = {
            "id": timer_id,
            "ringTime": ring_time_tuple,
            "ringed": False,
            "setTime": set_time,
        }
        with open(self.timer_file, "r+") as f:
            data = json.load(f)
            data["timers"].append(timer_details)
            f.seek(0)
            json.dump(data, f, indent=4)
        print(f"Timer set successfully! Timer-ID:{timer_id}.")


"---------------(set)TIME-BASED-FUNCTIONALITIES----------------"


class TimerHandle:

    def __init__(self, utility):
        self.timer_file = os.path.join(
            os.path.dirname(__file__), "data", "TimeData.json"
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
            "hours": "(\\d+)\\s*hour",
            "minutes": "(\\d+)\\s*minute",
            "seconds": "(\\d+)\\s*second",
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
            os.path.dirname(__file__), "data", "TimeData.json"
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
            "day": days,
            "delete": False,
            "id": unique_id,
            "label": lbl,
            "repeat": repeat,
            "ringAlarm": [hour, minute],
            "ringed": 0,
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
            os.path.dirname(__file__), "data", "TimeData.json"
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
            os.path.dirname(__file__), "data", "schedule.json"
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


"---------------(start/run)TIME-BASED-FUNCTIONALITIES----------------"


class HandleTimeBasedFunctions:

    def __init__(
        self, timer_manager, alarm_manager, schedule_manager, reminder_manager, utility
    ):
        self.time_data_file = os.path.join(
            os.path.dirname(__file__), "data", "TimeData.json"
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

    def check_alarms(self):
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        updated_alarms = []
        for alarm in self.data["alarms"]:
            alarm_time = f"{alarm['ringAlarm'][0]:02}:{alarm['ringAlarm'][1]:02}"
            if alarm_time == current_time:
                self.utils.speak(f"Ringing Alarm: {alarm['label']}")
                if alarm["repeat"] == "once":
                    continue
            self.today_alarms[alarm["label"]] = alarm_time
            updated_alarms.append(alarm)
        self.data["alarms"] = updated_alarms

    def check_reminders(self):
        now = datetime.now()
        today_date = now.strftime("%d-%m-%y")
        updated_reminders = []
        for reminder in self.data["reminders"]:
            if reminder["date"] == today_date:
                reminder_time = datetime.strptime(reminder["time"], "%H:%M").time()
                if now.time() >= reminder_time:
                    self.utils.speak(f"Reminder: {reminder['message'][0]}")
                else:
                    self.speech_engine.utils.speak(
                        f"You have missed reminder: {', '.join(reminder['message'])}"
                    )
            elif reminder["date"] > today_date:
                updated_reminders.append(reminder)
        self.data["reminders"] = updated_reminders

    def check_schedule(self):
        now = datetime.now().time()
        for event in self.data["schedule"]:
            event_time = datetime.strptime(event["time"], "%H:%M").time()
            if now < event_time:
                self.today_schedule_events[event["message"]] = event["time"]

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

    def speak(self, message):
        self.speech_engine.speak(message)


class ReminderManager:

    def __init__(self, util):
        self.reminder_file = os.path.join(
            os.path.dirname(__file__), "data", "TimeData.json"
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


import os
import json
from datetime import datetime, time


class TimerManager:
    def __init__(self, spk):
        self.timer_file = os.path.join(
            os.path.dirname(__file__), "data", "TimeData.json"
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

    def speak(self, query):
        self.se.speak(query)


class ScheduleManager:

    def __init__(self, spk):
        self.schedule_file = os.path.join(
            os.path.dirname(__file__), "data", "TimeData.json"
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
                        self.speak("Time to ", schedule["message"])
                        threading.Thread(target=self._do_halt).start()
                except Exception as e:
                    print(f"Error processing schedule entry '{schedule}': {e}")
        except KeyboardInterrupt:
            print("Schedule monitoring stopped by user.")
        except Exception as e:
            print(f"An error occurred while checking the schedule: {e}")

    def speak(self, query):
        self.se.speak(query)


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
            os.path.dirname(__file__), "data", "TimeData.json"
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

            for alarm in alarms:
                try:
                    # Extract alarm details
                    alarm_time = alarm.get("ringAlarm", [])
                    if len(alarm_time) != 2:
                        continue  # Skip invalid alarm times
                    alarm_hour, alarm_minute = alarm_time  #
                    alarm_day = alarm.get("day", [])
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
                            threading.Thread(target=self.ring_thread).start()

                            # Update alarm status
                            alarm["ringed"] = ringed + 1
                            data_changed = True

                            # Mark non-repeating alarms for deletion
                            if repeat == "once":
                                alarm["delete"] = True

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

    def speak(self, query):
        self.se.speak(query)


"---------------EXTRA----------------"


def music(Utility):
    Utility.intrOmsC()
    Utility.rockMsc(0.5)


def compareSent(main_query, list_of_strings):
    """
    Compares a main string with a list of strings and returns True if the similarity
    probability is greater than or equal to 90% for any string in the list.

    Args:
        main_query (str): The main string to compare.
        list_of_strings (list): A list of strings to compare with the main string.

    Returns:
        bool: True if any string in the list matches the main string with >=90% similarity, else False.
    """
    if not main_query or not list_of_strings:
        raise ValueError("Both main_query and list_of_strings must be non-empty.")

    def calculate_similarity(str1, str2):
        """
        Calculate the similarity ratio between two strings.
        """
        return SequenceMatcher(None, str1, str2).ratio()

    match_found = False
    for string in list_of_strings:
        probability = calculate_similarity(main_query, string) * 100
        print(
            f"Comparing '{main_query}' with '{string}': {probability:.2f}% similarity"
        )
        if probability >= 65:
            match_found = True
    return match_found


if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    recog = VoiceRecognition(gui)
    spk = SpeechEngine()
    utils = Utility(spk, recog)
    # utils = Utility(spk, recog)
    # utils.open_setting()
    utils.get_window("Code.exe", "HelperPHNX.py")
    # opn = OpenAppHandler(recog)
    # utils.speak("hello, sir")
    # utils.desKtoP(2)
    # utils.open_brave()
