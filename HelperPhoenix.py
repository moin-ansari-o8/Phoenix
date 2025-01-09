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
import random
import re
from pytube import YouTube, Search
import psutil
import datetime
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

class VoiceAssistantGUI: # GUI for Voice Assistant
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
        self.listen_img = Image.open(os.path.join(current_dir, "assets", "img", "green.png"))
        self.recognize_img = Image.open(os.path.join(current_dir, "assets", "img", "red.png"))

        # Configure window geometry
        max_width, max_height = 4, 30
        x_offset = self.root.winfo_screenwidth() - max_width
        y_offset = self.root.winfo_screenheight() - max_height
        self.root.geometry(f"{max_width}x{max_height}+{x_offset}+{y_offset}")

    def setup_transparency(self): # Set transparency based on OS
        if self.root.tk.call('tk', 'windowingsystem') == 'win32': # Windows
            self.root.attributes('-topmost', 1) # Always on top
        elif self.root.tk.call('tk', 'windowingsystem') == 'x11': # Linux
            self.root.attributes('-type', 'dock') # Dock
        elif self.root.tk.call('tk', 'windowingsystem') == 'aqua': # MacOS
            self.root.call('::tk::unsupported::MacWindowStyle', 'style', self.root._w, 'help', 'none') # No title bar
        self.root.wm_attributes("-transparentcolor", "white") # Set white as transparent

    def show_listen_image(self):
        mic_img = ImageTk.PhotoImage(self.listen_img.resize((40, 40), Image.LANCZOS).convert("RGBA"))
        self.mic_label.config(image=mic_img)
        self.mic_label.image = mic_img
        self.root.update()
    
    def hide_listen_image(self):
        self.mic_label.config(image=None)

    def show_recognize_image(self):
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
            print(">>> Listening...")
            audio = self.recognizer.listen(source, 0, 5)
        
        try:
            self.recognizer.pause_threshold = 1
            self.gui.show_recognize_image()
            print("<<< Recognizing...")
            query = self.recognizer.recognize_google(audio, language='en-in')
            print(f"# : {query}\n")
        except Exception as e:
            print("<!> Error Recognizing")
            self.gui.hide_listen_image()
            return ""
        
        return query

class Utility:
    word_to_num_map = {
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
        # Extend as needed
    }
    
    def __init__(self, speech_engine, voice_recognition):
        self.speech_engine = speech_engine
        self.voice_recognition = voice_recognition

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
                    right_steps = self.extract_steps(command, 'right')
                    for _ in range(right_steps):
                        pg.press("right")
                    pg.keyUp("alt")
                    self.speak(f"Switched {right_steps} tabs to the right, sir!")
                    break
                else:
                    self.speak("I didn't understand the command. Please repeat.")
        except Exception as e:
            self.speak("An error occurred while switching applications.")

    def extract_steps(self, command, direction): # Extract number of steps from command used in app_switch
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
        self.desKtoP_3()
        sleep(1)
        pg.keyDown("win")
        pg.press("6")  # Assumes Armory Crate is pinned as the 6th item in the taskbar
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

    def battery(self):
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
                self.speak("Sir, the device is fully charged! Do remember to unplug the charger.")
            elif battery_percentage < 100 and battery_percentage >= 80:
                self.speak(f"Sir, device is {battery_percentage}% charged. Do remember to unplug the charger after some time.")
            elif battery_percentage < 80 and battery_percentage >= 35:
                self.speak(f"Sir, device is {battery_percentage}% charged. Let the laptop charge for a while and do remember to unplug the charger after some time.")
        elif not plugged:
            if battery_percentage < 85 and battery_percentage >= 35:
                self.speak(f"Sir, device has {battery_percentage}% charge. Let the laptop charge for a while and do remember to unplug the charger after some time.")

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
            "Alrighty, I'm out! Catch you later sir!",
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
            os.system("taskkill /F /IM brave.exe")
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
        sleep(10)
        self.speak(shti2)
    # def open_app(self, app_name):
    #     """
    #     Open a specific application using its name.
    #     :param app_name: Name of the application to open.
    #     """
    #     app_name = app_name.lower()
    #     if "chrome" in app_name:
    #         os.system("start chrome")
    #         self.speak("Google Chrome has been opened.")
    #     elif "notepad" in app_name:
    #         os.system("start notepad")
    #         self.speak("Notepad has been opened.")
    #     elif "calculator" in app_name:
    #         os.system("start calc")
    #         self.speak("Calculator has been opened.")
    #     else:
    #         self.speak("I don't know how to open that application.")
    
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
if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    speech_engine = SpeechEngine()
    recognizer = VoiceRecognition(gui)
    utils = Utility(speech_engine, recognizer)

    # Example usage
    utils.speak("Utility functions are ready.")
    # utils.calC()  # Example for calculator function
    # utils.press("enter", 3)  # Example for press function
    # utils.bluetooth()  # Example for Bluetooth toggle
    # utils.hotspot()  # Example for hotspot toggle
    # utils.screenshot()  # Example for hotspot toggle
    utils.snG()  # Example for hotspot toggle
    # print(("second".isdigit()))



