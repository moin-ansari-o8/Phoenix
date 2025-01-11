import sys
import random
import pyttsx3
import speech_recognition as sr
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QTextEdit
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

# --- Speech Engine ---
class SpeechEngine:
    def __init__(self):
        self.engine = pyttsx3.init('sapi5')
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[1].id)
        self.engine.setProperty('rate', 174)

    def speak(self, audio):
        """Replace 'sir' with random respectful term and speak the audio."""
        replacements = ["boss", "my lord"]
        for punctuation in ["", "?", "!", ".", " "] :
            if f"sir{punctuation}" in audio:
                replacement = random.choice(replacements)
                audio = audio.replace(f"sir{punctuation}", f"{replacement}{punctuation}") 
                break
        self.engine.say(audio)
        # Call the update_output method to display the audio output in the GUI
        VoiceAssistantGUI.update_output(f"$ : {audio}")
        self.engine.runAndWait()

# --- Voice Recognition (in a separate thread) ---
class VoiceRecognition(QThread):
    # Signal to send recognized text back to the main thread
    recognized_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = False  # Flag to check if the thread is running

    def run(self):
        """Run speech recognition in the background."""
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()

        self.is_running = True

        while self.is_running:
            VoiceAssistantGUI.update_output(">>>")  # Listening
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source)

            try:
                VoiceAssistantGUI.update_output("<<<")  # Recognizing
                command = recognizer.recognize_google(audio)
                self.recognized_signal.emit(command)
            except sr.UnknownValueError:
                VoiceAssistantGUI.update_output("!<>")  # Not understood
                self.recognized_signal.emit("Sorry, I didn't understand that.")
            except sr.RequestError:
                VoiceAssistantGUI.update_output("!<>")  # Not understood
                self.recognized_signal.emit("Unable to connect to the speech service.")

    def stop(self):
        """Stop the thread safely."""
        self.is_running = False
        self.quit()
        self.wait()  # Wait for the thread to finish

# --- Voice Assistant GUI ---
class VoiceAssistantGUI:
    @staticmethod
    def update_output(text):
        """Update the text area with speech recognition or output."""
        if hasattr(VoiceAssistantGUI, 'text_output'):
            VoiceAssistantGUI.text_output.clear()  # Clear previous text
            VoiceAssistantGUI.text_output.append(text)  # Add the current text

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.root = QMainWindow()
        self.root.setWindowTitle("Voice Assistant")
        self.root.setGeometry(100, 100, 400, 400)  # Adjusted window size
        self.root.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.root.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout()

        # Add a text area to show speech recognition output
        self.text_output = QTextEdit(self.root)
        self.text_output.setFont(QFont('Arial', 12))
        self.text_output.setReadOnly(True)
        layout.addWidget(self.text_output)

        # Add a button to start/stop listening
        self.show_button = QPushButton("Start Listening", self.root)
        self.show_button.setFont(QFont('Arial', 12))
        self.show_button.clicked.connect(self.toggle_listening)
        layout.addWidget(self.show_button)

        # Set up the initial layout
        self.central_widget = QWidget(self.root)
        self.central_widget.setLayout(layout)
        self.root.setCentralWidget(self.central_widget)

        self.voice_recognition = None  # Initialize voice recognition to None
        self.speech_engine = SpeechEngine()  # Initialize SpeechEngine

    def toggle_listening(self):
        """Toggle listening state (start/stop)."""
        if self.voice_recognition and self.voice_recognition.is_running:
            # Stop listening
            self.voice_recognition.stop()
            self.show_button.setText("Start Listening")
            VoiceAssistantGUI.update_output("Stopped listening.")
        else:
            # Start listening
            self.voice_recognition = VoiceRecognition()
            self.voice_recognition.recognized_signal.connect(self.update_text_output)
            self.voice_recognition.start()
            self.show_button.setText("Stop Listening")
            VoiceAssistantGUI.update_output("Started listening.")

    def update_text_output(self, text):
        """Update the text area with speech recognition output."""
        self.text_output.append(f"Recognized: {text}")
        self.speech_engine.speak(text)

    def run(self):
        """Start the Qt application."""
        self.root.show()
        sys.exit(self.app.exec_())

# --- Example Usage ---
if __name__ == "__main__":
    gui = VoiceAssistantGUI()  # Create VoiceAssistantGUI instance
    gui.run()  # Start the Qt application
