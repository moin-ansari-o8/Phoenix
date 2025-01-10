import tkinter as tk
from tkinter import ttk
import time
from threading import Thread

class CustomNotification:
    def __init__(self, title="Notification", message="This is a custom notification"):
        self.title = title
        self.message = message
        self.duration = 5  # Duration in seconds

    def show_notification(self):
        # Create a new Tkinter window
        self.root = tk.Tk()
        self.root.title(self.title)

        # Make the window borderless
        self.root.overrideredirect(True)

        # Get screen dimensions to position the notification
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Define the size and position of the notification
        window_width = 300
        window_height = 100
        x = screen_width - window_width - 10
        y = screen_height - window_height - 50

        # Position the window
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Add a frame for styling
        frame = ttk.Frame(self.root, relief="raised", borderwidth=2)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Add title and message
        title_label = ttk.Label(frame, text=self.title, font=("Helvetica", 14, "bold"))
        title_label.pack(pady=(10, 5))
        message_label = ttk.Label(frame, text=self.message, font=("Helvetica", 10))
        message_label.pack()

        # Add a close button
        close_button = ttk.Button(frame, text="Close", command=self.close_notification)
        close_button.pack(pady=(5, 10))

        # Start a timer to automatically close the notification
        self.auto_close_timer()

        # Run the Tkinter main loop
        self.root.mainloop()

    def auto_close_timer(self):
        def timer():
            time.sleep(self.duration)
            self.close_notification()

        # Run the timer in a separate thread
        Thread(target=timer, daemon=True).start()

    def close_notification(self):
        self.root.destroy()


# Example usage
if __name__ == "__main__":
    # Create and display the notification
    notification = CustomNotification(
        title="PHOENIX",
        message="Your timer is up! Time to take action."
    )
    notification.show_notification()
