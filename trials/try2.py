from plyer import notification
import time
# import everything from tkinter module 
from tkinter import *
  
# import messagebox from tkinter module 
import tkinter.messagebox 
class TimerUtility:
    def set_timer(self, duration_minutes, message="Time's up!"):
        """Sets a timer and shows a notification when time is up."""
        try:
            print(f"Timer set for {duration_minutes} minute(s).")
            time.sleep(duration_minutes * 60)  # Wait for the specified time
            tkinter.messagebox.showinfo("PHOENIX.",  "Hi I  'm your message") 
        except Exception as e:
            print(f"An error occurred: {e}")

# Example Usage
if __name__ == "__main__":
    timer = TimerUtility()
    timer.set_timer(0.01, "Break's over!")  # Set a timer for 0.1 minute (6 seconds)
