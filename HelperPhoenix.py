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
from pytube import YouTube, Search
import psutil
from difflib import SequenceMatcher
import pyaudio
import wave
import tkinter as tk
from tkinter import Toplevel
import tkinter.messagebox
from PIL import Image, ImageTk
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QBrush, QColor, QFont

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
        self.lock = threading.Lock()

    def speak(self, audio):
        """
        Thread-safe method to handle text-to-speech.
        """
        with self.lock:
            replacements = ["boss", "my lord", "commander", "captain"]
            for punctuation in ["", "?", "!", ".", " "]:
                if f"sir{punctuation}" in audio:
                    replacement = random.choice(replacements)
                    audio = audio.replace(
                        f"sir{punctuation}", f"{replacement}{punctuation}"
                    )
                    break
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
        mic_img = Image.open(self.listen_img_path).convert("RGBA")
        mic_img = mic_img.resize((40, 40), Image.LANCZOS)
        mic_img = ImageTk.PhotoImage(mic_img)
        self.mic_label.config(image=mic_img)
        self.mic_label.image = mic_img
        self.root.update()

    def show_recognize_image(self):
        self.mic_label.config(image=None)
        recognize_img = ImageTk.PhotoImage(
            self.recognize_img.resize((40, 40), Image.LANCZOS).convert("RGBA")
        )
        self.mic_label.config(image=recognize_img)
        self.mic_label.image = recognize_img
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

    def __init__(self, speech_engine, voice_recognition, sleep_time=1):
        self.speech_engine = speech_engine
        self.voice_recognition = voice_recognition
        self.sleep_time = sleep_time

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
            "which desktop would you like me to open sir?",
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
                self.speak("Battery is quite good, Sir.")
            elif battery_percentage >= 60 and battery_percentage < 80:
                self.speak("Battery is ok, Sir.")
            elif battery_percentage <= 35:
                self.speak("Plug in the charger sir!")

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

    def close_all_py(self):
        try:
            subprocess.run(["taskkill", "/F", "/IM", "pyw.exe"], check=True)
            self.speak("Goodbye sir, see you soon.")
            subprocess.run(["taskkill", "/F", "/IM", "python.exe"], check=True)
        except subprocess.CalledProcessError:
            print("No Python program found.")

    def close_app(self, query, response):
        reply = response
        Nameofap = query.replace("close ", "")
        if (
            "the window" in Nameofap
            or "this window" in Nameofap
            or "window" in Nameofap
            or ("it" in Nameofap)
            or ("this" in Nameofap)
        ):
            self.speak(f"{reply} {Nameofap}")
            pg.keyDown("alt")
            pg.press("F4")
            pg.keyUp("alt")
        elif "tab" in Nameofap:
            self.close_tab()
        elif (
            "the desktop" in Nameofap
            or "this desktop" in Nameofap
            or "this desk" in Nameofap
            or ("desktop" in Nameofap)
            or ("desk" in Nameofap)
        ):
            sleep(1)
            pg.keyDown("win")
            pg.keyDown("ctrl")
            pg.press("f4")
            pg.keyUp("ctrl")
            pg.keyUp("win")
            sleep(1)
        elif (
            "brave" in Nameofap
            or "brave browser" in Nameofap
            or "all brave" in Nameofap
        ):
            try:
                subprocess.run(["taskkill", "/F", "/IM", "brave.exe"], check=True)
                self.speak(f"All Brave tabs are successfully closed.")
            except subprocess.CalledProcessError:
                self.speak(f"Failed to close Brave.")
        elif "arc" in Nameofap or "arc browser" in Nameofap:
            try:
                subprocess.run(["taskkill", "/F", "/IM", "Arc.exe"], check=True)
                self.speak(f"All Brave tabs are successfully closed.")
            except subprocess.CalledProcessError:
                self.speak(f"Failed to close Brave.")
        elif "code" in Nameofap or "vs code" in Nameofap or "v s code" in Nameofap:
            try:
                subprocess.run(["taskkill", "/F", "/IM", "code.exe"], check=True)
                self.speak(f"Visual Studio code tabs are successfully closed.")
            except subprocess.CalledProcessError:
                self.speak("No Visual Studio tabs are opened.")
        elif (
            "chrome" in Nameofap
            or "chrome browser" in Nameofap
            or "all chrome" in Nameofap
        ):
            try:
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], check=True)
                self.speak(f"All Chrome tabs are successfully closed.")
            except subprocess.CalledProcessError:
                self.speak(f"Failed to close Chrome.")

    def close_bg_py(self):
        try:
            subprocess.run(["taskkill", "/F", "/IM", "pyw.exe"], check=True)
        except subprocess.CalledProcessError:
            print("No Python program found.")

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
        return "Phoenix is online, Sir."

    @staticmethod
    def coffE():
        """Returns a random reminder to drink coffee."""
        return random.choice(
            ["Take a break, grab a cup of coffee.", "Have a cup of coffee sir."]
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
            custom_box, width=300, height=150, bd=0, highlightthickness=0, bg="black"
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
        year = int(datetime.now().year)
        month = int(datetime.now().month)
        date = int(datetime.now().day)
        dy = datetime.now().strftime("%A")
        self.speak(f"It's {date} {month} {year}, {dy}.")

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
                "Have you eaten something sir?",
                "Did you have your dinner sir?",
                "Take a rest, eat something.",
            ]
        )

    @staticmethod
    def finRep():
        """Returns a random response to inquire about well-being."""
        return random.choice(["Oh, it's great sir.", "Okay sir.", "Fine sir."])

    @staticmethod
    def greet(greeting_type):
        """Returns a random greeting based on the time of day."""
        greetings = {
            "afternoon": ["Good Afternoon!", "Good Afternoon!"],
            "evening": ["Good Evening!", "Good Evening!"],
            "morning": ["Good Morning!", "Good Morning!"],
        }
        return random.choice(greetings.get(greeting_type, []))

    def handle_song_selection(self, index):
        pass

    def handle_time_based_greeting(self, tag, response):
        hour = int(datetime.now().hour)
        if tag == "morning":
            if 0 <= hour < 12:
                self.speak(response)
            elif 12 <= hour < 18:
                self.speak("You might have mistaken Sir, It's Afternoon!")
            else:
                self.speak("You might have mistaken Sir, It's Evening!")
        elif tag == "afternoon":
            if 0 <= hour < 12:
                self.speak("You might have mistaken Sir, It's Morning!")
            elif 12 <= hour < 18:
                self.speak(response)
            else:
                self.speak("You might have mistaken Sir, It's Evening!")
        elif tag == "evening":
            if 0 <= hour < 12:
                self.speak("You might have mistaken Sir, It's Morning!")
            elif 12 <= hour < 18:
                self.speak("You might have mistaken Sir, It's Afternoon!")
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
                "Hello Sir!",
                "Hello! How are you sir?",
                "Hey love! How you doing!",
                "Hello Sir! I was just thinking of you.",
                "Hello Sir! How you doing?",
            ]
        )

    def hibernatE(self):
        self.lastChargeCheck()
        hib = [
            "Alrighty, I'm out! Catch you later sir !",
            "I'm off now. See ya soon sir !",
            "Later, sir ! I'm signing off.",
            "Peace out! I'm logging off.",
            "Adios Señor! Until we meet again!",
            "Shutting down now. Take care, sir !",
            "Take care! Goodbye sir !",
            "Take care! See you next time sir !",
            "Time for me to power down. See ya sir !",
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
        self.speak("Done Sir!")

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
        CHUNK = 1024
        wf = wave.open(f"E:\\MSC\\{x}", "rb")
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
        self.speak("which Sir?")
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
        self.speak("Done sir !")

    def maximize_window(self):
        pg.keyDown("win")
        pg.press("up")
        pg.keyUp("win")
        self.speak("Done Sir!")

    def minimize_window(self):
        pg.keyDown("win")
        pg.press("down")
        pg.keyUp("win")
        self.speak("Done Sir!")

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
        return random.choice(["Welcome back Sir", "Nice to see you again sir"])

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

    def open_app(self, query, response):
        reply = response
        Nameofapp = self.opN(query)
        print(Nameofapp)
        if Nameofapp:
            if Nameofapp in ["next tab", "next app"]:
                pg.keyDown("alt")
                pg.press("tab")
                pg.keyUp("alt")
            elif Nameofapp in [
                "task list",
                "tasklist",
                "all tasks list",
                "all task list",
                "list of tasks",
            ]:
                try:
                    self.speak("Listing All tasks : ")
                    subprocess.run(["tasklist"], check=True)
                except subprocess.CalledProcessError:
                    print("Failed to load list.")
            elif "notification" in Nameofapp:
                pg.keyDown("win")
                pg.press("n")
                pg.keyUp("win")
            elif "widget" in Nameofapp or "news" in Nameofapp:
                pg.keyDown("win")
                pg.press("w")
                pg.keyUp("win")
            elif "music" in Nameofapp:
                self.speak(f"{reply} {Nameofapp}")
                pg.press("win")
                sleep(1)
                keyboard.write(Nameofapp)
                sleep(1)
                keyboard.press("enter")
                sleep(6)
                pg.press("space")
            elif "code" in Nameofapp:
                self.speak(f"{reply} {Nameofapp}")
                self.desKtoP(2)
                pg.keyDown("win")
                pg.press("4")
                pg.keyUp("win")
                sleep(6)
            elif "arc" in Nameofapp:
                self.speak(f"{reply} {Nameofapp}")
                self.desKtoP(4)
                pg.press("enter")
                pg.keyDown("win")
                pg.press("1")
                pg.keyUp("win")
                sleep(1)
            elif "brave" in Nameofapp:
                self.speak(f"{reply} {Nameofapp}")
                self.desKtoP(4)
                pg.press("enter")
                pg.keyDown("win")
                pg.press("2")
                pg.keyUp("win")
                sleep(1)
            elif "movies" in Nameofapp or "entertainment" in Nameofapp:
                self.speak(self.rP())
                self.desKtoP(2)
                npath = "E:\\MV"
                os.startfile(npath)
            elif "e drive" in Nameofapp:
                self.speak(f"{reply} {Nameofapp}")
                self.desKtoP(2)
                npath = "E:\\"
                os.startfile(npath)
            elif "c drive" in Nameofapp:
                self.speak(f"{reply} {Nameofapp}")
                self.desKtoP(2)
                npath = "C:\\"
                os.startfile(npath)
            elif "d drive" in Nameofapp:
                self.speak(f"{reply} {Nameofapp}")
                self.desKtoP(2)
                npath = "M:\\"
                os.startfile(npath)
            elif "study" in Nameofapp:
                self.desKtoP(1)
            elif "alpha" in Nameofapp:
                self.desKtoP(2)
            elif "extra" in Nameofapp:
                self.desKtoP(3)
            elif "trash" in Nameofapp or "dress" in Nameofapp:
                self.desKtoP(4)
            elif (
                "armory crate" in Nameofapp
                or "armory" in Nameofapp
                or "crate" in Nameofapp
            ):
                self.speak(f"{reply} {Nameofapp}")
                self.arMcratE()
            elif (
                "file manager" in Nameofapp
                or "this pc" in Nameofapp
                or "thispc" in Nameofapp
                or ("file explorer" in Nameofapp)
            ):
                self.speak(f"{reply} {Nameofapp}")
                self.desKtoP(3)
                pg.keyDown("win")
                pg.press("5")
                pg.keyUp("win")
                sleep(2)
            elif (
                "phoenix folder" in Nameofapp
                or "ai folder" in Nameofapp
                or "a i folder" in Nameofapp
            ):
                self.speak(f"{reply} {Nameofapp}")
                self.desKtoP(3)
                npath = "C:\\PHNX"
                os.startfile(npath)
                sleep(2)
            elif "quick" in Nameofapp or "quick configuration" in Nameofapp:
                self.speak(f"{reply} quick configuration.")
                npath = "C:\\PHNX\\Xtra\\quiK.bat"
                pg.keyDown("win")
                pg.press("up")
                pg.keyUp("win")
                os.startfile(npath)
                sleep(2)
            elif (
                "gpt" in Nameofapp or "chatgpt" in Nameofapp or "chat gpt" in Nameofapp
            ):
                self.speak(f"Starting {Nameofapp}")
                Link = "https://chat.openai.com/"
                webbrowser.open(Link)
            elif "open" in Nameofapp:
                pass
            else:
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
                if Nameofapp in ls_app:
                    self.desKtoP(3)
                    self.speak(f"{reply} {Nameofapp}")
                    pg.press("win")
                    sleep(1)
                    keyboard.write(Nameofapp)
                    sleep(1)
                    keyboard.press("enter")
                else:
                    self.speak(f"Do you want to open {Nameofapp}?")
                    conF = self.take_command().lower()
                    if conF in self.AGREE:
                        self.speak(self.rP())
                        pg.press("win")
                        sleep(1)
                        keyboard.write(Nameofapp)
                        sleep(1)
                        keyboard.press("enter")
                    else:
                        pass

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
        self.speak("Done Sir!")

    @staticmethod
    def phN():
        """Returns a system status message indicating Phoenix is online."""
        return "Phoenix is Online"

    def play_pause_action(self, query):
        ply = query.replace("play ", "")
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
        song = query.replace("play ", "").strip()
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
            "I'm on it sir",
            "On it sir",
            "as you speak sir",
            "Okay-dokay, let’s rock!",
            "You got it!",
            "Sure thing, sir!",
            "Roger that, sir!",
            "you got it, sir!",
            "Affirmative, moving on!",
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
        try:
            self.speak("Restarting Windows Explorer...")
            subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], check=True)
            print("Explorer terminated successfully.")
            sleep(2)
            subprocess.Popen(["explorer.exe"], shell=False)
            print("Explorer restarted successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error during explorer management: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def restart_phoenix(self):
        try:
            subprocess.run(["taskkill", "/F", "/IM", "pyw.exe"], check=True)
            print("All background python programs closed.")
        except Exception:
            print("No python program found.")
        self.desKtoP(3)
        path = "C:\\PHNX\\NORMAL PHOENIX\\main.bat"
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
            title="Reminder", message=reminder_message, app_name="Phoenix", timeout=10
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
            "Alrighty, I'm out! See you later sir!",
            "I'm off now. See ya soon sir!",
            "Peace out! I'm logging off.",
            "Adios Señor! Until we meet again!",
            "Shutting down now. Take care, sir!",
            "Take care! See you next time sir!",
            "Time for me to power down. See ya sir!",
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
        tt = time.strftime("%I:%M %p")
        self.speak(f"The time is {tt}.")

    def toggle_fullscreen(self):
        pg.press("f11")
        self.speak("Done Sir!")

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
                "Hello Sir! I am listening.",
                "Hello! I am here for you.",
                "Hey love! Phoenix is here.",
                "Hello Sir! Phoenix is always here for you.",
                "Hello Sir! How can I help you?",
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
                "Be hydrated sir.",
                "Drink some water sir, be hydrated.",
                "Do drink water, be hydrated.",
            ]
        )


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
    speech_engine = SpeechEngine()
    recognizer = VoiceRecognition(gui)
    utils = Utility(speech_engine, recognizer)
    main_query = "i select game1"
    list_to_compare = ["game1", "game1 i select", "i choosel game1"]
    result = compareSent(main_query, list_to_compare)
    print("Match found:", result)
    print("back to main")
