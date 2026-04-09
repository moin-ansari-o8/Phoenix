import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Any

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

        self.state: Dict[str, Any] = {
            "last_event": {},
            "last_speech": {},
            "services": {},
        }

        self.battery_service = BatteryMonitorService(
            config=self.config.battery, event_callback=self._on_event
        )
        self.time_service = TimeMonitorService(
            config=self.config.time, event_callback=self._on_event
        )
        self.voice_service = VoiceProcessorService(
            config=self.config.voice, event_callback=self._on_event
        )

    def _on_event(self, source: str, payload: Dict[str, Any]):
        event = {"source": source, "timestamp": time.time(), **payload}
        self.state["last_event"][source] = event
        if payload.get("type") == "speech":
            self.state["last_speech"][source] = payload.get("message", "")
        if payload.get("type") == "status":
            self.state["services"][source] = payload.get("message")
        self.events.put(event)

    def _start_thread(self, name: str, target):
        thread = threading.Thread(target=target, args=(self.stop_event,), name=name, daemon=True)
        self.threads[name] = thread
        thread.start()

    def start_all(self):
        self._start_thread("battery-monitor-thread", self.battery_service.run)
        self._start_thread("time-monitor-thread", self.time_service.run)
        self._start_thread("voice-processor-thread", self.voice_service.run)

    def stop_all(self):
        self.stop_event.set()
        for thread in self.threads.values():
            thread.join(timeout=5)

    def snapshot(self) -> Dict[str, Any]:
        return self.state.copy()

    def run_forever(self):
        self.start_all()
        try:
            while not self.stop_event.is_set():
                try:
                    event = self.events.get(timeout=self.config.main_loop_sleep_seconds)
                    source = event.get("source")
                    event_type = event.get("type")
                    message = event.get("message") or event.get("line", "")
                    if event_type in {"speech", "status", "error"}:
                        print(f"[{source}] {event_type}: {message}")
                except queue.Empty:
                    continue
        except KeyboardInterrupt:
            print("\n[main] shutdown requested")
        finally:
            self.stop_all()

