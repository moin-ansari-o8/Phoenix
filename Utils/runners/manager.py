import queue
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, List

from .battery_monitor import BatteryMonitorConfig, BatteryMonitorService
from .time_monitor import TimeMonitorConfig, TimeMonitorService
from .voice_processor import VoiceProcessorConfig, VoiceProcessorService


@dataclass
class RuntimeConfig:
    battery: BatteryMonitorConfig = field(default_factory=BatteryMonitorConfig)
    time: TimeMonitorConfig = field(default_factory=TimeMonitorConfig)
    voice: VoiceProcessorConfig = field(default_factory=VoiceProcessorConfig)
    main_loop_sleep_seconds: float = 0.2


class PhoenixRuntimeManager:
    """Main coordinator that runs all background services in threads."""

    def __init__(self, config: RuntimeConfig | None = None):
        self.config = config or RuntimeConfig()
        self.stop_event = threading.Event()
        self.events: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.threads: Dict[str, threading.Thread] = {}
        self._ui_lock = threading.Lock()
        self._live_status = ""
        self._startup_announced: set[str] = set()

        self.state: Dict[str, Any] = {
            "last_event": {},
            "last_speech": {},
            "services": {},
            "flags": {
                "battery_hit": False,
                "time_hit": False,
                "listener_hit": False,
            },
            "hit_counts": {
                "battery": 0,
                "time": 0,
                "listener": 0,
            },
        }
        self._event_handlers: List[Callable[[Dict[str, Any]], None]] = []

        self.shared_speech_engine = None
        try:
            from Utils.limbs.assistant_io import SpeechEngine

            self.shared_speech_engine = SpeechEngine()
        except Exception:
            # Services can still self-initialize speech engines if shared init fails.
            self.shared_speech_engine = None

        self.battery_service = BatteryMonitorService(
            config=self.config.battery,
            speech_engine=self.shared_speech_engine,
            event_callback=self._on_event,
        )
        self.time_service = TimeMonitorService(
            config=self.config.time,
            speech_engine=self.shared_speech_engine,
            event_callback=self._on_event,
        )
        from core.config import AppConfig

        if AppConfig.current_mode == "voice":
            self.voice_service = VoiceProcessorService(
                config=self.config.voice, event_callback=self._on_event
            )
        else:
            self.voice_service = None

    def _print_startup_logo(self):
        logo = (
            "\n"
            "   ____  _   _  ___  _____ _   _ ___ __  __\n"
            "  | |_) | |_| | | | |  _| |  \\| || || |\\/| |\n"
            "  |  __/|  _  | |_| | |___| |\\  || || |  | |\n"
            "  |_|   |_| |_|\\___/|_____|_| \\_|___|_|  |_|\n"
            "\n"
            "               Phoenix Runtime Online\n"
        )
        for line in logo.splitlines():
            if line:
                self._print_feed(line)

    def _render_status(self):
        status = self._live_status or "🎧 Listening..."
        sys.stdout.write(f"\r\033[2K{status}")
        sys.stdout.flush()

    def _set_status(self, status: str):
        with self._ui_lock:
            if status == self._live_status:
                return
            self._live_status = status
            self._render_status()

    def _print_feed(self, line: str):
        with self._ui_lock:
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()
            print(line, flush=True)
            self._render_status()

    def _is_banner_or_noise(self, line: str) -> bool:
        if not line:
            return True
        if line.startswith("[DEBUG]"):
            return True
        if line.startswith("🎤 Voice Engine"):
            return True
        if line.startswith("💻 Loading Whisper"):
            return True
        if line.startswith("✅ Speech recognition ready"):
            return True
        if line.startswith("+") and "---" in line:
            return True
        if line.startswith("| ") and "PHOENIX VOICE ASSISTANT" in line:
            return True
        if line.startswith("| Speak naturally"):
            return True
        return False

    def _handle_voice_log(self, line: str):
        clean = line.strip()
        if self._is_banner_or_noise(clean):
            return

        if clean.startswith("[VOICE_STATE]"):
            state = clean.removeprefix("[VOICE_STATE]").strip().lower()
            if state == "listening":
                self._set_status("🎧 Listening...")
                return
            if state == "detected":
                self._set_status("🎙️  Voice detected...")
                return
            if state == "processing":
                self._set_status("🧠 Processing...")
                return

        if clean.startswith("[HEARD]"):
            heard = clean.removeprefix("[HEARD]").strip()
            if heard and heard != "<empty>":
                self._print_feed(f"👤 You: {heard}")
            self._set_status("🎧 Listening...")
            return

        if clean.startswith("[IGNORED_HEARD]"):
            heard = clean.removeprefix("[IGNORED_HEARD]").strip()
            if heard and heard != "<empty>":
                self._print_feed(f"👤 [Ignored]: {heard}")
            self._set_status("🎧 Listening...")
            return

        if clean.startswith("[PROCESSING]"):
            self._set_status("🧠 Processing...")
            return

        if clean.startswith("[IGNORED]"):
            self._set_status("🎧 Listening...")
            return

        if clean.startswith("[INTENT]"):
            self._set_status("🎧 Listening...")
            return

        if "🎙️  Voice detected" in clean:
            self._set_status("🎙️  Voice detected...")
            return

        if "🧠 Processing" in clean:
            self._set_status("🧠 Processing...")
            return

        if "🎧 Listening" in clean:
            self._set_status("🎧 Listening...")
            return

        if clean.startswith("👤 You "):
            return

        if clean.startswith("🔊 Phoenix "):
            self._print_feed(clean)
            self._set_status("🎧 Listening...")
            return

        if clean.startswith("Playing:") or clean.startswith("Playing a random song:"):
            self._print_feed(f"[voice] {clean}")
            return

        lowered = clean.lower()
        if "traceback" in lowered or "error" in lowered or "critical" in lowered:
            self._print_feed(f"[voice_processor] error: {clean}")

    def _on_event(self, source: str, payload: Dict[str, Any]):
        event = {"source": source, "timestamp": time.time(), **payload}
        self.state["last_event"][source] = event
        if payload.get("type") == "speech":
            self.state["last_speech"][source] = payload.get("message", "")
        if payload.get("type") == "status":
            self.state["services"][source] = payload.get("message")
        if source == "battery_monitor":
            self.state["flags"]["battery_hit"] = True
            self.state["hit_counts"]["battery"] += 1
        elif source == "time_monitor":
            self.state["flags"]["time_hit"] = True
            self.state["hit_counts"]["time"] += 1
        elif source == "voice_processor":
            self.state["flags"]["listener_hit"] = True
            self.state["hit_counts"]["listener"] += 1
        self.events.put(event)
        for handler in list(self._event_handlers):
            try:
                handler(event)
            except Exception:
                pass

    def _start_thread(self, name: str, target):
        thread = threading.Thread(
            target=target, args=(self.stop_event,), name=name, daemon=True
        )
        self.threads[name] = thread
        thread.start()

    def _preload_runtime_dependencies(self):
        """Warm up shared imports once to avoid thread-time partial module init races."""
        modules = [
            "Utils.limbs.assistant_io",
            "Utils.limbs.action_utilities",
            "Utils.limbs.time_handlers",
            "Utils.limbs.time_runner",
            "Utils.limbs.personal_manager",
        ]
        for module_name in modules:
            try:
                __import__(module_name)
            except Exception as e:
                self._on_event(
                    "main",
                    {
                        "type": "error",
                        "message": f"dependency preload failed for {module_name}: {e}",
                    },
                )

    def start_all(self):
        self._preload_runtime_dependencies()
        self._start_thread("battery-monitor-thread", self.battery_service.run)
        self._start_thread("time-monitor-thread", self.time_service.run)
        if self.voice_service:
            self._start_thread("voice-processor-thread", self.voice_service.run)

    def stop_all(self):
        self.stop_event.set()
        for thread in self.threads.values():
            thread.join(timeout=5)

    def snapshot(self) -> Dict[str, Any]:
        return self.state.copy()

    def set_flag(self, flag_name: str, value: bool):
        self.state["flags"][flag_name] = value

    def get_flag(self, flag_name: str) -> bool:
        return bool(self.state["flags"].get(flag_name, False))

    def register_event_handler(self, handler: Callable[[Dict[str, Any]], None]):
        self._event_handlers.append(handler)

    def run_forever(self):
        self._print_startup_logo()
        self.start_all()
        self._set_status("🎧 Listening...")
        try:
            while not self.stop_event.is_set():
                try:
                    event = self.events.get(timeout=self.config.main_loop_sleep_seconds)
                    source = event.get("source")
                    event_type = event.get("type")
                    message = event.get("message") or event.get("line", "")

                    if source == "voice_processor" and event_type == "log":
                        self._handle_voice_log(message)
                        continue

                    if event_type == "status":
                        status_message = event.get("message")

                        if status_message == "heartbeat":
                            continue

                        if status_message == "starting":
                            if source not in self._startup_announced:
                                self._startup_announced.add(source)
                                self._print_feed(f"[{source}] status: starting")
                            continue

                        if status_message == "running":
                            if source == "voice_processor":
                                self._set_status("🎧 Listening...")
                            continue

                        if status_message == "exited":
                            return_code = event.get("return_code")
                            if return_code not in (None, 0):
                                self._print_feed(
                                    f"[{source}] error: exited (return_code={return_code})"
                                )
                            continue

                        continue

                    # Show only meaningful speech and errors from background services.
                    if event_type in {"speech", "error"}:
                        self._print_feed(f"[{source}] {event_type}: {message}")
                except queue.Empty:
                    continue
        except KeyboardInterrupt:
            self._print_feed("[main] shutdown requested")
        finally:
            self.stop_all()
            with self._ui_lock:
                sys.stdout.write("\r\033[2K")
                sys.stdout.flush()
