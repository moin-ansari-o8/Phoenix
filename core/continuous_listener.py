"""
Phoenix Listener - continuous audio capture.

Thin driver over Utils/limbs/audio_capture.  All the signal logic (mic stream,
VAD, adaptive noise floor, endpointing, echo gating) lives there so it can be
unit-tested without a microphone; this file only wires it to the cross-process
queue and emits the runtime traces the TUI parses.

The previous version of this file owned an inline state machine that never once
endpointed on silence -- every utterance it produced was exactly 30.08 s of
mostly room noise.  See Utils/limbs/audio_capture for the full post-mortem.
"""

import logging
import os
import signal
import sys
import threading
import time

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import AppConfig
from Utils.limbs.audio_capture import (
    CapturePipeline,
    EchoGate,
    EndpointerConfig,
    Utterance,
)
from Utils.limbs.queue_manager import QueueManager, create_audio_chunk

# Setup logging (file only - the TUI owns the console)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("phoenix_listener.log")],
)
logger = logging.getLogger("PhoenixListener")

for _handler in list(logging.getLogger().handlers):
    if isinstance(_handler, logging.StreamHandler) and _handler.stream in (
        sys.stdout,
        sys.stderr,
    ):
        logging.getLogger().removeHandler(_handler)


class PhoenixListener:
    """Captures speech and forwards complete utterances to the processor."""

    STATS_INTERVAL_SECONDS = 30.0
    HEALTH_INTERVAL_SECONDS = 5.0
    RESELECT_COOLDOWN_SECONDS = 30.0

    def __init__(self, queue_manager: QueueManager):
        self.queue_manager = queue_manager
        self.stop_event = threading.Event()
        self.chunks_sent = 0
        self._running = False
        self._last_health_log = 0.0
        self._last_reselect_attempt = 0.0
        self._reported_dead_mic = False

        audio_cfg = AppConfig.audio
        self.echo_mode = audio_cfg.get("echo_mode", "gate")
        self.barge_in_configured = bool(audio_cfg.get("barge_in", True))

        # Seed the shared echo mode from config, then track it live so saying
        # "headphone mode" switches the running listener without a restart.
        self.queue_manager.set_echo_open(self.echo_mode == "open")

        # In "open" mode (headphones) the mic never hears Phoenix, so gating
        # would only add latency. In "gate" mode (speakers) it is the primary
        # defence against self-voice.
        self.echo_gate = EchoGate(
            state_provider=self.queue_manager.get_speech_window,
            enabled_provider=self.queue_manager.is_echo_open,
            tail=0.35,
            enabled=(self.echo_mode == "gate"),
        )

        endpointer_config = EndpointerConfig(
            pre_roll_ms=float(audio_cfg.get("pre_roll_ms", 300)),
            hangover_ms=float(audio_cfg.get("hangover_ms", 800)),
            min_voiced_ms=float(audio_cfg.get("min_voiced_ms", 400)),
            max_utterance_ms=float(audio_cfg.get("max_utterance_ms", 20000)),
        )

        # Tolerance for a mid-sentence pause is hangover + stitch window, but
        # only a sentence that actually continues pays the stitch window. See
        # CapturePipeline's docstring.
        self.stitch_window_ms = float(audio_cfg.get("stitch_window_ms", 900))

        self.mic_silence_timeout = float(audio_cfg.get("mic_silence_timeout_seconds", 20))
        self.pipeline = CapturePipeline(
            on_utterance=self._on_utterance,
            on_speech_start=self._on_speech_start,
            echo_gate=self.echo_gate,
            endpointer_config=endpointer_config,
            vad_threshold=float(audio_cfg.get("vad_threshold", 0.5)),
            device_index=audio_cfg.get("input_device"),
            stitch_window_ms=self.stitch_window_ms,
        )
        self.pipeline.noise_floor.multiplier = float(
            audio_cfg.get("noise_multiplier", 3.0)
        )
        self.pipeline.noise_floor.absolute_min = float(
            audio_cfg.get("noise_absolute_min", 120.0)
        )

        self.gui = self._init_gui()

        logger.info(
            "Listener ready (echo_mode=%s, barge_in=%s, vad=%s, hangover=%.0fms, "
            "stitch=%.0fms, pause_tolerance=%.0fms, max=%.0fms)",
            self.echo_mode,
            self.barge_in_configured,
            self.pipeline.detector.backend,
            endpointer_config.hangover_ms,
            self.stitch_window_ms,
            endpointer_config.hangover_ms + self.stitch_window_ms,
            endpointer_config.max_utterance_ms,
        )

    # -- optional on-screen indicator --------------------------------------

    def _init_gui(self):
        try:
            import tkinter as tk
            from Utils.limbs.assistant_io import VoiceAssistantGUI

            self._tk_root = tk.Tk()
            gui = VoiceAssistantGUI(self._tk_root)
            gui.show_listen_image()
            return gui
        except Exception as exc:
            logger.warning("Visual indicator unavailable: %s", exc)
            self._tk_root = None
            return None

    def _set_indicator(self, listening: bool):
        if self.gui is None:
            return
        try:
            if listening:
                self.gui.hide_recognize_image()
                self.gui.show_listen_image()
            else:
                self.gui.show_recognize_image()
        except Exception:
            pass

    # -- traces -------------------------------------------------------------

    @staticmethod
    def _trace(tag: str, message: str):
        """Line-based runtime traces the TUI in main.py parses."""
        print(f"[{tag}] {message}", flush=True)

    # -- pipeline callbacks -------------------------------------------------

    def _on_speech_start(self):
        self._trace("VOICE_STATE", "detected")

        # Barge-in: the user started talking while Phoenix is still talking.
        # Only meaningful when the gate is off (headphones) -- with speakers
        # this audio could be Phoenix's own voice, and it would interrupt
        # itself mid-sentence. `echo_gate.enabled` tracks the live mode, so
        # this follows a runtime "headphone mode" switch.
        if (
            self.barge_in_configured
            and not self.echo_gate.enabled
            and self.echo_gate.is_speaking_now
        ):
            logger.info("Speech during playback - requesting interrupt")
            self.queue_manager.request_interrupt()
            self._trace("VOICE_STATE", "interrupt")

    def _on_utterance(self, utterance: Utterance):
        self._set_indicator(listening=False)
        self._trace("VOICE_STATE", "processing")

        chunk = create_audio_chunk(
            audio_data=utterance.audio,
            energy_level=0.0,
            start_timestamp=utterance.start_timestamp,
            end_timestamp=utterance.end_timestamp,
            voiced_ms=utterance.voiced_ms,
            end_reason=utterance.reason,
        )

        if self.queue_manager.send_chunk(chunk, timeout=0.5):
            self.chunks_sent += 1
            logger.info(
                "Utterance sent: %.2fs (%.0fms voiced, end=%s)",
                utterance.duration,
                utterance.voiced_ms,
                utterance.reason,
            )
        else:
            logger.warning("Queue full - utterance dropped")

        self._set_indicator(listening=True)
        self._trace("VOICE_STATE", "listening")

    # -- lifecycle ----------------------------------------------------------

    def _stats_loop(self):
        """Periodic health line, so 'is it actually listening?' has an answer."""
        while not self.stop_event.wait(self.HEALTH_INTERVAL_SECONDS):
            self._check_microphone_alive()

            now = time.time()
            if now - self._last_health_log < self.STATS_INTERVAL_SECONDS:
                continue
            self._last_health_log = now

            stats = self.pipeline.stats
            logger.info(
                "[HEALTH] frames=%d gated=%d utterances=%d stitched=%d backlog=%d "
                "dropped=%d noise_floor=%.1f threshold=%.1f device=%s silent_for=%.0fs",
                stats.frames,
                stats.gated_frames,
                stats.utterances,
                stats.stitched_utterances,
                self.pipeline.mic.backlog,
                self.pipeline.mic.dropped_frames,
                stats.last_noise_floor,
                stats.last_threshold,
                self.pipeline.mic.device_index,
                self.pipeline.mic.silent_for(),
            )

    def _check_microphone_alive(self):
        """
        Move to another microphone if the current one has gone dead.

        A mic that another app takes over -- typically a call -- keeps opening
        fine and keeps delivering frames, but every sample is zero. Without
        this the listener would sit there happily processing digital silence
        forever, looking healthy while hearing nothing.
        """
        mic = self.pipeline.mic
        if mic.pinned_device or not self._running:
            return

        silent_for = mic.silent_for()
        if silent_for < self.mic_silence_timeout:
            self._reported_dead_mic = False
            return

        now = time.time()
        if now - self._last_reselect_attempt < self.RESELECT_COOLDOWN_SECONDS:
            return
        self._last_reselect_attempt = now

        if not self._reported_dead_mic:
            logger.warning(
                "Microphone %s has delivered silence for %.0fs - looking for another input",
                mic.device_index,
                silent_for,
            )
            self._reported_dead_mic = True

        if mic.reselect_device():
            self._trace("MIC", f"switched to input device {mic.device_index}")
            # Full reset, not just the endpointer: audio parked for stitching
            # came from the dead device and must not be glued onto the first
            # utterance from the new one.
            self.pipeline.reset()

    def run(self):
        logger.info("Starting continuous listening...")
        self._running = True
        threading.Thread(target=self._stats_loop, name="listener-stats", daemon=True).start()

        self._trace("VOICE_STATE", "listening")
        try:
            self.pipeline.run(stop_check=self.stop_event.is_set)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception:
            logger.exception("Fatal error in listening loop")
        finally:
            self.shutdown()

    def shutdown(self):
        if self.stop_event.is_set():
            return
        logger.info("Shutting down listener...")
        self._running = False
        self.stop_event.set()
        stats = self.pipeline.stats
        logger.info(
            "=== Listener stats: frames=%d gated=%d utterances=%d sent=%d dropped=%d ===",
            stats.frames,
            stats.gated_frames,
            stats.utterances,
            self.chunks_sent,
            self.pipeline.mic.dropped_frames,
        )
        try:
            if self._tk_root is not None:
                self._tk_root.destroy()
        except Exception:
            pass


class ListenerManager:
    """Manages the listener lifecycle"""

    def __init__(self):
        self.listener = None
        self.queue_manager = None
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        if self.listener:
            self.listener.shutdown()
        sys.exit(0)

    def start(self):
        try:
            logger.info("PHOENIX CONTINUOUS LISTENER STARTING")
            self.queue_manager = QueueManager(max_size=10)
            self.listener = PhoenixListener(self.queue_manager)
            self.listener.run()
        except Exception as e:
            logger.critical(f"CRITICAL ERROR: Listener failed to start: {e}", exc_info=True)
            sys.exit(1)
        finally:
            if self.listener:
                self.listener.shutdown()


if __name__ == "__main__":
    try:
        ListenerManager().start()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
