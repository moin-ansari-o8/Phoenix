import pyttsx3
import random
import speech_recognition as sr
import tkinter as tk
from PIL import Image, ImageTk

class SpeechEngine:
    def __init__(self):
        self.engine = pyttsx3.init('sapi5')
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[1].id)
        self.engine.setProperty('rate', 175)
    
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

class VoiceAssistantGUI:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.9)
        self.root.attributes("-topmost", True)
        self.setup_transparency()

        self.mic_label = tk.Label(self.root, bg='white')
        self.mic_label.pack()

        # Load images for GUI
        self.listen_img = Image.open("C:\\PHNX\\A_MODULES\\faT_funcS\\listenShow2.png")
        self.recognize_img = Image.open("C:\\PHNX\\A_MODULES\\faT_funcS\\recogShow.png")

        # Configure window geometry
        max_width, max_height = 4, 30
        x_offset = self.root.winfo_screenwidth() - max_width
        y_offset = self.root.winfo_screenheight() - max_height
        self.root.geometry(f"{max_width}x{max_height}+{x_offset}+{y_offset}")

    def setup_transparency(self):
        if self.root.tk.call('tk', 'windowingsystem') == 'win32':
            self.root.attributes('-topmost', 1)
        elif self.root.tk.call('tk', 'windowingsystem') == 'x11':
            self.root.attributes('-type', 'dock')
        elif self.root.tk.call('tk', 'windowingsystem') == 'aqua':
            self.root.call('::tk::unsupported::MacWindowStyle', 'style', self.root._w, 'help', 'none')
        self.root.wm_attributes("-transparentcolor", "white")

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

# Main Application
if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    speech_engine = SpeechEngine()
    recognizer = VoiceRecognition(gui)
    # Example Usage
    speech_engine.speak("yoii, what's up?")
    recognizer.take_command()
    root.mainloop()
