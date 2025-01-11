import pyttsx3
import random
import speech_recognition as sr
import tkinter as tk
from PIL import Image, ImageTk
import os
import pyautogui as pg
import keyboard
from time import sleep
import time
import webbrowser
from plyer import notification
import sys
import subprocess
import random
import re
from pytube import YouTube, Search
import psutil
import datetime
import pygame
import pyaudio
import wave
# from tkinter import *
from tkinter import Toplevel
import tkinter.messagebox 
from PyQt5.QtWidgets import QApplication, QDialog, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QColor, QFont

class SpeechEngine: # Text-to-Speech Engine
    def __init__(self):
        self.engine = pyttsx3.init('sapi5')
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[1].id)
        self.engine.setProperty('rate', 174)
    
    def speak(self, audio):
        # Replace "sir" with a random respectful term
        replacements = ["boss", "my lord"]
        for punctuation in ["", "?", "!", ".", " "]:
            if f"sir{punctuation}" in audio:
                replacement = random.choice(replacements)
                audio = audio.replace(f"sir{punctuation}", f"{replacement}{punctuation}") 
                break
        self.engine.say(audio)
        print(f"$ : {audio}")
        self.engine.runAndWait()

class VoiceAssistantGUI:  # GUI for Voice Assistant
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.9)
        self.root.attributes("-topmost", True)
        self.setup_transparency()

        self.mic_label = tk.Label(self.root, bg='white')
        self.mic_label.pack()

        # Get the directory of the current script
        current_dir = os.path.dirname(__file__)

        # Construct relative paths to the images
        # self.listen_img_path = os.path.join(current_dir, "assets", "img", "green.png")
        self.listen_img_path = "E:\\STDY\\GIT_PROJECTS\\Phoenix\\assets\\img\\green.png"
        self.recognize_img_path = "E:\\STDY\\GIT_PROJECTS\\Phoenix\\assets\\img\\red.png"
        # self.recognize_img_path = os.path.join(current_dir, "assets", "img", "red.png")
        
        print(f"Listen image path: {self.listen_img_path}")
        print(f"Recognize image path: {self.recognize_img_path}")
        
        # Verify if image paths exist
        if not os.path.exists(self.listen_img_path):
            print("Error: Listen image not found!")
        if not os.path.exists(self.recognize_img_path):
            print("Error: Recognize image not found!")

        # Load images
        self.listen_img = Image.open(self.listen_img_path)
        self.recognize_img = Image.open(self.recognize_img_path)

        # Configure window geometry
        max_width = max(4, 4)
        max_height = max(30, 30)
        x_offset = self.root.winfo_screenwidth() - max_width
        y_offset = self.root.winfo_screenheight() - max_height
        self.root.geometry(f"{max_width}x{max_height}+{x_offset}+{y_offset}")

    def setup_transparency(self):  # Set transparency based on OS
        if self.root.tk.call('tk', 'windowingsystem') == 'win32':  # Windows
            self.root.attributes('-topmost', 1)  # Always on top
        elif self.root.tk.call('tk', 'windowingsystem') == 'x11':  # Linux
            self.root.attributes('-type', 'dock')  # Dock
        elif self.root.tk.call('tk', 'windowingsystem') == 'aqua':  # MacOS
            self.root.call('::tk::unsupported::MacWindowStyle', 'style', self.root._w, 'help', 'none')  # No title bar
        self.root.wm_attributes("-transparentcolor", "white")  # Set white as transparent

    def show_listen_image(self):
        # self.mic_label.config(image=None)
        mic_img = Image.open(self.listen_img_path).convert("RGBA")
        mic_img = mic_img.resize((40, 40), Image.LANCZOS)
        mic_img = ImageTk.PhotoImage(mic_img)
        self.mic_label.config(image=mic_img)
        self.mic_label.image = mic_img
        self.root.update()


    def hide_listen_image(self):
        self.mic_label.config(image=None)

    def show_recognize_image(self):
        self.mic_label.config(image=None)
        recognize_img = ImageTk.PhotoImage(self.recognize_img.resize((40, 40), Image.LANCZOS).convert("RGBA"))
        self.mic_label.config(image=recognize_img)
        self.mic_label.image = recognize_img
        self.root.update()

    def hide_recognize_image(self):
        self.mic_label.config(image=None)

class VoiceRecognition:
    def __init__(self, gui):
        self.recognizer = sr.Recognizer()
        self.gui = gui

    def take_command(self):
        with sr.Microphone() as source:
            self.gui.show_listen_image()
            print(">>>",end="\r")
            audio = self.recognizer.listen(source, 0, 5)
        
        try:
            self.recognizer.pause_threshold = 1
            self.gui.show_recognize_image()
            print("<<<",end="\r")
            query = self.recognizer.recognize_google(audio, language='en-in')
            print(f"# : {query}\n")
        except Exception as e:
            print("<!>",end="\r")
            self.gui.hide_listen_image()
            return ""
        
        return query
class Utility:
    MONTH_DICT = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
    }

    WORD_TO_NUM = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50
    }
    def __init__(self, speech_engine, voice_recognition,sleep_time=1):
        self.speech_engine = speech_engine
        self.voice_recognition = voice_recognition
        self.sleep_time = sleep_time  # Default sleep time (can be adjusted)

    def speak(self, message):
        self.speech_engine.speak(message)

    def take_command(self):
        return self.voice_recognition.take_command()

    def calC(self):
        try:
            self.speak("sir, tell me the first number:")
            x = self.take_command()
            self.speak("And the second number?")
            y = self.take_command()
            self.speak("Which arithmetic operation should I perform?")
            operation = self.take_command().lower()

            z = None
            if 'addition' in operation or 'sum' in operation or 'plus' in operation:
                z = int(x) + int(y)
                self.speak(f"The addition result is {z}")
            elif 'subtraction' in operation or 'minus' in operation:
                z = int(x) - int(y)
                self.speak(f"The subtraction result is {z}")
            elif 'multiplication' in operation:
                z = int(x) * int(y)
                self.speak(f"The multiplication result is {z}")
            elif 'division' in operation:
                if int(y) == 0:
                    self.speak("Division by zero is undefined.")
                else:
                    z = int(x) / int(y)
                    self.speak(f"The division result is {z}")
            elif 'modulo' in operation or 'remainder' in operation:
                z = int(x) % int(y)
                self.speak(f"The modulo result is {z}")
            else:
                self.speak("I couldn't understand the operation.")
        except Exception as e:
            self.speak("I couldn't process the input. Please try again.")

    def press(self, key, times):
        try:
            for _ in range(times):
                pg.press(key)
                sleep(1)
            self.speak(f"Pressed the {key} key {times} times.")
        except Exception as e:
            self.speak("An error occurred while pressing the key.")

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

    def screenshot(self):
        try:
            pg.keyDown("win")
            pg.press("prntscrn")
            pg.keyUp("win")
            self.speak("Screenshot captured, sir.")
        except Exception as e:
            self.speak("An error occurred while taking the screenshot.")

    def change_tab(self, n=1):
        try:
            pg.keyDown("ctrl")
            for _ in range(n):
                pg.press("tab")
            pg.keyUp("ctrl")
            self.speak(f"Switched {n} tabs to the right.")
        except Exception as e:
            self.speak("An error occurred while changing tabs.")

    def new_tab(self, n=1):
        try:
            pg.keyDown("ctrl")
            for _ in range(n):
                pg.press("t")
            pg.keyUp("ctrl")
            self.speak(f"Opened {n} new tabs.")
        except Exception as e:
            self.speak("An error occurred while opening new tabs.")

    def close_tab(self, n=1):
        try:
            pg.keyDown("ctrl")
            for _ in range(n):
                pg.press("w")
            pg.keyUp("ctrl")
            self.speak(f"Closed {n} tabs.")
        except Exception as e:
            self.speak("An error occurred while closing tabs.")

    def app_switch(self):
        try:
            pg.keyDown("alt")
            pg.press("tab")
            self.speak("Which tab should I switch to, sir?")
            while True:
                print(">>> Listening for tab switch command...")
                command = self.take_command().lower()
                if 'this' in command or 'same' in command or 'opened' in command:
                    pg.press("enter")
                    pg.keyUp("alt")
                    self.speak("Done, sir!")
                    break
                elif 'left' in command:
                    pg.press("left")
                    pg.keyUp("alt")
                    self.speak("Switched to the left tab, sir!")
                    break
                elif 'right' in command:
                    right_steps = self._extract_steps(command, 'right')
                    for _ in range(right_steps):
                        pg.press("right")
                    pg.keyUp("alt")
                    self.speak(f"Switched {right_steps} tabs to the right, sir!")
                    break
                else:
                    self.speak("I didn't understand the command. Please repeat.")
        except Exception as e:
            self.speak("An error occurred while switching applications.")

    def _extract_steps(self, command, direction): # Extract number of steps from command used in app_switch
        words = command.split()
        for word in words:
            if word.isdigit():
                return int(word)
        return 1  # Default to 1 step if no number is found

    def arMcratE(self):
        """
        Automates the process of opening Armory Crate application
        and performing specific actions within it.
        """
        self.desKtoP(3)
        sleep(1)
        pg.keyDown("win")
        pg.press("7")  # Assumes Armory Crate is pinned as the 6th item in the taskbar
        pg.keyUp("win")
        self.speak("Armory Crate has been opened.")

        # Uncomment and customize this section if specific key navigation is needed.
        # pg.press("tab", presses=9, interval=0.5)
        # pg.press("down")
        # pg.press("enter")
        # self.speak("Selected the desired option in Armory Crate.")

    def alrM(self):
        """
        Sets up an alarm at the specified time.
        """
        self.speak("Please enter the alarm time.")
        print(time.localtime())
        alarm_time = input("Enter the alarm time in HH:MM format: ")

        try:
            alarm_hour, alarm_minute = map(int, alarm_time.split(':'))
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
            time.sleep(10)  # Check every 10 seconds

    def extracTnumbeR(self, string):
        """
        Extracts a number (in digit or word form) from a string based on the format "change tab to X".
        """
        match = re.search(r'change tab(?: (?:to|with))? (\w+)', string, re.IGNORECASE)
        if match:
            number_str = match.group(1).strip().lower()
            if number_str.isdigit():
                return int(number_str)
            if number_str in self.word_to_num_map:
                return self.word_to_num_map[number_str]
            raise ValueError(f"Cannot convert '{number_str}' to a number.")
        else:
            return 1

    def mute_speaker(self):
        """Mute the system volume."""
        os.system("nircmd.exe mutesysvolume 1")
        self.speak("System volume has been muted.")

    def unmute_speaker(self):
        """Unmute the system volume."""
        os.system("nircmd.exe mutesysvolume 0")
        self.speak("System volume has been unmuted.")

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

    def adj_brightness(self,change):
        direction = "increased" if change > 0 else "decreased"
        cmd = f'powershell -Command "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, ((Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness + {change}))"'
        os.system(cmd)
        print(f"Brightness has been {direction} by {abs(change)}%")

    def rP(self):
        rply = [
            "I'm on it sir", "Roger that sir", "On it sir", "as you speak sir"
        ]
        return random.choice(rply)

    def askDesk(self):
        rply = [
            "which desktop shall I open, sir?", "which desktop would you like me to open sir?",
        ]
        return random.choice(rply)

    def play_song(self,song):
        search = Search(song)
        video_url = search.results[0].watch_url
        print(f"Playing: {video_url}")
        webbrowser.open(video_url)

    def snG(self):
        """Searches and plays a random song directly on YouTube."""
        song_list = [
            "Pee loon song", "Channa ve", "Tu Jaane na", "Tera ban jaunga", 
            "Khairiyat", "Tujhe kitna Chahne lage by Jubin", "Vaaste",
            "Tujhe Bhula diya", "Tum hi Aana", "Bhula diya by Darshan Raval",
            "Dekhte Dekhte by Atif Aslam", "Dillagi by Rahat fateh ali khan",
            "Lo safar", "Toota jo kabhi Tara", "Teri Ore", "Falak Tak reverb",
            "Pehla Nasha by Udit Narayan", "Tum se hi", "Chale Jana Phir",
            "Tera Pyar", "Kya Mujhe Pyaar Hai", "Tere Nainon Mein",
            "Hale Dil Tujhko Sunata", "Agar Tum Sath Ho", "Lord Imran Khan's playlist",
            "Tere Vaaste", "Mareez E Ishq", "Hale Dil", "Zara Zara by Jalraj",
            "Tere Liye", "Ye Tune Kya Kiya", "Labon Ko", "Pehli Nazar Mein",
            "Zara Sa", "Wajah Tum Ho", "Mat Aazma Re", "Tu Hai ki Nahi",
            "Raataaan Lambiyan", "Tune jo Na Kaha", "Thodi der from Half girlfriend",
            "Zindagi Se", "Best of AP Dhillon"
        ]
        # Randomly select a song
        song_name = random.choice(song_list)
        print(f"Playing a random song: {song_name}")
        self.play_song(song_name)
                
    @staticmethod
    def whTabT():
        abt_list = ["What about", "How about", "You shall listen", "what about this one:"]
        return random.choice(abt_list)

    @staticmethod
    def opN(query1):
        app_name = ""
        # Split the query into words
        words = query1.split()
        # Check if the first word in the query matches any of the keywords
        if words[0] in ["open", "launch", "start"]:
            # Store the next word after x in app_name
            if len(words) > 2:
                app_name = words[1] + " " + words[2]
            else:
                app_name = words[1]
        return app_name

    @staticmethod
    def adjust_volume(query):
        # Define patterns and keywords
        inc_vol_keywords = ["increase", "increased"]
        dec_vol_keywords = ["decrease", "decreased"]
        # Unified regex pattern for capturing numbers with or without a percentage sign
        pattern = r'\b\d+%?'
        # Check if "set" is in query
        if "set" in query:
            match = re.search(pattern, query)
            if match:
                # Extract numeric value and remove percentage sign if present
                value = int(re.sub(r'\D', '', match.group()))
                Utility.adj_volume("set", value)
        else:
            # Check for increase or decrease keywords
            if any(word in query for word in inc_vol_keywords):
                Utility.adj_volume("increase", None)
            elif any(word in query for word in dec_vol_keywords):
                Utility.adj_volume("decrease", None)

    @staticmethod
    def adjust_brightness(query):
        # Define patterns and keywords
        inc_bright_keywords = ["increase", "increased"]
        dec_bright_keywords = ["decrease", "decreased"]
        # Unified regex pattern for capturing numbers with or without a percentage sign
        pattern = r'\b\d+%?'
        # Check if "by" is in query, indicating a specific adjustment amount
        if "by" in query:
            match = re.search(pattern, query)
            if match:
                # Extract numeric value and remove percentage sign if present
                value = int(match.group().rstrip('%'))
                if any(word in query for word in inc_bright_keywords):
                    Utility.adj_brightness(value)
                elif any(word in query for word in dec_bright_keywords):
                    Utility.adj_brightness(-value)
        else:
            # Default adjustment amount is 10%
            if any(word in query for word in inc_bright_keywords):
                Utility.adj_brightness(10)
            elif any(word in query for word in dec_bright_keywords):
                Utility.adj_brightness(-10)

    @staticmethod
    def adj_volume(action, value=None):
        # Example implementation for volume adjustment
        if action == "set":
            print(f"Setting volume to {value}%")
        elif action == "increase":
            print("Increasing volume")
        elif action == "decrease":
            print("Decreasing volume")

    @staticmethod
    def adj_brightness(value):
        # Example implementation for brightness adjustment
        if value > 0:
            print(f"Increasing brightness by {value}%")
        else:
            print(f"Decreasing brightness by {-value}%")
    
    def date(self):
        year = int(datetime.datetime.now().year)
        month = int(datetime.datetime.now().month)
        date = int(datetime.datetime.now().day)
        dy = datetime.datetime.now().strftime("%A")
        self.speak(f"It's {date} {month} {year}, {dy}.")

    def tim(self):
        tt = time.strftime("%I:%M %p")
        self.speak(f"The time is {tt}.")

    def battery_check(self):
        battery = psutil.sensors_battery()
        battery_percentage = int(battery.percent)
        plugged = battery.power_plugged
        if plugged:
            self.speak(f"The device is containing {battery_percentage} percent charge. \nAnd it is being charged.")
        if not plugged:
            self.speak(f"The device is containing {battery_percentage} percent charge.")
            if battery_percentage >= 80 and battery_percentage <= 100:
                self.speak("Battery is quite good, Sir.")
            elif battery_percentage >= 60 and battery_percentage < 80:
                self.speak("Battery is ok, Sir.")
            elif battery_percentage <= 35:
                self.speak("Plug in the charger sir!")

    def lastChargeCheck(self):
        battery = psutil.sensors_battery()
        plugged = battery.power_plugged
        battery_percentage = int(battery.percent)
        if plugged:
            if battery_percentage == 100:
                self.speak("Sir, the device is fully charged!")
            elif battery_percentage < 100 and battery_percentage >= 80:
                self.speak(f"Sir, device is {battery_percentage}% charged. Do remember to unplug the charger after some time.")
            elif battery_percentage < 80 and battery_percentage >= 35:
                self.speak(f"Sir, device is {battery_percentage}% charged. Let the laptop charge for a while.")
        elif not plugged:
            if battery_percentage < 85 and battery_percentage >= 35:
                self.speak(f"Sir, device has {battery_percentage}% charge. Let the laptop charge for a while.")

    def shutD(self):
        self.lastChargeCheck()
        sht1 = [
            "The PC will shut down in less than a minute.",
            "The computer will be shutting down in under a minute.",
            "Your PC is about to shut down in less than 60 seconds.",
            "The system will power off in less than a minute.",
            "PC shutdown will occur in less than a minute.",
            "The computer will turn off in less than a minute.",
            "The PC will be shutting down shortly, in less than a minute.",
            "In less than one minute, the PC will shut down.",
            "Shutdown in progress: PC will turn off in under a minute.",
            "The PC will be powered down in less than a minute."
        ]
        sht2 = [
            "Alrighty, I'm out! See you later sir!",
            "Time for me to power down. See ya sir!",
            "Shutting down now. Take care, sir!",
            "Peace out! I'm logging off.",
            "I'm off now. See ya soon sir!",
            "Adios Señor! Until we meet again!",
            "Take care! See you next time sir!"
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

    def hibernatE(self):
        self.lastChargeCheck()
        hib = ["Alrighty, I'm out! Catch you later sir !",
               "Time for me to power down. See ya sir !",
               "Shutting down now. Take care, sir !",
               "Peace out! I'm logging off.",
               "Later, sir ! I'm signing off.",
               "I'm off now. See ya soon sir !",
               "Adios Señor! Until we meet again!",
               "Take care! See you next time sir !",
               "Take care! Goodbye sir !"]
        hibi = random.choice(hib)
        self.speak(hibi)
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        sleep(40)
        self.restart_explorer()
        self.speak(self.onL())

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

    def maiNdesKtoP(self):
        self.speak("which Sir?")
        print("study(0),alpha(1),extra(2),trash(3)")
        dt = self.take_command().lower()
        if 'study' in dt or 'zero' in dt or '0' in dt:
            self.desKtoP(0)
        elif 'alpha' in dt or '1' in dt or 'one' in dt or 'first' in dt:
            self.desKtoP(0)
        elif 'extra' in dt or '2' in dt or 'two' in dt or 'second' in dt:
            self.desKtoP(2)
        elif 'trash' in dt or '3' in dt or 'three' in dt or 'third' in dt:
            self.desKtoP(3)
        self.speak("Done sir !")
    
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

    def _click_at_position(self, x, y):
        """Helper function to click at specific screen coordinates."""
        pg.leftClick(x, y)
        sleep(self.sleep_time)

    def desKtoP(self, screen_index):
        """Generalized method for desk-to-previous method calls."""
        positions = {
            0: (466, 945),
            1: (709, 945),
            2: (958, 945),
            3: (1201, 945)
        }

        # If the screen_index is not valid, we return early
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
        pg.press("down", presses=3)  # We can do all 3 'down' presses in one line
        pg.press("enter", presses=2)

    @staticmethod
    def tM():
        """Returns a random time-related phrase."""
        return random.choice(["It's", "The time is", "Time is"])

    @staticmethod
    def greet(greeting_type):
        """Returns a random greeting based on the time of day."""
        greetings = {
            'morning': ["Good Morning!", "Good Morning!"],
            'afternoon': ["Good Afternoon!", "Good Afternoon!"],
            'evening': ["Good Evening!", "Good Evening!"]
        }
        return random.choice(greetings.get(greeting_type, []))

    @staticmethod
    def cmnD():
        """Returns a system status message."""
        return "Phoenix is online, Sir."

    @staticmethod
    def phN():
        """Returns a system status message indicating Phoenix is online."""
        return "Phoenix is Online"

    @staticmethod
    def onL():
        """Returns a random welcome back message."""
        return random.choice(["Welcome back Sir", "Nice to see you again sir"])

    @staticmethod
    def helO():
        """Returns a random greeting message."""
        return random.choice([
            "Hello Sir!",
            "Hello! How are you sir?",
            "Hey love! How you doing!",
            "Hello Sir! I was just thinking of you.",
            "Hello Sir! How you doing?"
        ])

    @staticmethod
    def finRep():
        """Returns a random response to inquire about well-being."""
        return random.choice(["Oh, it's great sir.", "Okay sir.", "Fine sir."])

    @staticmethod
    def wtR():
        """Returns a random reminder to drink water."""
        return random.choice([
            "Be hydrated sir.",
            "Drink some water sir, be hydrated.",
            "Do drink water, be hydrated."
        ])

    @staticmethod
    def eaT():
        """Returns a random reminder to eat."""
        return random.choice([
            "Have you eaten something sir?",
            "Did you have your dinner sir?",
            "Take a rest, eat something."
        ])

    @staticmethod
    def wakE():
        """Returns a random greeting when the user wakes up."""
        return random.choice([
            "Hello Sir! I am listening.",
            "Hello! I am here for you.",
            "Hey love! Phoenix is here.",
            "Hello Sir! Phoenix is always here for you.",
            "Hello Sir! How can I help you?"
        ])

    @staticmethod
    def awaK():
        """Returns a random reminder when the user is still awake."""
        return random.choice([
            "Oh, are you still awake?",
            "You still awake! Don't you have to go to college tomorrow?",
            "Haven't you slept yet?"
        ])

    @staticmethod
    def coffE():
        """Returns a random reminder to drink coffee."""
        return random.choice([
            "Take a break, grab a cup of coffee.",
            "Have a cup of coffee sir."
        ])

    @staticmethod
    def intrOmsC():
        """Plays a random system intro sound."""
        intr = ["robo1.wav", "robo2.wav"]
        x = random.choice(intr)
        CHUNK = 1024
        wf = wave.open(f"E:\\MSC\\{x}", 'rb')
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)
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

    @staticmethod
    def rockMsc(volume):
        """Plays a random rock music track for a fixed duration."""
        intr = ["rock1.mp3", "rock2.mp3", "rock3.mp3"]
        x = random.choice(intr)
        file_path = f"E:\\MSC\\{x}"  # Construct the file path
        duration = 25  # Set duration to 25 seconds
        
        pygame.mixer.init()  # Initialize the mixer

        try:
            # Load the music
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(volume)
            print(f"Volume set to {volume * 100}%")
            # Play the music
            pygame.mixer.music.play()
            print(f"Playing {file_path} for {duration} seconds...")
            
            # Wait for the specified duration
            time.sleep(duration)
            
            # Stop the music
            pygame.mixer.music.stop()
            print("Music stopped.")
        
        except Exception as e:
            print(f"An error occurred: {e}")
        
    def _word_to_number(self,word):
        """Convert word numbers to integers."""
        return Utility.WORD_TO_NUM.get(word.lower(), None)

    def _extract_number(self, text):
        """Extract a number from the given text."""
        # Split the text into words
        words = text.split()
        # Iterate over the words to find the number
        for word in words:
            if word.isdigit():
                return int(word)
            if word.lower() in Utility.WORD_TO_NUM:
                return Utility.WORD_TO_NUM[word.lower()]
        return None
    
    def _parse_time(self, time_str):
        """
        Parse time from text input and return it in HH:MM format.
        
        Supports various AM/PM formats and ensures proper hour/minute conversion.
        If an error occurs, fall back to CLI input.
        """
        try:
            # Regex pattern to extract time and AM/PM
            alarm_pattern = re.compile(
                r'(\d{1,4})\s?([ap]\.?m\.?)', re.IGNORECASE
            )
            match = alarm_pattern.search(time_str)

            if match:
                # Extract raw time and period (AM/PM)
                raw_time = match.group(1)
                period = match.group(2).lower()

                # Convert period to standardized 'am' or 'pm'
                period = 'am' if 'a' in period else 'pm'

                # Extract hour and minute from raw time
                if len(raw_time) <= 2:  # If only hour is provided (e.g., "1am")
                    hour = int(raw_time)
                    minute = 0
                else:  # Full time provided (e.g., "1241am")
                    hour = int(raw_time[:-2])  # Extract hour part
                    minute = int(raw_time[-2:])  # Extract minute part

                # Adjust hour for 12-hour to 24-hour conversion
                if period == 'am':
                    hour = hour if hour < 12 else 0  # 12 AM is 00
                elif period == 'pm':
                    hour = hour if hour == 12 else hour + 12  # 12 PM is 12, others add 12

                return hour, minute

            # If parsing fails, raise a ValueError
            raise ValueError("Time parsing failed")
        
        except Exception as e:
            # Fallback to CLI input if an error occurs
            self.speak("Invalid time format detected. Please provide the time again.")
            self.speak("At what time should I set the reminder?")
            reminder_time = input(" (Provide in HH:MM format) : ")

            # Handle fallback input
            try:
                hour, minute = map(int, reminder_time.split(':'))
                return hour, minute
            except ValueError:
                self.speak("The time you entered is still invalid. Please try again.")
                return None, None

    def _parse_date(self,date_str):
        """Parse date from text input."""
        if date_str.lower() in {"today", "to day", "2 day", "to-day", "2-day"}:
            today = datetime.datetime.now()
            return today.month, today.day

        match = re.search(r'\d+', date_str)
        month = None
        day = None
        for month_name, month_num in Utility.MONTH_DICT.items():
            if month_name in date_str.lower():
                month = month_num
                break

        if match:
            day = int(match.group())

        if month and day:
            return month, day
        return None, None
 
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

        now = datetime.datetime.now()
        reminder_datetime = datetime.datetime(now.year, month, day, hour, minute)
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
            timeout=10  # Notification visible for 10 seconds
        )
        self.speak("Reminder notification delivered, sir!")

        import tkinter as tk

    def custom_message(self, title, message):
        """Creates a custom message box with rounded corners."""
        # Create a top-level window
        custom_box = tk.Toplevel()
        custom_box.geometry("300x150")  # Set size of the window
        custom_box.overrideredirect(True)  # Remove the title bar
        custom_box.attributes("-topmost", True)  # Always on top

        # Position the message box at the top-right corner of the screen
        custom_box.update_idletasks()
        screen_width = custom_box.winfo_screenwidth()
        size = tuple(int(_) for _ in custom_box.geometry().split('+')[0].split('x'))
        x = screen_width - size[0] - 10  # Position at right side with padding
        custom_box.geometry(f"{size[0]}x{size[1]}+{int(x)}+10")

        # Create a canvas to simulate rounded corners
        canvas = tk.Canvas(custom_box, width=300, height=150, bd=0, highlightthickness=0, bg="black")
        canvas.pack()

        # Draw a rounded rectangle using polygons and ovals
        canvas.create_oval(0, 0, 30, 30, fill="#2c3e50", outline="#2c3e50")  # Top-left
        canvas.create_oval(270, 0, 300, 30, fill="#2c3e50", outline="#2c3e50")  # Top-right
        canvas.create_oval(0, 120, 30, 150, fill="#2c3e50", outline="#2c3e50")  # Bottom-left
        canvas.create_oval(270, 120, 300, 150, fill="#2c3e50", outline="#2c3e50")  # Bottom-right
        canvas.create_rectangle(15, 0, 285, 150, fill="#2c3e50", outline="#2c3e50")
        canvas.create_rectangle(0, 15, 300, 135, fill="#2c3e50", outline="#2c3e50")

        # Create a frame to hold the content (on top of canvas)
        content_frame = tk.Frame(custom_box, bg="#2c3e50", bd=0)
        content_frame.place(x=0, y=0, width=300, height=150)

        # Title label
        title_label = tk.Label(
            content_frame,
            text=title,
            bg="#2c3e50",
            fg="#f1c40f",
            font=("Arial", 14, "bold"),
            wraplength=250
        )
        title_label.pack(pady=(10, 5))

        # Message label
        message_label = tk.Label(
            content_frame,
            text=message,
            bg="#2c3e50",
            fg="#ecf0f1",
            font=("Arial", 12),
            wraplength=250
        )
        message_label.pack(pady=5)

        # OK button
        ok_button = tk.Button(
            content_frame,
            text="OK",
            bg="#16a085",
            fg="white",
            font=("Arial", 10),
            command=custom_box.destroy
        )
        ok_button.pack(pady=10)

        # Focus handling
        custom_box.transient()
        custom_box.grab_set()
        custom_box.wait_window()

    def set_timer(self):
        """
        Sets a timer based on user input.
        Notifies the user when the timer ends.
        """
        try:
            # Prompt user to enter timer duration
            self.speak("For how long should I set the timer?")
            print("e.g :: 1 hour, 5 minutes, or 1 hour and 30 minutes)")
            time_input = self.take_command().lower()

            # Parse input to extract hours, minutes, and seconds
            hours, minutes, seconds = self._parse_time_duration(time_input)
            
            if hours is None and minutes is None and seconds is None:
                self.speak("Sorry, I couldn't understand the duration. Please try again.")
                return

            # Convert to total seconds
            total_seconds = hours * 3600 + minutes * 60 + seconds

            # Confirm the timer
            self.speak(f"Setting a timer for {hours} hour(s), {minutes} minute(s), and {seconds} second(s).")
            print(f"Timer set for {hours} hour(s), {minutes} minute(s), and {seconds} second(s).")

            # Countdown timer
            while total_seconds:
                mins, secs = divmod(total_seconds, 60)
                hrs, mins = divmod(mins, 60)
                timer = f'{hrs:02d}:{mins:02d}:{secs:02d}'
                print(f"Time left: {timer}", end="\r")  # Dynamic countdown
                time.sleep(1)
                total_seconds -= 1

            # Notify when timer ends
            self.speak("\nTime's up!")
            # Show a custom message using RoundedMessageBox

            app = QApplication(sys.argv)  # Ensure an application instance exists
            message_box = RoundedMessageBox("Timer", "Time's up, sir!")
            message_box.exec_()
            sys.exit(app.exec_())  # Terminate the application after the dialog closes
            
        except Exception as e:
            self.speak(f"An error occurred while setting the timer: {str(e)}")
        return
    
    def _parse_time_duration(self, time_str):
        """
        Parses the timer duration from the input string.
        Returns the duration in hours, minutes, and seconds.
        """
        try:
            # Regex pattern to match hours, minutes, and seconds
            duration_pattern = re.compile(
                r'(?:(\d+)\s*hour(?:s)?)?\s*'
                r'(?:(\d+)\s*minute(?:s)?)?\s*'
                r'(?:(\d+)\s*second(?:s)?)?',
                re.IGNORECASE
            )
            match = duration_pattern.search(time_str)

            if match:
                hours = int(match.group(1)) if match.group(1) else 0
                minutes = int(match.group(2)) if match.group(2) else 0
                seconds = int(match.group(3)) if match.group(3) else 0
                return hours, minutes, seconds

            return None, None, None
        except Exception as e:
            self.speak("I couldn't parse the time duration. Please try again.")
            return None, None, None

    # def close_app(self, app_name):
    #     """
    #     Close a specific application using its name.
    #     :param app_name: Name of the application to close.
    #     """
    #     app_name = app_name.lower()
    #     if "chrome" in app_name:
    #         os.system("taskkill /f /im chrome.exe")
    #         self.speak("Google Chrome has been closed.")
    #     elif "notepad" in app_name:
    #         os.system("taskkill /f /im notepad.exe")
    #         self.speak("Notepad has been closed.")
    #     elif "calculator" in app_name:
    #         os.system("taskkill /f /im calculator.exe")
    #         self.speak("Calculator has been closed.")
    #     else:
    #         self.speak("I don't know how to close that application.")
# Main Application
class RoundedMessageBox(QDialog):
    def __init__(self, title, message):
        super().__init__()
        # Set up window attributes
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 150)
        self.init_ui(title, message)

    def init_ui(self, title, message):
        # Set up the layout with custom margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title label
        title_label = QLabel(title, self)
        title_label.setStyleSheet(
            "color: #f1c40f; font-size: 16px; font-weight: bold;"
        )
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Message label
        message_label = QLabel(message, self)
        message_label.setStyleSheet("color: #ecf0f1; font-size: 14px;")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(message_label)

        # OK button
        ok_button = QPushButton("OK", self)
        ok_button.setStyleSheet(
            """
            QPushButton {
                background-color: #16a085;
                color: white;
                font-size: 12px;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #1abc9c;
            }
            """
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

def music(Utility): #integrating more function into one  
    # Playing intro sound (ensure the file path is correct)
    Utility.intrOmsC()

    # Playing rock music with 50% volume (ensure the file path is correct)
    Utility.rockMsc(0.5)

if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    speech_engine = SpeechEngine()
    recognizer = VoiceRecognition(gui)
    utils = Utility(speech_engine, recognizer)
    gui.show_listen_image()
    while True:
        recognizer.take_command()
    # Example usage
    # utils.speak("Utility functions are ready.")
    # utils.calC()  # Example for calculator function
    # utils.press("enter", 3)  # Example for press function
    # utils.bluetooth()  # Example for Bluetooth toggle
    # utils.hotspot()  # Example for hotspot toggle
    # utils.screenshot()  # Example for hotspot toggle
    # utils.snG()  # Example for hotspot toggle
    # utils.desKtoP_4()  # Example for hotspot toggle
    # utils.set_reminder()  
    # utils.set_timer()  
    # utils.custom_message("Phoenix:","Time's up")  
    # app = QApplication(sys.argv)

    # Display the custom message box
    # message_box = RoundedMessageBox(
    #     "Custom Title", "This is a custom message box with rounded corners!"
    # )
    # message_box.exec_()
    # # print(utils._parse_time("1341"))  
    # sleep(5)
    print("back to main")
    
    
    # music(Utility)


    # print(("second".isdigit()))



