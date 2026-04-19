import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

EventCallback = Optional[Callable[[str, Dict], None]]


@dataclass
class BatteryMonitorConfig:
    initial_delay_seconds: float = 5.0
    check_interval_seconds: float = 10.0
    trigger_cooldown_seconds: float = 600.0
    charge_thresholds_plugged: tuple = (50, 75, 90, 100)
    charge_thresholds_unplugged: tuple = (85, 70, 50, 35, 30, 25)


class BatteryMonitorService:
    """Professionalized battery background monitor (renamed from BgBtryPHNX)."""

    def __init__(
        self,
        config: BatteryMonitorConfig | None = None,
        speech_engine=None,
        event_callback: EventCallback = None,
    ):
        self.config = config or BatteryMonitorConfig()
        self.se = speech_engine
        self.event_callback = event_callback
        self._pending_speech: list[str] = []

        self.last_plugged_state = None
        self.triggered_plugged = {
            v: False for v in self.config.charge_thresholds_plugged
        }
        self.triggered_unplugged = {
            v: False for v in self.config.charge_thresholds_unplugged
        }

    def _emit(self, event_type: str, payload: Dict):
        if self.event_callback:
            self.event_callback("battery_monitor", {"type": event_type, **payload})

    def _drain_pending_speech(self):
        if not self.se:
            return

        while self._pending_speech:
            next_message = self._pending_speech[0]
            spoken = False

            try:
                spoken = self.se.speak(next_message)
            except Exception as e:
                self._emit("error", {"message": f"speech delivery failed: {e}"})
                break

            if spoken is False:
                break

            self._pending_speech.pop(0)

    def _speak(self, message: str):
        self._emit("speech", {"message": message})
        self._pending_speech.append(message)
        self._drain_pending_speech()

    def get_battery_status(self):
        import psutil

        battery = psutil.sensors_battery()
        if battery is None:
            raise RuntimeError("Battery information is not available on this system.")
        return battery.percent, battery.power_plugged

    def speak_battery_status(self, plugged: bool, percentage: int):
        status = "plugged in" if plugged else "running on battery power"
        self._speak(f"Device is {status}. And it is {percentage} percent charged.")

    def reset_triggers(self, plugged: bool):
        if plugged:
            self.triggered_plugged = {key: False for key in self.triggered_plugged}
        else:
            self.triggered_unplugged = {key: False for key in self.triggered_unplugged}

    def _trigger_event(self, message: str, percentage: int, triggers: Dict[int, bool]):
        time.sleep(5)
        self._speak(message)
        triggers[percentage] = True
        time.sleep(self.config.trigger_cooldown_seconds)

    def handle_plugged_in(self, percentage: int):
        triggers = self.triggered_plugged
        checks = {
            50: "Sir, the device is 50 percent charged.",
            75: "Sir, the device is 75 percent charged.",
            90: "Sir, the device is 90 percent charged.",
            100: "Sir, the device is fully charged! You should unplug the charger.",
        }
        for level, message in checks.items():
            if percentage == level and not triggers.get(level, False):
                self._trigger_event(message, level, triggers)
                break

    def handle_unplugged(self, percentage: int):
        triggers = self.triggered_unplugged
        checks = {
            85: "Sir, the device has 85 percent charge left.",
            70: "Sir, the device has 70 percent charge left.",
            50: "Sir, the device has used half of its full charge.",
            35: "Plug in the charger, sir. Only 35 percent battery power left.",
            30: "Plug in the charger, sir. Only 30 percent battery power left.",
            25: "Plug in the charger, sir. Only 25 percent battery power left.",
        }
        for level, message in checks.items():
            if percentage == level and not triggers.get(level, False):
                self._trigger_event(message, level, triggers)
                break

    def run(self, stop_event):
        self._emit("status", {"message": "starting"})
        if self.se is None:
            try:
                from utils.services.assistant_io import SpeechEngine

                self.se = SpeechEngine()
            except Exception as e:
                self._emit("error", {"message": f"speech engine init failed: {e}"})
        if self.config.initial_delay_seconds > 0:
            stop_event.wait(self.config.initial_delay_seconds)

        while not stop_event.is_set():
            try:
                self._drain_pending_speech()
                percentage, plugged = self.get_battery_status()
                self._emit(
                    "status",
                    {"message": "heartbeat", "percent": percentage, "plugged": plugged},
                )

                if plugged != self.last_plugged_state:
                    self.speak_battery_status(plugged, percentage)
                    self.reset_triggers(plugged)
                    self.last_plugged_state = plugged

                if plugged:
                    self.handle_plugged_in(percentage)
                else:
                    self.handle_unplugged(percentage)

            except Exception as e:
                self._emit("error", {"message": str(e)})
                self._speak(
                    f"An error occurred: {e}. Restarting the battery management program."
                )
                stop_event.wait(5)

            stop_event.wait(self.config.check_interval_seconds)

        self._emit("status", {"message": "stopped"})
