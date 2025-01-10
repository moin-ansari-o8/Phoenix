import time
from plyer import notification
import re
import tkinter as tk
import tkinter.messagebox
# from ..HelperPhoenix import VoiceAssistantGUI,SpeechEngine,VoiceRecognition,Utility
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from HelperPhoenix import VoiceAssistantGUI, SpeechEngine, VoiceRecognition, Utility

class TimerUtility:
    def __init__(self,speech_engine, voice_recognition,sleep_time=1):
        self.speech_engine = speech_engine
        self.voice_recognition = voice_recognition
        self.sleep_time = sleep_time

    def speak(self, message):
        self.speech_engine.speak(message)

    def take_command(self):
        return self.voice_recognition.take_command()

    def set_timer(self):
        """
        Sets a timer based on user input.
        Notifies the user when the timer ends.
        """
        try:
            # Prompt user to enter timer duration
            self.speak("For how long should I set the timer? (e.g., 1 hour and 30 minutes, or 90 minutes)")
            time_input = self.take_command().lower()

            # Parse input to extract hours and minutes
            hours, minutes = self._parse_timer_duration(time_input)
            
            if hours is None and minutes is None:
                self.speak("Sorry, I couldn't understand the duration. Please try again.")
                return

            # Convert to total seconds
            total_seconds = hours * 3600 + minutes * 60

            # Confirm the timer
            self.speak(f"Setting a timer for {hours} hour(s) and {minutes} minute(s).")
            print(f"Timer set for {hours} hour(s) and {minutes} minute(s).")

            # Countdown timer
            while total_seconds:
                mins, secs = divmod(total_seconds, 60)
                timer = f'{mins:02d}:{secs:02d}'
                print(f"Time left: {timer}", end="\r")  # Dynamic countdown
                time.sleep(1)
                total_seconds -= 1
                

            # Notify when timer ends
            self.speak("Time's up!")
            tkinter.messagebox.showinfo("PHOENIX.",  "Hi I  'm your message") 
        except Exception as e:
            self.speak(f"An error occurred while setting the timer: {str(e)}")

    def _parse_timer_duration(self, time_str):
        """
        Parses the timer duration from the input string.
        Returns the duration in hours and minutes.
        """
        try:
            # Regex pattern to match hours and minutes
            duration_pattern = re.compile(
                r'(?:(\d+)\s*hour(?:s)?)?\s*(?:(\d+)\s*minute(?:s)?)?', re.IGNORECASE
            )
            match = duration_pattern.search(time_str)

            if match:
                hours = int(match.group(1)) if match.group(1) else 0
                minutes = int(match.group(2)) if match.group(2) else 0
                return hours, minutes

            return None, None
        except Exception as e:
            self.speak("I couldn't parse the time duration. Please try again.")
            return None, None


if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    speech_engine = SpeechEngine()
    recognizer = VoiceRecognition(gui)
    timer = TimerUtility(speech_engine, recognizer)
    timer.set_timer()