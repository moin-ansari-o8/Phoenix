"""
Real-time audio capture pipeline for Phoenix.

Replaces the hand-rolled state machine that used to live inside
core/continuous_listener.py.  That version had three defects which together
made voice mode unusable:

  1. It fed webrtcvad 1024-sample (64 ms) frames.  webrtcvad only accepts
     10/20/30 ms frames, so every call raised and was swallowed by a bare
     `except: pass` -- VAD was silently dead and detection degraded to a fixed
     RMS threshold of 150, which ordinary room/fan noise clears permanently.
  2. Because of (1) the speech state latched on and never endpointed on
     silence.  Every utterance it ever produced was exactly MAX_SPEECH_DURATION
     (30.08 s) of mostly-noise.
  3. While Phoenix was speaking it *stalled* the input stream instead of
     draining it, so the OS capture buffer accumulated Phoenix's own TTS and
     replayed it as user speech seconds later.

The rules this module enforces, in order of importance:

  * The mic stream is NEVER paused.  A PyAudio callback drains it
    unconditionally; unwanted audio is discarded downstream.  Pausing is what
    created the backlog.
  * Self-voice is rejected by CAPTURE TIMESTAMP, not by a live "is it
    speaking?" flag.  Asking whether Phoenix is speaking *now* tells you
    nothing about audio captured eight seconds ago.
  * VAD decides, energy only vetoes.  The energy threshold adapts to the room
    so a fan can never latch the detector open again.

Frame size is 512 samples (32 ms).  That is Silero's native window; webrtcvad
fallback uses the first 480 samples (30 ms) of each frame.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("PhoenixAudio")

SAMPLE_RATE = 16000
FRAME_SAMPLES = 512  # 32 ms - Silero's native window size
FRAME_MS = 1000.0 * FRAME_SAMPLES / SAMPLE_RATE  # 32.0
WEBRTC_FALLBACK_SAMPLES = 480  # 30 ms - the largest frame webrtcvad accepts

try:
    import webrtcvad

    WEBRTCVAD_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on environment
    WEBRTCVAD_AVAILABLE = False


def frames_for_ms(milliseconds: float) -> int:
    """Number of whole frames covering `milliseconds` (at least 1)."""
    return max(1, int(round(milliseconds / FRAME_MS)))


@dataclass
class Frame:
    """One 32 ms slice of microphone audio."""

    timestamp: float  # epoch seconds at the START of the frame
    samples: np.ndarray  # int16, length FRAME_SAMPLES
    rms: float

    @property
    def end_timestamp(self) -> float:
        return self.timestamp + FRAME_MS / 1000.0


def compute_rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))


# --------------------------------------------------------------------------
# Input device selection
# --------------------------------------------------------------------------

# A live microphone always delivers some dither, even in a dead-quiet room.
# A device that another application holds -- a mic that is busy in a call, or
# muted at the OS level -- opens successfully but delivers digital silence.
# Peak amplitude below this over a probe window means "this device is not
# actually giving us audio", which is the signal we select against.
SILENT_DEVICE_PEAK = 4


@dataclass
class DeviceProbe:
    index: int
    name: str
    peak: int = 0
    rms: float = 0.0
    openable: bool = False
    error: str = ""

    @property
    def alive(self) -> bool:
        return self.openable and self.peak >= SILENT_DEVICE_PEAK


def probe_input_device(
    audio, index: int, name: str, seconds: float = 0.5, warmup_seconds: float = 0.4
) -> DeviceProbe:
    """
    Open a device briefly and measure what it actually delivers.

    The warm-up read is not optional: Windows shared-mode capture hands back
    zero-filled buffers for the first few hundred milliseconds after a stream
    opens. Measuring immediately makes every healthy microphone look like a
    dead one, which is worse than not probing at all -- it would move Phoenix
    off a perfectly good mic.
    """
    import pyaudio

    probe = DeviceProbe(index=index, name=name)
    stream = None
    try:
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=index,
            frames_per_buffer=FRAME_SAMPLES,
        )
        probe.openable = True

        for _ in range(max(1, int(warmup_seconds * SAMPLE_RATE / FRAME_SAMPLES))):
            stream.read(FRAME_SAMPLES, exception_on_overflow=False)

        blocks = max(1, int(seconds * SAMPLE_RATE / FRAME_SAMPLES))
        peak, total = 0, 0.0
        for _ in range(blocks):
            samples = np.frombuffer(
                stream.read(FRAME_SAMPLES, exception_on_overflow=False), dtype=np.int16
            )
            peak = max(peak, int(np.abs(samples).max(initial=0)))
            total += compute_rms(samples)
        probe.peak = peak
        probe.rms = total / blocks
    except Exception as exc:
        probe.error = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            if stream is not None:
                stream.stop_stream()
                stream.close()
        except Exception:
            pass
    return probe


def select_input_device(audio, preferred: Optional[int] = None, avoid: Optional[int] = None):
    """
    Pick a microphone that is actually delivering audio.

    Deliberately NOT the "prefer the quietest device" rule used elsewhere in
    this codebase: a microphone that is busy in a call reads as perfectly
    silent, so preferring quiet actively selects the dead device. We require
    signs of life first, and only then fall back to preference order.

    `avoid` lets a caller skip the device it is currently stuck on when
    re-selecting mid-session.
    """
    if preferred is not None:
        return preferred, []

    try:
        default_index = audio.get_default_input_device_info()["index"]
    except Exception:
        default_index = None

    try:
        host_info = audio.get_host_api_info_by_index(0)
        device_count = host_info.get("deviceCount", 0)
    except Exception:
        return default_index, []

    candidates = []
    for i in range(device_count):
        try:
            info = audio.get_device_info_by_host_api_device_index(0, i)
        except Exception:
            continue
        if info.get("maxInputChannels", 0) > 0:
            candidates.append((i, str(info.get("name", "?"))))

    # Try the default first so a healthy default wins without probing everything.
    ordered = sorted(candidates, key=lambda c: (c[0] != default_index, c[0] == avoid))

    probes = []
    for index, name in ordered:
        probe = probe_input_device(audio, index, name)
        probes.append(probe)
        logger.info(
            "Mic probe [%d] %s -> peak=%d rms=%.1f %s",
            probe.index,
            probe.name[:40],
            probe.peak,
            probe.rms,
            "alive" if probe.alive else (probe.error or "silent/busy"),
        )
        if probe.alive and probe.index != avoid:
            return probe.index, probes

    alive = [p for p in probes if p.alive]
    if alive:
        return alive[0].index, probes

    logger.warning(
        "No input device is delivering audio (all silent or busy); "
        "falling back to the default and will retry"
    )
    return default_index, probes


# --------------------------------------------------------------------------
# Microphone
# --------------------------------------------------------------------------


class MicStream:
    """
    Callback-mode PyAudio input.

    The callback only appends to a bounded deque, so it can never block and the
    OS-level capture buffer can never back up -- which is precisely the failure
    that let Phoenix hear its own voice.  If the consumer falls behind, the
    oldest frames are dropped (counted in `dropped_frames`) rather than
    accumulating into a stale backlog.
    """

    def __init__(self, device_index: Optional[int] = None, buffer_seconds: float = 8.0):
        self.device_index = device_index
        self.pinned_device = device_index is not None
        self._maxlen = frames_for_ms(buffer_seconds * 1000.0)
        self._frames: Deque[Frame] = deque(maxlen=self._maxlen)
        self._new_frame = threading.Event()
        self._audio = None
        self._stream = None
        self.dropped_frames = 0
        self.total_frames = 0
        self._running = False
        self._last_sound_time = time.time()
        self.device_switches = 0

    def _callback(self, in_data, frame_count, time_info, status):
        import pyaudio

        now = time.time()
        try:
            samples = np.frombuffer(in_data, dtype=np.int16)
            # The callback fires once the buffer is full, so the frame started
            # one frame-duration ago.
            frame = Frame(
                timestamp=now - (len(samples) / SAMPLE_RATE),
                samples=samples,
                rms=compute_rms(samples),
            )
            if int(np.abs(samples).max(initial=0)) >= SILENT_DEVICE_PEAK:
                self._last_sound_time = now
            if len(self._frames) == self._maxlen:
                self.dropped_frames += 1
            self._frames.append(frame)
            self.total_frames += 1
            self._new_frame.set()
        except Exception:  # never raise inside the audio callback
            logger.exception("Error in audio callback")
        return (None, pyaudio.paContinue)

    def start(self):
        import pyaudio

        self._audio = pyaudio.PyAudio()
        if not self.pinned_device:
            self.device_index, _ = select_input_device(self._audio)
        self._open_stream()

    def _open_stream(self):
        import pyaudio

        self._stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=FRAME_SAMPLES,
            stream_callback=self._callback,
        )
        self._stream.start_stream()
        self._running = True
        self._last_sound_time = time.time()
        logger.info(
            "MicStream started (device=%s, frame=%d samples/%.0f ms)",
            self.device_index,
            FRAME_SAMPLES,
            FRAME_MS,
        )

    def silent_for(self) -> float:
        """Seconds since the device last delivered anything above the noise of a live mic."""
        return time.time() - self._last_sound_time

    def reselect_device(self) -> bool:
        """
        Re-probe and move to a microphone that is actually delivering audio.

        Called when the current device has gone completely silent, which is
        what happens when a call app takes the mic mid-session. Returns True if
        we moved to a different device.
        """
        if self.pinned_device or self._audio is None:
            return False

        previous = self.device_index
        try:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
        except Exception:
            pass

        chosen, _ = select_input_device(self._audio, avoid=previous)
        self.device_index = chosen if chosen is not None else previous

        try:
            self._open_stream()
        except Exception:
            logger.exception("Failed to reopen mic on device %s", self.device_index)
            self.device_index = previous
            try:
                self._open_stream()
            except Exception:
                logger.exception("Failed to fall back to device %s", previous)
                return False

        self._frames.clear()
        if self.device_index != previous:
            self.device_switches += 1
            logger.warning(
                "Microphone %s went silent (busy or muted); switched to %s",
                previous,
                self.device_index,
            )
            return True
        return False

    def read(self, timeout: float = 0.1) -> Optional[Frame]:
        """Pop the oldest buffered frame, waiting up to `timeout` seconds."""
        if not self._frames:
            self._new_frame.wait(timeout)
            self._new_frame.clear()
        try:
            return self._frames.popleft()
        except IndexError:
            return None

    def flush(self) -> int:
        """Discard everything buffered. Returns how many frames were dropped."""
        count = len(self._frames)
        self._frames.clear()
        return count

    @property
    def backlog(self) -> int:
        return len(self._frames)

    def stop(self):
        self._running = False
        try:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
        except Exception:
            pass
        try:
            if self._audio is not None:
                self._audio.terminate()
        except Exception:
            pass
        logger.info(
            "MicStream stopped (frames=%d, dropped=%d)",
            self.total_frames,
            self.dropped_frames,
        )


# --------------------------------------------------------------------------
# Adaptive noise floor
# --------------------------------------------------------------------------


class NoiseFloor:
    """
    Rolling percentile of frame RMS, used as an energy veto under the VAD.

    Only updated while the endpointer is idle, so a long utterance can't drag
    the floor up and deafen the detector mid-sentence.
    """

    def __init__(
        self,
        window_seconds: float = 5.0,
        percentile: float = 20.0,
        multiplier: float = 3.0,
        absolute_min: float = 120.0,
    ):
        self._history: Deque[float] = deque(maxlen=frames_for_ms(window_seconds * 1000))
        self.percentile = percentile
        self.multiplier = multiplier
        self.absolute_min = absolute_min

    def update(self, rms: float):
        self._history.append(rms)

    @property
    def value(self) -> float:
        if not self._history:
            return 0.0
        return float(np.percentile(np.asarray(self._history), self.percentile))

    @property
    def threshold(self) -> float:
        """RMS a frame must exceed to be considered plausibly speech."""
        return max(self.value * self.multiplier, self.absolute_min)

    def is_loud_enough(self, rms: float) -> bool:
        return rms > self.threshold

    @property
    def samples(self) -> int:
        return len(self._history)


# --------------------------------------------------------------------------
# Voice activity detection
# --------------------------------------------------------------------------


class VoiceDetector:
    """
    Silero VAD (bundled with faster-whisper, so no extra dependency) with a
    webrtcvad fallback, plus an adaptive-energy veto.

    Silero is evaluated over a rolling context window rather than a single
    isolated frame: the bundled wrapper resets its LSTM state on every call, so
    a lone 32 ms frame gives it no temporal context.  An 8-frame (256 ms)
    window costs ~0.56 ms per call -- under 2% of one core -- and we keep only
    the probability for the newest frame.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        context_frames: int = 8,
        prefer_silero: bool = True,
    ):
        self.threshold = threshold
        self.context_frames = max(1, context_frames)
        self._context: Deque[np.ndarray] = deque(maxlen=self.context_frames)
        self._silero = None
        self._webrtc = None
        self.backend = "energy"

        if prefer_silero:
            try:
                from faster_whisper.vad import get_vad_model

                self._silero = get_vad_model()
                self.backend = "silero"
            except Exception as exc:
                logger.warning("Silero VAD unavailable (%s), falling back", exc)

        if self._silero is None and WEBRTCVAD_AVAILABLE:
            try:
                self._webrtc = webrtcvad.Vad(2)
                self.backend = "webrtcvad"
            except Exception as exc:
                logger.warning("webrtcvad unavailable (%s)", exc)

        logger.info("VoiceDetector backend: %s", self.backend)

    def reset(self):
        self._context.clear()

    def speech_probability(self, frame: Frame) -> float:
        audio = frame.samples.astype(np.float32) / 32768.0

        if self._silero is not None:
            self._context.append(audio)
            window = np.concatenate(list(self._context))
            try:
                out = self._silero(window)
                return float(np.asarray(out).reshape(-1)[-1])
            except Exception as exc:
                logger.warning("Silero VAD call failed (%s), disabling", exc)
                self._silero = None
                self.backend = "webrtcvad" if WEBRTCVAD_AVAILABLE else "energy"
                if self._webrtc is None and WEBRTCVAD_AVAILABLE:
                    self._webrtc = webrtcvad.Vad(2)

        if self._webrtc is not None:
            # webrtcvad accepts only 10/20/30 ms frames -- feed it exactly 30 ms.
            # Handing it the full 512-sample frame is what broke the old listener.
            chunk = frame.samples[:WEBRTC_FALLBACK_SAMPLES]
            if chunk.size == WEBRTC_FALLBACK_SAMPLES:
                try:
                    return 1.0 if self._webrtc.is_speech(chunk.tobytes(), SAMPLE_RATE) else 0.0
                except Exception as exc:
                    logger.warning("webrtcvad call failed (%s), disabling", exc)
                    self._webrtc = None
                    self.backend = "energy"

        return -1.0  # "no opinion" -- caller falls back to energy alone

    def is_voiced(self, frame: Frame, noise_floor: NoiseFloor) -> Tuple[bool, float]:
        """
        Returns (voiced, probability).

        The energy veto matters: Silero happily fires on distant TV chatter and
        keyboard clatter that sit near the noise floor.  Requiring both a VAD
        hit and an above-floor RMS is what keeps a silent room silent.
        """
        prob = self.speech_probability(frame)
        loud_enough = noise_floor.is_loud_enough(frame.rms)

        if prob < 0.0:  # no VAD backend at all
            return loud_enough, prob
        return (prob >= self.threshold and loud_enough), prob


# --------------------------------------------------------------------------
# Endpointing
# --------------------------------------------------------------------------


@dataclass
class EndpointerConfig:
    pre_roll_ms: float = 300.0  # audio kept before speech is confirmed
    start_frames: int = 3  # consecutive voiced frames to open an utterance
    hangover_ms: float = 600.0  # trailing silence that closes an utterance
    min_voiced_ms: float = 400.0  # below this, discard as noise
    max_utterance_ms: float = 12000.0  # hard cap; never another 30 s blob


@dataclass
class Utterance:
    audio: np.ndarray  # int16 mono @ 16 kHz
    start_timestamp: float
    end_timestamp: float
    voiced_ms: float
    reason: str  # "silence" | "max_duration"

    @property
    def duration(self) -> float:
        return len(self.audio) / SAMPLE_RATE


class Endpointer:
    """
    Turns a stream of (frame, voiced) decisions into complete utterances.

    Opens on `start_frames` consecutive voiced frames, prepends `pre_roll_ms` of
    already-captured audio so the first syllable isn't clipped, and closes after
    `hangover_ms` of continuous silence.  Utterances carrying less than
    `min_voiced_ms` of actual voiced audio are dropped -- that alone kills the
    "Thank you." hallucinations, because a noise-only window never reaches
    Whisper at all.
    """

    def __init__(self, config: Optional[EndpointerConfig] = None):
        self.config = config or EndpointerConfig()
        self._pre_roll: Deque[Frame] = deque(
            maxlen=frames_for_ms(self.config.pre_roll_ms)
        )
        self._buffer: List[Frame] = []
        self._active = False
        self._voiced_frames = 0
        self._consecutive_voiced = 0
        self._consecutive_silent = 0
        self._start_timestamp = 0.0

    @property
    def active(self) -> bool:
        return self._active

    @property
    def buffered_ms(self) -> float:
        return len(self._buffer) * FRAME_MS

    def reset(self):
        """
        Abandon any in-progress utterance and clear look-back.

        Called when the echo gate closes, so audio captured during Phoenix's own
        playback can never be stitched onto the front of a live user utterance.
        That stitching is exactly how a reply and the next command ended up in
        one transcript.
        """
        self._pre_roll.clear()
        self._buffer = []
        self._active = False
        self._voiced_frames = 0
        self._consecutive_voiced = 0
        self._consecutive_silent = 0
        self._start_timestamp = 0.0

    def push(self, frame: Frame, voiced: bool) -> Optional[Utterance]:
        cfg = self.config

        if voiced:
            self._consecutive_voiced += 1
            self._consecutive_silent = 0
        else:
            self._consecutive_silent += 1
            self._consecutive_voiced = 0

        if not self._active:
            self._pre_roll.append(frame)
            if self._consecutive_voiced >= cfg.start_frames:
                self._active = True
                self._buffer = list(self._pre_roll)
                self._voiced_frames = min(cfg.start_frames, len(self._buffer))
                self._start_timestamp = self._buffer[0].timestamp
                self._pre_roll.clear()
            return None

        self._buffer.append(frame)
        if voiced:
            self._voiced_frames += 1

        if self.buffered_ms >= cfg.max_utterance_ms:
            return self._finish("max_duration")

        if self._consecutive_silent >= frames_for_ms(cfg.hangover_ms):
            return self._finish("silence")

        return None

    def _finish(self, reason: str) -> Optional[Utterance]:
        frames = self._buffer
        voiced_ms = self._voiced_frames * FRAME_MS
        start = self._start_timestamp
        end = frames[-1].end_timestamp if frames else start

        self._buffer = []
        self._active = False
        self._voiced_frames = 0
        self._consecutive_silent = 0
        self._consecutive_voiced = 0
        self._pre_roll.clear()

        if not frames or voiced_ms < self.config.min_voiced_ms:
            logger.debug(
                "Utterance discarded: only %.0f ms voiced (need %.0f)",
                voiced_ms,
                self.config.min_voiced_ms,
            )
            return None

        return Utterance(
            audio=np.concatenate([f.samples for f in frames]),
            start_timestamp=start,
            end_timestamp=end,
            voiced_ms=voiced_ms,
            reason=reason,
        )


# --------------------------------------------------------------------------
# Self-voice gating
# --------------------------------------------------------------------------


class EchoGate:
    """
    Drops microphone frames that were captured while Phoenix's own audio was
    audible.

    The critical detail is that this is keyed on the frame's CAPTURE timestamp,
    not on whether Phoenix happens to be speaking at the moment the frame is
    examined.  The previous implementation checked a live boolean, which says
    nothing about audio recorded seconds earlier -- so backlogged self-voice
    sailed straight through.

    `state_provider` returns (speaking_since, speaking_until) as epoch seconds
    and is polled at `poll_interval` rather than per frame, because it crosses a
    process boundary.  `speaking_until` is heartbeated forward by the speech
    engine while audio plays, so if that process dies mid-sentence the gate
    self-heals within half a second instead of wedging the mic shut forever.
    """

    def __init__(
        self,
        state_provider: Callable[[], Tuple[float, float]],
        lead_in: float = 0.15,
        tail: float = 0.40,
        poll_interval: float = 0.05,
        enabled: bool = True,
        enabled_provider: Optional[Callable[[], Optional[bool]]] = None,
    ):
        self._state_provider = state_provider
        # Polled alongside the speech window so switching between speakers and
        # headphones takes effect in the running listener. Returning None means
        # "no opinion", leaving whatever `enabled` already is.
        self._enabled_provider = enabled_provider
        self.lead_in = lead_in
        self.tail = tail
        self.poll_interval = poll_interval
        self.enabled = enabled
        self._since = 0.0
        self._until = 0.0
        self._last_poll = 0.0
        self._was_gating = False
        self._closed_edge = False
        self.dropped_frames = 0

    def _refresh(self, now: Optional[float] = None):
        now = now or time.time()
        if now - self._last_poll < self.poll_interval:
            return
        self._last_poll = now
        try:
            self._since, self._until = self._state_provider()
        except Exception as exc:
            logger.debug("Echo gate state unavailable (%s)", exc)
            self._since, self._until = 0.0, 0.0

        if self._enabled_provider is not None:
            try:
                is_open = self._enabled_provider()
                if is_open is not None:
                    self.enabled = not is_open
            except Exception as exc:
                logger.debug("Echo mode unavailable (%s)", exc)

    def should_drop(self, timestamp: float) -> bool:
        self._refresh()
        if not self.enabled:
            self._was_gating = False
            return False
        if self._since <= 0.0:
            gating = False
        else:
            gating = (self._since - self.lead_in) <= timestamp <= (self._until + self.tail)

        if self._was_gating and not gating:
            self._closed_edge = True
        self._was_gating = gating

        if gating:
            self.dropped_frames += 1
        return gating

    def consume_close_edge(self) -> bool:
        """
        True exactly once after the gate stops suppressing audio.

        The driver uses this to flush the mic buffer and reset the endpointer,
        so nothing captured during playback survives into the next utterance.
        """
        if self._closed_edge:
            self._closed_edge = False
            return True
        return False

    @property
    def is_speaking_now(self) -> bool:
        now = time.time()
        self._refresh(now)
        return self._since > 0.0 and now <= self._until


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


@dataclass
class CaptureStats:
    frames: int = 0
    gated_frames: int = 0
    utterances: int = 0
    discarded_utterances: int = 0
    last_noise_floor: float = 0.0
    last_threshold: float = 0.0


class CapturePipeline:
    """
    Wires MicStream -> EchoGate -> VoiceDetector -> Endpointer together.

    Deliberately transport-agnostic: it hands finished utterances to a callback
    so the same pipeline can feed the cross-process queue in production and a
    plain list in tests.
    """

    def __init__(
        self,
        on_utterance: Callable[[Utterance], None],
        echo_gate: Optional[EchoGate] = None,
        endpointer_config: Optional[EndpointerConfig] = None,
        vad_threshold: float = 0.5,
        device_index: Optional[int] = None,
        on_speech_start: Optional[Callable[[], None]] = None,
    ):
        self.on_utterance = on_utterance
        self.on_speech_start = on_speech_start
        self.mic = MicStream(device_index=device_index)
        self.noise_floor = NoiseFloor()
        self.detector = VoiceDetector(threshold=vad_threshold)
        self.endpointer = Endpointer(endpointer_config)
        self.echo_gate = echo_gate
        self.stats = CaptureStats()
        self._running = False

    def process_frame(self, frame: Frame) -> Optional[Utterance]:
        """
        Single-frame step, broken out so tests can drive it without a mic.

        Dispatching the callback and counting stats both happen here rather
        than in run(), so feeding frames directly behaves identically to the
        live path instead of silently skipping the callback.
        """
        self.stats.frames += 1

        if self.echo_gate is not None and self.echo_gate.should_drop(frame.timestamp):
            self.stats.gated_frames += 1
            return None

        if self.echo_gate is not None and self.echo_gate.consume_close_edge():
            dropped = self.mic.flush()
            self.endpointer.reset()
            self.detector.reset()
            logger.debug("Echo gate closed: flushed %d frames, reset endpointer", dropped)
            return None

        voiced, prob = self.detector.is_voiced(frame, self.noise_floor)

        # Freeze the noise floor during an utterance so speech can't inflate it.
        if not self.endpointer.active and not voiced:
            self.noise_floor.update(frame.rms)

        was_active = self.endpointer.active
        utterance = self.endpointer.push(frame, voiced)
        if not was_active and self.endpointer.active and self.on_speech_start:
            self.on_speech_start()

        self.stats.last_noise_floor = self.noise_floor.value
        self.stats.last_threshold = self.noise_floor.threshold

        if utterance is not None:
            self.stats.utterances += 1
            self.on_utterance(utterance)
        return utterance

    def run(self, stop_check: Callable[[], bool]):
        self.mic.start()
        self._running = True
        try:
            while not stop_check():
                frame = self.mic.read(timeout=0.1)
                if frame is None:
                    continue
                self.process_frame(frame)
        finally:
            self._running = False
            self.mic.stop()
