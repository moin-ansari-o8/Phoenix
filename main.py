from core.config import AppConfig
import queue
import sys
import threading
import time
import os
from datetime import datetime

from rich.console import Console
from rich.text import Text
from rich.theme import Theme

from utils.background.manager import RuntimeConfig, PhoenixRuntimeManager
from utils.background.battery_monitor import BatteryMonitorConfig
from utils.background.time_monitor import TimeMonitorConfig
from utils.background.voice_processor import VoiceProcessorConfig


import pythoncom


class GlobalSpeechWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="global-speech-worker")
        self.q = queue.Queue()
        self.engine = None
        self._current_speech = ""

    def run(self):
        import utils.helpers.console_ui

        utils.helpers.console_ui.phoenix_said = lambda x: None

        from utils.helpers.assistant_io import SpeechEngine

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

        self._current_status = f"{AppConfig.name} Runtime Online"

    def stop_all(self):
        self.speech_worker.q.put(None)
        super().stop_all()

    def _render_status(self):
        # Clears the current line and rewrites the status
        sys.stdout.write(f"\r\033[2K{self._current_status}")
        sys.stdout.flush()

    def _set_status(self, status: str):
        with self._ui_lock:
            if status == self._current_status:
                return
            self._current_status = status
            self._render_status()

    def log_chat(self, speaker, message):
        with self._ui_lock:
            # Clear status line
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()

            timestamp = datetime.now().strftime("%H:%M:%S")
            time_txt = Text(f"[{timestamp}] ", style="time")

            if speaker == "You":
                speaker_txt = Text("You: ", style="user")
                msg_txt = Text(message, style="white")
            else:
                speaker_txt = Text(AppConfig.name + ": ",  style="phoenix")
                msg_txt = Text(message, style="bright_white")

            final_text = time_txt + speaker_txt + msg_txt
            self.console.print(final_text)

            # Re-render status
            self._render_status()

    def run_forever(self):
        # Start background threads
        # We need to disable the noisy logging from parent:
        self._print_feed = lambda x: None  # No more raw prints
        self._print_startup_logo = lambda: None  # No ascii art

        self.start_all()

        # Give UI empty space
        os.system("cls" if os.name == "nt" else "clear")

        self.console.print(
            "\n[bold dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]"
        )
        self.console.print(f" [bold magenta]{AppConfig.name} AI Assistant[/]  [dim]v2.0[/]")
        self.console.print(
            "[bold dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n"
        )

        self._set_status("Listening...")

        try:
            while not self.stop_event.is_set():
                try:
                    event = self.events.get(timeout=0.25)
                    source = event.get("source")
                    event_type = event.get("type")
                    message = event.get("message") or event.get("line", "")

                    # DEBUG SYSTEM: Print all events to terminal
                    # sys.stdout.write("\r\033[2K")
                    # msg_preview = message.strip() if message else str(event)
                    # self.console.print(
                    #     f"[dim yellow][debug] {source} | {event_type} | {msg_preview}[/]"
                    # )
                    # self._render_status()

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
                                # Don't overwrite processing with listening immediately
                                if self._current_status != "Processing...":
                                    self._set_status("Listening...")
                            elif state == "processing":
                                self._set_status("Processing...")
                            elif state == "detected":
                                pass
                            continue

                        if clean.startswith("[HEARD]"):
                            heard = clean.removeprefix("[HEARD]").strip()
                            if heard and heard != "<empty>":
                                self.log_chat("You", heard)
                            self._set_status("Listening...")
                            continue

                        if clean.startswith("[IGNORED]") or clean.startswith(
                            "[INTENT]"
                        ):
                            self._set_status("Listening...")
                            continue

                        if clean.startswith("[PROCESSING]"):
                            self._set_status("Processing...")
                            continue

                        if clean.startswith("Phoenix"):
                            try:
                                msg = clean.split("]: ", 1)[1]
                            except IndexError:
                                msg = clean.replace("Phoenix", "").strip()
                            self.log_chat("Phoenix", msg)
                            self._set_status("Listening...")
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
