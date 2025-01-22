import os
import sys
import threading
from time import sleep
import random
import pyttsx3
import speech_recognition as sr
import tkinter as tk
from PIL import Image, ImageTk
from time import sleep
from colorama import Fore


class SpeechEngine:

    def __init__(self):
        self.engine = pyttsx3.init("sapi5")
        voices = self.engine.getProperty("voices")
        self.engine.setProperty("voice", voices[1].id)
        self.engine.setProperty("rate", 174)
        # self.engine.setProperty("volume", 1.0)
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
            # "boss",
            # "captain",
            # "commander",
            # "my lord",
            # "your highness",
            # "your majesty",
            # "my liege",
            # "your grace",
            "sir",
            "boss",
            "master",
            "sensei",
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
        self.listen_img_path = os.path.join(
            os.path.dirname(__file__), "..", "assets", "img", "green.png"
        )
        self.recognize_img_path = os.path.join(
            os.path.dirname(__file__), "..", "assets", "img", "red.png"
        )
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
            audio = self.recognizer.listen(source, 0, 6)
        try:
            self.recognizer.pause_threshold = 1
            self.gui.show_recognize_image()
            print("<<<", end="\r")
            query = self.recognizer.recognize_google(audio, language="en-in")
            # print(f"# : {query}\n")
        except Exception as e:
            print("<!>", end="\r")
            self.gui.hide_listen_image()
            return ""
        return query


"---------------EXTRA----------------"


def music(Utility):
    Utility.intrOmsC()
    Utility.rockMsc(0.5)


if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    recog = VoiceRecognition(gui)
    spk = SpeechEngine()
    # utils = Utility(spk, recog)
    # utils.open_setting()
    # utils.get_window("Code.exe", "HelperPHNX.py")
    spk.speak("oohoom..!")
    # recog.take_command()
    # music(recog)
    # print("oj")
    # opn = OpenAppHandler(recog)
    # utils.speak("hello, sir")
    # utils.desKtoP(2)
    # utils.open_brave()
