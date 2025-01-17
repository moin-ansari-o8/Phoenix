import pyttsx3
import random
import speech_recognition as sr
import tkinter as tk
from PIL import Image, ImageTk
import os

engine = pyttsx3.init("sapi5")
voices = engine.getProperty("voices")
engine.setProperty("voice", voices[1].id)
engine.setProperty("rate", 174)
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-alpha", 0.9)
root.attributes("-topmost", True)
if root.tk.call("tk", "windowingsystem") == "win32":
    root.attributes("-topmost", 1)
elif root.tk.call("tk", "windowingsystem") == "x11":
    root.attributes("-type", "dock")
elif root.tk.call("tk", "windowingsystem") == "aqua":
    root.call("::tk::unsupported::MacWindowStyle", "style", root._w, "help", "none")
root.wm_attributes("-transparentcolor", "white")
mic_label = tk.Label(root, bg="white")
mic_label.pack()
current_dir = os.path.dirname(__file__)
listen_img = os.path.join(current_dir, "assets", "img", "green.png")
recognize_img = os.path.join(current_dir, "assets", "img", "red.png")
max_width = max(4, 4)
max_height = max(30, 30)
x_offset = root.winfo_screenwidth() - max_width
y_offset = root.winfo_screenheight() - max_height
root.geometry(f"{max_width}x{max_height}+{x_offset}+{y_offset}")


def speak(audio):
    replacements = ["boss", "my lord"]
    for punctuation in ["", "?", "!", ".", " "]:
        if f"sir{punctuation}" in audio:
            replacement = random.choice(replacements)
            audio = audio.replace(f"sir{punctuation}", f"{replacement}{punctuation}")
            break
    engine.say(audio)
    print(f"$ : {audio}")
    engine.runAndWait()


def takeCommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        show_listen_image()
        print(">>>")
        audio = r.listen(source, 0, 6)
    try:
        # r.pause_threshold = 1
        show_recognize_image()
        print("<<<")
        query = r.recognize_google(audio, language="en-in")
        print(f"# : {query}\n")
    except Exception as e:
        print("<!>")
        hide_listen_image()
        return ""
    return query


def show_listen_image():
    mic_label.config(image=None)
    mic_img = Image.open(listen_img).convert("RGBA")
    mic_img = mic_img.resize((40, 40), Image.LANCZOS)
    mic_img = ImageTk.PhotoImage(mic_img)
    mic_label.config(image=mic_img)
    mic_label.image = mic_img
    root.update()


def hide_listen_image():
    mic_label.config(image=None)


def show_recognize_image():
    mic_label.config(image=None)
    recognize_img = Image.open(recognize_img).convert("RGBA")
    recognize_img = recognize_img.resize((40, 40), Image.LANCZOS)
    recognize_img = ImageTk.PhotoImage(recognize_img)
    mic_label.config(image=recognize_img)
    mic_label.image = recognize_img
    root.update()


def hide_recognize_image():
    mic_label.config(image=None)


if __name__ == "__main__":
    # speak("Let me setup your desktops... until then... sit back and enjoy the music!")
    while True:
        h = takeCommand().lower()
        if h:
            print(h)
    # speak("hehehehe, u r funny!")
    # speak("hihihi, u r so funny!")
    # speak("hahahah, u r so funny!")
