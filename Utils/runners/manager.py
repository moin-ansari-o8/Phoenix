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

            # One per process. AdvancedTUIManager replaces this reference
            # with a proxy, so building a second engine here was paying for
            # a COM init and a voice enumeration nothing ever spoke through.
            self.shared_speech_engine = SpeechEngine.shared()
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
        status = self._live_status or "Listening..."
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

    def _handle_trace_event(self, event):
        """Render a structured trace in the plain (non-rich) fallback UI."""
        kind = event.get("event", "")
        text = (event.get("text") or "").strip()

        if kind == "fatal":
            self._print_feed(f"[!] Voice processor stopped: {text}")
            self._set_status("Voice processor stopped - restart Phoenix")
            return
        if kind == "voice_state":
            state = text.lower()
            self._set_status(
                {
                    "listening": "Listening...",
                    "detected": "Voice detected...",
                    "processing": "Processing...",
                    "awake": "Listening (follow-up)...",
                    "dormant": "Listening - say the wake word...",
                }.get(state, "Listening...")
            )
            return
        if kind == "heard":
            if text and text != "<empty>":
                self._print_feed(f"You: {text}")
            self._set_status("Listening...")
            return
        if kind == "ignored_heard":
            if text and text != "<empty>":
                self._print_feed(f"heard: {text}")
            self._set_status("Listening...")
            return
        if kind == "processing":
            self._set_status("Processing...")
            return
        if kind == "intent":
            self._set_status("Listening...")
            return
        if kind in ("discarded", "self_echo"):
            self._set_status("Listening...")
            return
        # Diagnostics. Listed explicitly so a new event type fails
        # tests/test_trace.py rather than disappearing without trace.
        if kind == "stale":
            self._print_feed(f"  -> skipped: {text}")
            self._set_status("Listening...")
            return
        if kind in ("stt", "gate", "speaker", "repaired", "song_rerank"):
            if text:
                self._print_feed(f"  -> {kind}: {text}")
            return

    def _is_banner_or_noise(self, line: str) -> bool:
        # Startup chatter from the child processes. These used to be matched by
        # their emoji prefix; assistant_io now emits [INFO]/[WARN] per the
        # project's no-emoji-in-console rule, so match the text instead - an
        # emoji match here silently stopped filtering the moment that changed.
        if not line:
            return True
        if line.startswith("[DEBUG]"):
            return True
        if "Voice engine:" in line:
            return True
        if "Loading Whisper" in line:
            return True
        if "Speech recognition ready" in line:
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

        # Structured traces first - see core/trace.py. This fallback formatter
        # (used when the TUI subclass is not driving) previously carried its
        # own copy of the tag parser, which drifted out of sync with main.py's.
        from core.trace import parse as parse_trace

        event = parse_trace(clean)
        if event is not None:
            self._handle_trace_event(event)
            return

        if self._is_banner_or_noise(clean):
            return

        if clean.startswith("[FATAL]"):
            detail = clean.removeprefix("[FATAL]").strip()
            self._print_feed(f"[!] Voice processor stopped: {detail}")
            self._set_status("Voice processor stopped - restart Phoenix")
            return

        if clean.startswith("[VOICE_STATE]"):
            state = clean.removeprefix("[VOICE_STATE]").strip().lower()
            if state == "listening":
                self._set_status("Listening...")
                return
            if state == "detected":
                self._set_status("Voice detected...")
                return
            if state == "processing":
                self._set_status("Processing...")
                return
            if state == "awake":
                self._set_status("Listening (follow-up)...")
                return
            if state == "dormant":
                self._set_status("Listening - say the wake word...")
                return

        if clean.startswith("[HEARD]"):
            heard = clean.removeprefix("[HEARD]").strip()
            if heard and heard != "<empty>":
                self._print_feed(f"You: {heard}")
            self._set_status("Listening...")
            return

        if clean.startswith("[IGNORED_HEARD]"):
            heard = clean.removeprefix("[IGNORED_HEARD]").strip()
            if heard and heard != "<empty>":
                self._print_feed(f"heard: {heard}")
            self._set_status("Listening...")
            return

        if clean.startswith("[PROCESSING]"):
            self._set_status("Processing...")
            return

        if clean.startswith("[IGNORED]"):
            self._set_status("Listening...")
            return

        if clean.startswith("[INTENT]"):
            self._set_status("Listening...")
            return

        # console_ui.py's own output, reaching us over the child's stdout.
        # These used to match on its emoji prefixes; console_ui now emits plain
        # text per the project's no-emoji rule, and an emoji matcher would have
        # silently stopped matching the moment that changed - with no failure,
        # just a status line that quietly stopped updating.
        if "Voice detected" in clean:
            self._set_status("Voice detected...")
            return

        if clean.startswith("Processing"):
            self._set_status("Processing...")
            return

        if clean.startswith("Listening"):
            self._set_status("Listening...")
            return

        if clean.startswith("You ["):
            return

        if clean.startswith("Phoenix ["):
            self._print_feed(clean)
            self._set_status("Listening...")
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
        import subprocess
        try:
            # Launch ollama serve silently in the background
            # If it's already running, this will just exit silently.
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            self._on_event(
                "main", {"type": "error", "message": f"Failed to start ollama: {e}"}
            )

        # Warm both AI models so the first real query does not pay the cold-load
        # cost. keep_alive in OllamaHelper.chat then holds them resident.
        def _warm():
            try:
                from Utils.ai_manager import AIDecisionMaker

                ai = AIDecisionMaker()
                for helper in (ai._get_router(), ai._get_answer()):
                    helper.chat([{"role": "user", "content": "hi"}], timeout=300)
            except Exception:
                pass

        threading.Thread(target=_warm, daemon=True, name="model-warmup").start()

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
        from core.config import AppConfig

        self._preload_runtime_dependencies()
        if AppConfig.bg_progs.get("battery_check", True):
            self._start_thread("battery-monitor-thread", self.battery_service.run)
        if AppConfig.bg_progs.get("time_check", True):
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
        self._set_status("Listening...")
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
                                self._set_status("Listening...")
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
