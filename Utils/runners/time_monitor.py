import datetime
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

EventCallback = Optional[Callable[[str, Dict], None]]


@dataclass
class TimeMonitorConfig:
    loop_interval_seconds: float = 1.0
    startup_water_delay_seconds: float = 10.0
    periodic_project_check_hours: int = 6


class TimeMonitorService:
    """Professionalized time monitor (renamed from BgTmPHNX)."""

    def __init__(
        self,
        config: TimeMonitorConfig | None = None,
        speech_engine=None,
        event_callback: EventCallback = None,
    ):
        self.config = config or TimeMonitorConfig()
        self.se = speech_engine
        self.event_callback = event_callback
        self.last_check_hour = None
        self._pending_speech: list[str] = []

    def _emit(self, event_type: str, payload: Dict):
        if self.event_callback:
            self.event_callback("time_monitor", {"type": event_type, **payload})

    def _drain_pending_speech(self, utility):
        while self._pending_speech:
            next_message = self._pending_speech[0]
            spoken = False
            try:
                spoken = utility.speak(next_message)
            except Exception as e:
                self._emit("error", {"message": f"speech delivery failed: {e}"})
                break

            if spoken is False:
                break

            self._pending_speech.pop(0)

    def _safe_speak(self, utility, message: str):
        self._emit("speech", {"message": message})
        self._pending_speech.append(message)
        self._drain_pending_speech(utility)

    def _startup_reminders(self, utility, personal_manager):
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        self._safe_speak(utility, f"{utility.tM()} {current_time}.")

        summary = personal_manager.get_startup_summary()
        message = personal_manager.format_startup_message(summary)
        if message:
            self._safe_speak(utility, message)

        time.sleep(self.config.startup_water_delay_seconds)
        self._safe_speak(utility, utility.wtR())

    def _periodic_checks(
        self,
        utility,
        personal_manager,
        current_hour: int,
    ):
        if (
            current_hour % self.config.periodic_project_check_hours == 0
            and self.last_check_hour != current_hour
        ):
            self.last_check_hour = current_hour
            stale = personal_manager.projects.check_stale_projects(
                personal_manager.settings.get("reminder_threshold_days", 3)
            )
            if stale:
                project = stale[0]
                self._safe_speak(
                    utility,
                    f"Sir, no update on {project['name']} project in {project['days_since_update']} days.",
                )

    def run(self, stop_event):
        self._emit("status", {"message": "starting"})

        root = None
        try:
            import tkinter as tk
            from Utils.limbs.action_utilities import Utility
            from Utils.limbs.assistant_io import (
                SpeechEngine,
                VoiceAssistantGUI,
                VoiceRecognition,
            )
            from Utils.limbs.personal_manager import PersonalManager
            from Utils.limbs.time_handlers import AlarmHandle
            from Utils.limbs.time_runner import (
                AlarmManager,
                HandleTimeBasedFunctions,
                ReminderManager,
                ScheduleManager,
                TimerManager,
            )

            root = tk.Tk()
            root.withdraw()
            gui = VoiceAssistantGUI(root)
            recognition = VoiceRecognition(gui)
            speech = self.se or SpeechEngine()
            self.se = speech
            utility = Utility(spk=speech, reco=recognition)

            time_based_all = HandleTimeBasedFunctions(
                utility=utility,
                timer_manager=TimerManager(speech),
                alarm_manager=AlarmManager(speech, alarm_handle=AlarmHandle(utility)),
                schedule_manager=ScheduleManager(speech),
                reminder_manager=ReminderManager(utility),
            )
            personal_manager = PersonalManager()

            try:
                time_based_all.clear_time_data()
            except Exception as e:
                self._emit("error", {"message": f"clear_time_data failed: {e}"})

            self._startup_reminders(utility, personal_manager)
            previous_hour = datetime.datetime.now().hour

            while not stop_event.is_set():
                try:
                    self._drain_pending_speech(utility)
                    time_based_all.main_time()
                    previous_hour = time_based_all.spk_time(previous_hour)
                    current_hour = datetime.datetime.now().hour
                    self._periodic_checks(utility, personal_manager, current_hour)
                    self._emit("status", {"message": "heartbeat", "hour": current_hour})
                except Exception as e:
                    self._emit("error", {"message": str(e)})

                stop_event.wait(self.config.loop_interval_seconds)

        except Exception as e:
            self._emit("error", {"message": f"critical start failure: {e}"})
        finally:
            if root:
                try:
                    root.destroy()
                except Exception:
                    pass
            self._emit("status", {"message": "stopped"})
