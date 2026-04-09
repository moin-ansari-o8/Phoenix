import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional


EventCallback = Optional[Callable[[str, Dict], None]]


@dataclass
class VoiceProcessorConfig:
    auto_restart: bool = True
    restart_delay_seconds: float = 2.0


class VoiceProcessorService:
    """Professionalized voice processor runner (renamed from BgVoiceProcessorPHNX)."""

    def __init__(
        self,
        config: VoiceProcessorConfig | None = None,
        event_callback: EventCallback = None,
    ):
        self.config = config or VoiceProcessorConfig()
        self.event_callback = event_callback
        self.process: subprocess.Popen | None = None
        self._root_dir = Path(__file__).resolve().parents[2]
        self._script_path = self._root_dir / "bgprogs" / "BgVoiceProcessorPHNX.pyw"

    def _emit(self, event_type: str, payload: Dict):
        if self.event_callback:
            self.event_callback("voice_processor", {"type": event_type, **payload})

    def _stream_output(self):
        if not self.process or not self.process.stdout:
            return
        for line in self.process.stdout:
            clean = line.rstrip()
            if clean:
                self._emit("log", {"line": clean})

    def run(self, stop_event):
        self._emit("status", {"message": "starting"})
        while not stop_event.is_set():
            try:
                self.process = subprocess.Popen(
                    [sys.executable, str(self._script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                self._emit("status", {"message": "running", "pid": self.process.pid})

                stream_thread = threading.Thread(
                    target=self._stream_output, name="voice-processor-log-stream", daemon=True
                )
                stream_thread.start()

                while self.process.poll() is None and not stop_event.is_set():
                    time.sleep(0.2)

                if stop_event.is_set() and self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=5)
                    break

                return_code = self.process.poll()
                self._emit("status", {"message": "exited", "return_code": return_code})
                if not self.config.auto_restart or stop_event.is_set():
                    break
                stop_event.wait(self.config.restart_delay_seconds)

            except Exception as e:
                self._emit("error", {"message": str(e)})
                if not self.config.auto_restart or stop_event.is_set():
                    break
                stop_event.wait(self.config.restart_delay_seconds)

        self._emit("status", {"message": "stopped"})

