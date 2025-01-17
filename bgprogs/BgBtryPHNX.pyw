import psutil
import sys
import os
from time import sleep

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from HelperPHNX import SpeechEngine


class BatteryMonitor:
    def __init__(self):
        self.last_plugged_state = None
        self.triggered_plugged = {75: False, 100: False, 50: False, 90: False}
        self.triggered_unplugged = {
            85: False,
            50: False,
            35: False,
            30: False,
            25: False,
            70: False,
        }
        self.se = SpeechEngine()

    def get_battery_status(self):
        battery = psutil.sensors_battery()
        return battery.percent, battery.power_plugged

    def speak_battery_status(self, plugged, percentage):
        status = "plugged in" if plugged else "running on battery power"
        self.se.speak(f"Device is {status}. And it is {percentage} percent charged.")

    def reset_triggers(self, plugged):
        """Reset triggers based on plugged/unplugged status."""
        if plugged:
            self.triggered_plugged = {key: False for key in self.triggered_plugged}
        else:
            self.triggered_unplugged = {key: False for key in self.triggered_unplugged}

    def check_triggers(self, percentage, plugged):
        if plugged:
            self.handle_plugged_in(percentage)
        else:
            self.handle_unplugged(percentage)

    def handle_plugged_in(self, percentage):
        triggers = self.triggered_plugged

        if percentage >= 50:
            if percentage == 75 and not triggers[75]:
                self.trigger_event(
                    "Sir, the device is 75 percent charged.", 75, triggers
                )
            elif percentage == 100 and not triggers[100]:
                self.trigger_event(
                    "Sir, the device is fully charged! You should unplug the charger.",
                    100,
                    triggers,
                )
            elif percentage == 50 and not triggers[50]:
                self.trigger_event(
                    "Sir, the device is 50 percent charged.", 50, triggers
                )
            elif percentage == 90 and not triggers[90]:
                self.trigger_event(
                    "Sir, the device is 90 percent charged.", 90, triggers
                )

    def handle_unplugged(self, percentage):
        triggers = self.triggered_unplugged

        if percentage <= 85:
            if percentage == 85 and not triggers[85]:
                self.trigger_event(
                    "Sir, the device has 85 percent charge left.", 85, triggers
                )
            elif percentage == 50 and not triggers[50]:
                self.trigger_event(
                    "Sir, the device has used half of its full charge.", 50, triggers
                )
            elif percentage == 35 and not triggers[35]:
                self.trigger_event(
                    "Plug in the charger, sir. Only 35 percent battery power left.",
                    35,
                    triggers,
                )
            elif percentage == 30 and not triggers[30]:
                self.trigger_event(
                    "Plug in the charger, sir. Only 30 percent battery power left.",
                    30,
                    triggers,
                )
            elif percentage == 25 and not triggers[25]:
                self.trigger_event(
                    "Plug in the charger, sir. Only 25 percent battery power left.",
                    25,
                    triggers,
                )
            elif percentage == 70 and not triggers[70]:
                self.trigger_event(
                    "Sir, the device has 70 percent charge left.", 70, triggers
                )

    def trigger_event(self, message, percentage, triggers):
        sleep(5)
        self.se.speak(message)
        triggers[percentage] = True
        sleep(600)  # Sleep for 10 minutes to avoid frequent triggers

    def monitor(self):
        try:
            while True:
                percentage, plugged = self.get_battery_status()

                if plugged != self.last_plugged_state:
                    self.speak_battery_status(plugged, percentage)
                    self.reset_triggers(plugged)
                    self.last_plugged_state = plugged

                self.check_triggers(percentage, plugged)
                sleep(10)  # Sleep for 1 minute before checking again
        except Exception as e:
            self.se.speak(
                f"An error occurred: {e}. Restarting the battery management program."
            )
            sleep(5)
            self.monitor()


if __name__ == "__main__":
    sleep(5)  # Initial delay

    monitor = BatteryMonitor()
    monitor.monitor()
