from core.config import AppConfig
import queue
import sys
import threading
import time
import os
from datetime import datetime
import msvcrt

from rich.console import Console
from rich.text import Text
from rich.theme import Theme

from core.config import AppConfig

from utils.runners.manager import RuntimeConfig, PhoenixRuntimeManager
from utils.runners.battery_monitor import BatteryMonitorConfig
from utils.runners.time_monitor import TimeMonitorConfig
from utils.runners.voice_processor import VoiceProcessorConfig


import pythoncom


class GlobalSpeechWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="global-speech-worker")
        self.q = queue.Queue()
        self.engine = None
        self._current_speech = ""

    def run(self):
        import utils.services.console_ui

        utils.services.console_ui.phoenix_said = lambda x: None

        from utils.services.assistant_io import SpeechEngine

        try:
            pythoncom.CoInitialize()
        except Exception:
            pass

        try:
            self.engine = SpeechEngine()
        except Exception:
            return

        while True:
            item = self.q.get()
            if item is None:
                break

            text, event, tui = item

            if tui:
                tui.log_chat("Phoenix", text)

            try:
                self._current_speech = text
                self.engine.speak(text)
            except Exception:
                pass
            finally:
                self._current_speech = ""
                event.set()
                self.q.task_done()


class ProxySpeechEngine:
    """Proxy engine that defers to global worker to ensure sequential voice."""

    def __init__(self, worker: GlobalSpeechWorker, tui_manager=None):
        self.worker = worker
        self.tui = tui_manager

    def speak(self, text, speed=174, **kwargs):
        # Block until the text finishes speaking to prevent skipping!
        event = threading.Event()
        self.worker.q.put((text, event, self.tui))
        event.wait()
        return True


RUNTIME_CONFIG = RuntimeConfig(
    battery=BatteryMonitorConfig(
        initial_delay_seconds=5.0,
        check_interval_seconds=10.0,
        trigger_cooldown_seconds=600.0,
    ),
    time=TimeMonitorConfig(
        loop_interval_seconds=1.0,
        startup_water_delay_seconds=10.0,
        periodic_project_check_hours=6,
    ),
    voice=VoiceProcessorConfig(
        auto_restart=True,
        restart_delay_seconds=2.0,
    ),
)


class AdvancedTUIManager(PhoenixRuntimeManager):
    """
    Advanced CLI interface that mimics modern AI CLI tools (like Gemini/Claude CLI).
    Minimal boilerplate, clean chat output, and a single animated status line.
    """

    def __init__(self, config):
        super().__init__(config=config)
        self.theme = Theme(
            {
                "phoenix": "bold bright_blue",
                "user": "bold red",
                "time": "dim bright_black",
            }
        )
        self.console = Console(theme=self.theme)

        self.speech_worker = GlobalSpeechWorker()
        self.speech_worker.start()

        self.shared_speech_engine = ProxySpeechEngine(self.speech_worker, self)
        self.battery_service.se = self.shared_speech_engine
        self.time_service.se = self.shared_speech_engine

        if AppConfig.current_mode == "text" and hasattr(self, "voice_service"):
            if hasattr(self.voice_service, "spk"):
                self.voice_service.spk = self.shared_speech_engine
                if hasattr(self.voice_service, "utility"):
                    self.voice_service.utility.spk = self.shared_speech_engine

        self._current_status = f"{AppConfig.name} Runtime Online"

    def stop_all(self):
        self.speech_worker.q.put(None)
        super().stop_all()

    def _render_status(self):
        # Clears the current line and rewrites the status
        sys.stdout.write(f"\r\033[2K{self._current_status}")
        sys.stdout.flush()

    def _set_idle_status(self):
        from core.config import AppConfig

        if AppConfig.current_mode == "text":
            pass  # Keep it at whatever text was typed by user
        elif self._current_status != "Processing...":
            self._set_status("Listening...")

    def _set_status(self, status: str):
        with self._ui_lock:
            if status == self._current_status:
                return
            self._current_status = status
            self._render_status()

    def log_chat(self, speaker, message, is_ignored=False):
        with self._ui_lock:
            # Clear status line
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()

            timestamp = datetime.now().strftime("%H:%M:%S")
            time_txt = Text(f"[{timestamp}] ", style="time")

            if is_ignored:
                speaker_txt = Text("[Heard noise/speech]: ", style="yellow")
                msg_txt = Text(message, style="yellow")
            elif speaker == "You":
                user_name = getattr(AppConfig, "user_name", "User")
                speaker_txt = Text(f"{user_name}: ", style="user")
                msg_txt = Text(message, style="white")
            else:
                speaker_txt = Text(AppConfig.name + ": ", style="phoenix")
                msg_txt = Text(message, style="bright_white")

            final_text = time_txt + speaker_txt + msg_txt
            self.console.print(final_text)

            # Re-render status
            self._render_status()

    def run_forever(self):
        # Start background threads
        self._print_feed = lambda x: None
        self._print_startup_logo = lambda: None

        self.start_all()

        # Purely text mode assistant instantiation
        self.text_assistant = None
        if AppConfig.current_mode == "text":
            from utils.services.action_utilities import (
                Utility,
                OpenAppHandler,
                CloseAppHandler,
            )
            from utils.services.time_handlers import (
                TimerHandle,
                AlarmHandle,
                ReminderHandle,
                ScheduleHandle,
            )
            from utils.services.command_processor import PhoenixAssistant

            # Use the shared speech engine in text mode
            utility = Utility(spk=self.shared_speech_engine, reco=None)
            self.text_assistant = PhoenixAssistant(
                utility=utility,
                open_handler=OpenAppHandler(utility),
                close_handler=CloseAppHandler(utility),
                timer_handle=TimerHandle(utility),
                alarm_handle=AlarmHandle(utility),
                schedule_handle=ScheduleHandle(utility),
                reminder_handle=ReminderHandle(utility),
            )

        # Give UI empty space
        os.system("cls" if os.name == "nt" else "clear")

        self.console.print(
            "\n[bold dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
        )
        self.console.print(
            f" [bold magenta]{AppConfig.name} AI Assistant[/]  [dim]v2.0[/]"
        )
        self.console.print(
            "[bold dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n"
        )

        self._set_idle_status()

        if AppConfig.current_mode == "text":
            self._set_status("[Text Mode] You: ")

        try:
            text_buffer = ""
            while not self.stop_event.is_set():
                if (
                    AppConfig.current_mode == "text"
                    and self._current_status != "Processing..."
                ):
                    if msvcrt.kbhit():
                        c = msvcrt.getwch()
                        if c in ("\r", "\n"):
                            cmd = text_buffer.strip()
                            text_buffer = ""
                            if cmd:
                                self.log_chat("You", cmd)
                                self._set_status("Processing...")

                                # Execute async
                                def ex(t):
                                    try:
                                        self.text_assistant.main(t)
                                    except Exception as e:
                                        self.log_chat("Phoenix", f"Error: {e}")
                                    self._set_status("[Text Mode] You: ")

                                threading.Thread(
                                    target=ex, args=(cmd,), daemon=True
                                ).start()
                        elif c == "\x08":  # backspace
                            text_buffer = text_buffer[:-1]
                            self._set_status(f"[Text Mode] You: {text_buffer}")
                        else:
                            text_buffer += c
                            self._set_status(f"[Text Mode] You: {text_buffer}")

                try:
                    event = self.events.get(timeout=0.05)
                    source = event.get("source")
                    event_type = event.get("type")
                    message = event.get("message") or event.get("line", "")

                    if source == "voice_processor" and event_type == "log":
                        clean = message.strip()
                        if (
                            not clean
                            or "DEBUG" in clean
                            or "---" in clean
                            or "|" in clean
                        ):
                            continue

                        if clean.startswith("[VOICE_STATE]"):
                            state = clean.removeprefix("[VOICE_STATE]").strip().lower()
                            if state == "listening":
                                self._set_idle_status()
                            elif state == "processing":
                                self._set_status("Processing...")
                            elif state == "detected":
                                pass
                            continue

                        if clean.startswith("[HEARD]"):
                            heard = clean.removeprefix("[HEARD]").strip()
                            if heard and heard != "<empty>":
                                self.log_chat("You", heard)
                            self._set_idle_status()
                            continue

                        if clean.startswith("[IGNORED_HEARD]"):
                            heard = clean.removeprefix("[IGNORED_HEARD]").strip()
                            if heard and heard != "<empty>":
                                self.log_chat("You", heard, is_ignored=True)
                            self._set_idle_status()
                            continue

                        if "Phoenix [" in clean:
                            try:
                                msg = clean.split("]: ", 1)[1]
                            except IndexError:
                                msg = clean.split("Phoenix")[1].strip()
                            # Clean up ANSI and tags if any
                            if msg.startswith("["):
                                try:
                                    msg = msg.split("]: ", 1)[1]
                                except:
                                    pass

                            self.log_chat("Phoenix", msg)
                            self._set_idle_status()
                            continue

                        # Ignore other random print outputs from VoiceProcessor
                        continue

                except queue.Empty:
                    pass
        except KeyboardInterrupt:
            with self._ui_lock:
                sys.stdout.write("\r\033[2K")
                sys.stdout.flush()
                self.console.print("[dim]Phoenix shutting down...[/]")
        finally:
            self.stop_all()


def main():
    manager = AdvancedTUIManager(config=RUNTIME_CONFIG)
    manager.run_forever()


if __name__ == "__main__":
    main()
