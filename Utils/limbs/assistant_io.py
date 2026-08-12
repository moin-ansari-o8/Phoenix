import logging
import os
import sys
import threading
from time import sleep
import random
import pyttsx3
import speech_recognition as sr
import tkinter as tk
from PIL import Image, ImageTk
from colorama import Fore
import warnings
import numpy as np
import pyaudio
import queue
import time
import asyncio
from datetime import datetime

# Suppress pygame deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")

# Hide pygame welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Keep helper-level console output quiet unless explicitly enabled.
CONSOLE_VERBOSE = os.environ.get("PHOENIX_CONSOLE_VERBOSE", "0") == "1"


_logger = logging.getLogger("SpeechEngine")


def _console_print(*args, force=False, **kwargs):
    if force or CONSOLE_VERBOSE:
        print(*args, **kwargs)


# Edge TTS for natural voice (like IGRS)
try:
    import edge_tts
    import pygame

    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    _console_print(
        "[Warning] edge-tts or pygame not installed. Using pyttsx3 fallback.",
        force=True,
    )

# Faster-Whisper for offline speech recognition
try:
    from faster_whisper import WhisperModel

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    _console_print(
        "[Warning] faster-whisper not installed. Using Google Speech Recognition (requires internet).",
        force=True,
    )

# VAD (Voice Activity Detection) for continuous listening
try:
    import webrtcvad

    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    _console_print(
        "[Warning] webrtcvad not installed. Install with: pip install webrtcvad",
        force=True,
    )


class SpeechEngine:
    """
    Speech engine. SAPI5 (pyttsx3) is the default and tested path; Edge TTS is
    available but reaches Microsoft's cloud, so it is opt-in only.

    Piper was removed 2026-08-12. It synthesised a .wav via a subprocess on
    every utterance, which is too slow for a conversational turn and was
    intermittently glitchy. `voice/*.onnx` on disk is now unused.

    Config is read in __init__, NOT into class attributes. The old code did
    `EDGE_VOICE = AppConfig.voice` in the class body, which binds once at first
    import and leaks AppConfig into the class namespace - so a profile switch
    could not affect an already-imported process, and the separate processes
    that each build a SpeechEngine could disagree about the voice.
    """

    EDGE_PITCH = "+0Hz"
    EDGE_RATE = "+10%"  # Slightly faster speech

    def __init__(self):
        from core.config import AppConfig

        self.lock = threading.Lock()
        self.honorifics = True
        self.on_playback_start = None  # callback fired when audio begins playing

        self.EDGE_VOICE = AppConfig.voice
        self.TTS_ENGINE = AppConfig.tts_engine  # validated in core/config.py
        self.SAPI_VOICE = getattr(AppConfig, "sapi_voice", "")
        self._fallback_voice_index = AppConfig.fallback_voice_index

        self.use_edge_tts = (self.TTS_ENGINE == "edge") and EDGE_TTS_AVAILABLE
        self._pygame_initialized = False

        # One SAPI engine per thread, built lazily. pyttsx3.init() was being
        # called on EVERY utterance - a COM init plus driver construction per
        # sentence, on the critical path between the answer and the first
        # audible word. It is per-thread rather than shared because a SAPI COM
        # object belongs to the apartment that created it.
        self._tls = threading.local()

        # One queue-server connection for the lifetime of the engine. This used
        # to be re-established on every single utterance, which meant a fresh
        # named-pipe handshake before Phoenix could say anything at all.
        self._queue_manager = None
        self._queue_unavailable = False
        self._speaking_stop = None
        self._interrupted = False

        # Temp file for TTS audio
        self._temp_audio_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "data"
        )
        os.makedirs(self._temp_audio_dir, exist_ok=True)
        self._temp_audio_file = os.path.join(self._temp_audio_dir, "phoenix_speech.mp3")

        self.voice_id = None
        self.voice_name = ""
        self.rate = 174
        self.volume = 1.0

        try:
            probe = pyttsx3.init("sapi5")
            self.voice_id, self.voice_name = self._pick_sapi_voice(
                probe.getProperty("voices")
            )
            probe.stop()
            del probe
        except Exception as exc:
            _console_print(f"[WARN] Could not enumerate SAPI voices: {exc}", force=True)

        if self.use_edge_tts:
            _console_print(f"[INFO] Voice engine: Edge TTS ({self.EDGE_VOICE})")
        else:
            _console_print(f"[INFO] Voice engine: SAPI5 ({self.voice_name or 'default'})")

    def _pick_sapi_voice(self, voices):
        """
        Resolve the SAPI voice by NAME, falling back to the index.

        `fallback_voice_index` indexes a registry enumeration whose order is
        machine-dependent, so index 1 is Zira on this box and could be anything
        elsewhere. Name matching makes the config portable; the index survives
        only as a last resort.
        """
        if not voices:
            return None, ""

        wanted = (self.SAPI_VOICE or "").strip().lower()
        if wanted:
            for voice in voices:
                if wanted in (voice.name or "").lower():
                    return voice.id, voice.name

            _console_print(
                f"[WARN] SAPI voice {self.SAPI_VOICE!r} not installed. "
                f"Available: {', '.join(v.name for v in voices)}. Using index "
                f"{self._fallback_voice_index}.",
                force=True,
            )

        idx = max(0, min(self._fallback_voice_index, len(voices) - 1))
        return voices[idx].id, voices[idx].name

    # -- process-wide instance ------------------------------------------------

    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def shared(cls):
        """
        The one SpeechEngine for this process.

        Constructing this is not free - a COM init plus a SAPI voice
        enumeration - and more importantly two engines in one process can talk
        over each other, since only the queue server's speaking window
        coordinates them. `PhoenixRuntimeManager.__init__` built one that
        `AdvancedTUIManager` then replaced with a proxy, so the TUI process was
        paying for an engine it never spoke through.

        Safe to share across threads: the SAPI handle itself is per-thread
        (see _get_sapi_engine), only the configuration is shared.
        """
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _manage_honorifics(self):
        self.honorifics = False
        sleep(30)
        self.honorifics = True

    def _apply_honorifics(self, audio):
        """Replace 'sir' with random honorifics for personality"""
        replacements = [
            "boss",
            "captain",
            "commander",
            "my lord",
            "your majesty",
            "my liege",
            "your grace",
            "sir",
            "boss",
            "master",
            "sensei",
        ]

        for punctuation in ["", "?", "!", ".", " "]:
            if f" sir{punctuation}" in audio:
                if self.honorifics:
                    replacement = random.choice(replacements)
                    audio = audio.replace(
                        f"sir{punctuation}", f"{replacement}{punctuation}"
                    )
                    threading.Thread(target=self._manage_honorifics).start()
                    break
                else:
                    audio = audio.replace(f"sir{punctuation}", "")
        return audio

    # -- shared speech state -------------------------------------------------

    def _get_queue_manager(self):
        """
        Connect to the queue server once and reuse it.

        Returns None when there is no server (text mode, or the speech engine
        running standalone), in which case self-voice gating and barge-in are
        simply inactive rather than fatal.
        """
        if self._queue_manager is not None or self._queue_unavailable:
            return self._queue_manager
        try:
            from Utils.limbs.queue_manager import QueueManager

            self._queue_manager = QueueManager()
        except Exception as exc:
            self._queue_unavailable = True
            from core.config import AppConfig

            if AppConfig.current_mode != "text":
                _console_print(f"[WARN] Speech state unavailable: {exc}", force=True)
        return self._queue_manager

    def _heartbeat_speaking(self, queue_manager, stop_event):
        """
        Hold the speaking window open while audio plays.

        The window is extended in small steps rather than being opened for an
        estimated duration, so if this process dies mid-sentence the window
        lapses on its own and the microphone reopens. A plain "speaking = True"
        flag would leave the mic gated shut forever.
        """
        while not stop_event.wait(0.2):
            queue_manager.heartbeat_speaking()

    def _should_interrupt(self):
        queue_manager = self._get_queue_manager()
        if queue_manager is None:
            return False
        try:
            return queue_manager.interrupt_requested()
        except Exception:
            return False

    def _mci(self, command: str, want_result: bool = False):
        """Send an MCI command; optionally return its reply string."""
        import ctypes

        winmm = ctypes.windll.winmm
        if not want_result:
            return winmm.mciSendStringW(command, None, 0, None)
        buffer = ctypes.create_unicode_buffer(128)
        winmm.mciSendStringW(command, buffer, 128, None)
        return buffer.value

    def _play_file_interruptible(self, path: str, alias: str) -> bool:
        """
        Play an audio file via MCI without blocking on it.

        The old code used `play {alias} wait`, which parks inside winmm until
        the clip finishes -- there is no moment at which an interrupt could be
        noticed. Polling the transport instead is what makes barge-in possible.
        """
        abs_path = os.path.abspath(path)
        self._mci(f"close {alias}")
        self._mci(f'open "{abs_path}" alias {alias}')

        if self.on_playback_start:
            self.on_playback_start()

        self._mci(f"play {alias}")
        interrupted = False
        try:
            while True:
                mode = self._mci(f"status {alias} mode", want_result=True)
                if mode != "playing":
                    break
                if self._should_interrupt():
                    self._mci(f"stop {alias}")
                    interrupted = True
                    _console_print("[INFO] Playback interrupted by user")
                    break
                time.sleep(0.05)
        finally:
            self._mci(f"close {alias}")

        self._interrupted = interrupted
        return True

    def _init_pygame(self):
        """Initialize pygame mixer if not already done"""
        if not self._pygame_initialized:
            try:
                pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=4096)
                self._pygame_initialized = True
            except Exception as e:
                _console_print(f"⚠️ Pygame init failed: {e}", force=True)
                return False
        return True

    def _cleanup_pygame(self):
        """Cleanup pygame mixer after playback"""
        try:
            pygame.mixer.music.unload()
        except:
            pass

    def _generate_and_play_edge_tts(self, text):
        """Generate and play speech using Edge TTS (synchronous wrapper)"""
        try:
            # Initialize pygame if needed
            if not self._init_pygame():
                _console_print("[WARN] Pygame failed to init inside TTS.", force=True)
                return False

            self._cleanup_pygame()

            import uuid

            # Use unique temp file to avoid locks!
            unique_filename = f"phoenix_speech_{uuid.uuid4().hex[:8]}.mp3"
            unique_path = os.path.join(self._temp_audio_dir, unique_filename)

            async def generate():
                for attempt in range(3):
                    try:
                        import edge_tts

                        communicate = edge_tts.Communicate(
                            text,
                            self.EDGE_VOICE,
                        )
                        await communicate.save(unique_path)
                        return True
                    except Exception as e:
                        if attempt == 2:
                            _console_print(
                                f"[ERROR] Edge TTS Generation Failed: {e}", force=True
                            )
                            raise e
                        _console_print(
                            f"[WARN] Edge TTS attempt {attempt+1} failed ({e}), retrying...",
                            force=True,
                        )
                        await asyncio.sleep(1.0)
                return False

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = False
            try:
                success = loop.run_until_complete(generate())
            finally:
                loop.close()
            if success and os.path.exists(unique_path):
                alias = f"phoenix_{uuid.uuid4().hex[:8]}"
                self._play_file_interruptible(unique_path, alias)
                try:
                    os.remove(unique_path)
                except:
                    pass
                return True
            return False

        except Exception as e:
            _console_print(f"?? Edge TTS error caught outside: {e}", force=True)
            return False

    def speak(self, audio, speed=174):
        """
        Thread-safe text-to-speech.

        Around the actual playback this maintains the shared speaking window
        that the listener uses to recognise Phoenix's own voice, and publishes
        the spoken text so the processor can reject any of it that leaks into a
        transcript anyway.
        """
        # Import here to avoid circular imports
        from Utils.limbs.console_ui import phoenix_said

        queue_manager = self._get_queue_manager()
        speak_success = False
        heartbeat = None
        self._interrupted = False

        try:
            with self.lock:
                # Apply personality (honorifics replacement) BEFORE publishing,
                # so the echo filter compares against what was actually spoken
                # rather than the pre-substitution text.
                audio = self._apply_honorifics(audio)
                phoenix_said(audio)  # TUI output

                if queue_manager is not None:
                    try:
                        queue_manager.remember_tts(audio)
                        queue_manager.clear_interrupt()
                        queue_manager.begin_speaking()
                        self._speaking_stop = threading.Event()
                        heartbeat = threading.Thread(
                            target=self._heartbeat_speaking,
                            args=(queue_manager, self._speaking_stop),
                            daemon=True,
                            name="speaking-window-heartbeat",
                        )
                        heartbeat.start()
                    except Exception as e:
                        _console_print(
                            f"[WARN] Could not open speaking window: {e}", force=True
                        )

                if self.use_edge_tts:
                    if self._generate_and_play_edge_tts(audio):
                        speak_success = True
                    else:
                        _console_print(
                            "[WARN] Edge TTS failed, using fallback voice...",
                            force=True,
                        )

                if not speak_success:
                    speak_success = self._speak_pyttsx3(audio, speed)

        except Exception as e:
            _console_print(f"[ERROR] Speech error: {e}", force=True)
            speak_success = False
        finally:
            if self._speaking_stop is not None:
                self._speaking_stop.set()
                self._speaking_stop = None
            if heartbeat is not None:
                heartbeat.join(timeout=0.5)
            if queue_manager is not None:
                try:
                    # A short tail covers the speaker's decay and room reverb;
                    # the listener's echo gate adds its own margin on top.
                    queue_manager.end_speaking(tail=0.15)
                    queue_manager.clear_interrupt()
                except Exception as e:
                    _console_print(
                        f"[WARN] Error closing speaking window: {e}", force=True
                    )

        if not speak_success and not self._interrupted:
            # Never fail silently. "Phoenix wrote it but did not say it" was
            # indistinguishable from "Phoenix chose not to answer", and the
            # only way to tell them apart was to read the source. A failed
            # utterance is now in the log with the text that was lost.
            _logger.warning(
                "Speech FAILED (engine=%s, voice=%s): %r",
                "edge" if self.use_edge_tts else "sapi5",
                self.voice_name or "default",
                (audio or "")[:80],
            )
            _console_print(
                "[WARN] Phoenix could not speak that line - see logs/", force=True
            )

        return speak_success

    @property
    def was_interrupted(self) -> bool:
        """True if the last utterance was cut short by the user talking over it."""
        return self._interrupted

    def _build_sapi_engine(self, speed):
        """Create and configure one SAPI engine for the calling thread."""
        try:
            import pythoncom

            pythoncom.CoInitialize()
        except Exception:
            pass

        try:
            engine = pyttsx3.init("sapi5")
        except Exception:
            try:
                engine = pyttsx3.init()
            except Exception:
                return None

        try:
            if self.voice_id:
                engine.setProperty("voice", self.voice_id)
            engine.setProperty("rate", speed)
            engine.setProperty("volume", self.volume)
        except Exception:
            pass
        return engine

    def _get_sapi_engine(self, speed):
        """
        Per-thread cached SAPI engine.

        Rebuilding this per utterance cost a COM init and a driver construction
        on the critical path. Cached per thread because a SAPI COM object
        belongs to the apartment that created it, and speech can come from the
        TUI's GlobalSpeechWorker thread or the processor's main thread.
        """
        engine = getattr(self._tls, "engine", None)
        if engine is None:
            engine = self._build_sapi_engine(speed)
            self._tls.engine = engine
            self._tls.rate = speed
        elif getattr(self._tls, "rate", None) != speed:
            try:
                engine.setProperty("rate", speed)
                self._tls.rate = speed
            except Exception:
                pass
        return engine

    def _speak_pyttsx3(self, audio, speed=174):
        """Speak via SAPI5. This is the default engine."""
        engine = self._get_sapi_engine(speed)
        if engine is None:
            return False

        if self.on_playback_start:
            self.on_playback_start()

        # runAndWait() blocks, so barge-in needs a watcher thread to call
        # stop() on the engine from outside. This is the active path whenever
        # tts_engine is "local".
        watcher_stop = threading.Event()

        def _watch_for_interrupt():
            while not watcher_stop.wait(0.05):
                if self._should_interrupt():
                    self._interrupted = True
                    try:
                        engine.stop()
                    except Exception:
                        pass
                    _console_print("[INFO] Playback interrupted by user")
                    return

        watcher = threading.Thread(
            target=_watch_for_interrupt, daemon=True, name="pyttsx3-interrupt-watcher"
        )
        watcher.start()

        try:
            engine.say(audio)
            engine.runAndWait()
        except Exception as exc:
            # A cached engine can be left in a bad state - most often by
            # engine.stop() landing mid-loop during a barge-in. Drop it so the
            # next utterance builds a fresh one rather than failing forever.
            _console_print(f"[WARN] SAPI engine reset after error: {exc}", force=True)
            self._tls.engine = None
            return False
        finally:
            watcher_stop.set()
            watcher.join(timeout=0.3)

        if self._interrupted:
            # stop() during runAndWait leaves the driver's loop flag set on some
            # SAPI builds; the next say() then returns instantly and silently.
            self._tls.engine = None

        return True

    def threadedSpeak(self, audio):
        """
        Starts a thread to call the `speak` method.
        """
        threading.Thread(target=self.speak, args=(audio,)).start()


class VoiceAssistantGUI:

    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.9)
        self.root.attributes("-topmost", True)
        self.setup_transparency()
        self.mic_label = tk.Label(self.root, bg="white")
        self.mic_label.pack()
        self.listen_img_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "img", "green.png"
        )
        self.recognize_img_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "img", "red.png"
        )
        if not os.path.exists(self.listen_img_path):
            _console_print("Error: Listen image not found!", force=True)
        if not os.path.exists(self.recognize_img_path):
            _console_print("Error: Recognize image not found!", force=True)
        self.listen_img = Image.open(self.listen_img_path)
        self.recognize_img = Image.open(self.recognize_img_path)
        max_width = max(4, 4)
        max_height = max(30, 30)
        x_offset = self.root.winfo_screenwidth() - max_width
        y_offset = self.root.winfo_screenheight() - max_height
        self.root.geometry(f"{max_width}x{max_height}+{x_offset}+{y_offset}")

    def hide_listen_image(self):
        self.mic_label.config(image=None)

    def hide_recognize_image(self):
        self.mic_label.config(image=None)

    def setup_transparency(self):
        if self.root.tk.call("tk", "windowingsystem") == "win32":
            self.root.attributes("-topmost", 1)
        elif self.root.tk.call("tk", "windowingsystem") == "x11":
            self.root.attributes("-type", "dock")
        elif self.root.tk.call("tk", "windowingsystem") == "aqua":
            self.root.call(
                "::tk::unsupported::MacWindowStyle",
                "style",
                self.root._w,
                "help",
                "none",
            )
        self.root.wm_attributes("-transparentcolor", "white")

    def show_listen_image(self):
        self.mic_label.config(image=None)
        mic_img = Image.open(self.listen_img_path).convert("RGBA")
        mic_img = mic_img.resize((40, 40), Image.LANCZOS)
        mic_img = ImageTk.PhotoImage(mic_img)  # Convert to Tkinter-compatible image
        self.mic_label.config(image=mic_img)
        self.mic_label.image = mic_img  # Keep a reference to the image object
        self.root.update()

    def show_recognize_image(self):
        self.mic_label.config(image=None)
        recognize_img = self.recognize_img.resize((40, 40), Image.LANCZOS).convert(
            "RGBA"
        )
        recognize_img = ImageTk.PhotoImage(recognize_img)
        self.mic_label.config(image=recognize_img)
        self.mic_label.image = recognize_img  # Keep a reference to the image object
        self.root.update()


class VoiceRecognition:

    def __init__(self, gui):
        self.gui = gui
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1

        # Audio settings for continuous listening
        self.SAMPLE_RATE = 16000
        self.CHUNK_SIZE = 1024
        self.CHANNELS = 1

        # VAD settings
        self.MIN_SILENCE_DURATION = 0.8  # Seconds of silence to trigger processing
        self.MIN_SPEECH_DURATION = 0.3  # Minimum speech duration
        self.ENERGY_THRESHOLD = 150  # RMS energy threshold (raised for fan noise)
        self.SPEECH_CONFIRMATION_CHUNKS = (
            3  # Require N consecutive chunks to confirm speech
        )
        self.MAX_SPEECH_DURATION = 30.0  # Max seconds before auto-processing

        # State management
        self.audio_buffer = []
        self.is_speaking = False
        self.silence_start_time = None
        self.speech_start_time = None
        self.consecutive_speech_chunks = 0  # Track consecutive speech detections
        self.consecutive_silence_chunks = 0  # Track consecutive silence detections

        # Initialize VAD
        self.vad = None
        if VAD_AVAILABLE:
            try:
                self.vad = webrtcvad.Vad()
                self.vad.set_mode(3)  # Most aggressive (human voice only)
            except Exception as e:
                _console_print(f"⚠️ VAD init failed: {e}", force=True)
                self.vad = None

        # Initialize Faster-Whisper for offline recognition
        # Using CUDA/GPU for 5-10x faster transcription!
        self.whisper_model = None
        if WHISPER_AVAILABLE:
            try:
                # Try CUDA (GPU) first for maximum speed
                try:
                    import torch

                    cuda_available = torch.cuda.is_available()
                except ImportError:
                    cuda_available = False

                if cuda_available:
                    _console_print("🚀 Loading Whisper on GPU (CUDA)...")
                    self.whisper_model = WhisperModel(
                        "small", device="cuda", compute_type="float16"
                    )
                    _console_print("✅ Speech recognition ready (GPU accelerated)")
                else:
                    _console_print("💻 Loading Whisper on CPU...")
                    self.whisper_model = WhisperModel(
                        "small", device="cpu", compute_type="int8"
                    )
                    _console_print("✅ Speech recognition ready (CPU mode)")
            except Exception as e:
                _console_print(f"⚠️ Whisper load failed: {e}", force=True)
                _console_print("⚠️ Using Google Speech (requires internet)", force=True)

    def _get_working_microphone_index(self, audio_instance=None):
        """Find the best available microphone, skipping busy ones.

        On Windows, shared-mode audio lets multiple apps open the same mic,
        so a simple 'can I open it?' check isn't enough.  Instead we read
        ~0.5 s of audio from every candidate mic and measure the RMS energy.
        A mic that already carries active audio from a call will have
        noticeably higher energy than an idle mic picking up only ambient
        room noise.  We prefer the *quietest* openable mic (i.e. the one
        NOT already in use by another app).

        Parameters
        ----------
        audio_instance : pyaudio.PyAudio, optional
            Reuse an existing PyAudio instance to avoid the Windows bug
            caused by rapid Pa_Terminate → Pa_Initialize cycles.
        """
        own_instance = audio_instance is None
        p = audio_instance or pyaudio.PyAudio()

        # --- discover default mic ------------------------------------------
        try:
            default_mic = p.get_default_input_device_info()['index']
        except IOError:
            default_mic = None

        # --- enumerate all input devices -----------------------------------
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')

        mics = []
        for i in range(numdevices):
            dev = p.get_device_info_by_host_api_device_index(0, i)
            if dev.get('maxInputChannels') > 0:
                mics.append(i)

        # put default mic first so it wins ties
        if default_mic is not None and default_mic in mics:
            mics.remove(default_mic)
            mics.insert(0, default_mic)

        _console_print(f"🎤 Found {len(mics)} microphone(s), checking availability...")

        # --- probe each mic ------------------------------------------------
        PROBE_RATE = 16000
        PROBE_CHUNK = 1024
        PROBE_CHUNKS = 8  # ~0.5 s at 16 kHz / 1024 chunk
        BUSY_RMS_THRESHOLD = 200  # mics with RMS above this are likely in use

        candidates = []  # list of (mic_index, rms, device_name)

        for mic_index in mics:
            dev_name = p.get_device_info_by_host_api_device_index(0, mic_index).get('name')
            try:
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=PROBE_RATE,
                    input=True,
                    input_device_index=mic_index,
                    frames_per_buffer=PROBE_CHUNK,
                )

                # read several chunks and compute average RMS
                total_energy = 0.0
                for _ in range(PROBE_CHUNKS):
                    raw = stream.read(PROBE_CHUNK, exception_on_overflow=False)
                    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
                    total_energy += np.sqrt(np.mean(samples ** 2))

                avg_rms = total_energy / PROBE_CHUNKS

                stream.stop_stream()
                stream.close()

                candidates.append((mic_index, avg_rms, dev_name))
                _console_print(f"   ✅ '{dev_name}' (idx {mic_index}) — avg RMS: {avg_rms:.1f}")

            except Exception as e:
                _console_print(f"   ❌ '{dev_name}' (idx {mic_index}) — cannot open: {e}")

        if own_instance:
            p.terminate()

        if not candidates:
            _console_print("⚠️ No microphones could be opened!")
            return None

        # --- pick best mic -------------------------------------------------
        # If only one mic, use it regardless
        if len(candidates) == 1:
            chosen = candidates[0]
        else:
            # Separate into "idle" (below threshold) and "busy" (above)
            idle = [c for c in candidates if c[1] < BUSY_RMS_THRESHOLD]
            busy = [c for c in candidates if c[1] >= BUSY_RMS_THRESHOLD]

            if idle:
                # prefer the default mic if it's among the idle ones
                chosen = idle[0]  # already ordered with default first
                if busy:
                    busy_names = ", ".join(f"'{b[2]}'" for b in busy)
                    _console_print(f"🔄 Skipping busy mic(s): {busy_names}")
            else:
                # all mics appear busy — fall back to the quietest one
                chosen = min(candidates, key=lambda c: c[1])
                _console_print("⚠️ All mics appear busy, using quietest one")

        _console_print(f"🎤 Selected: '{chosen[2]}' (idx {chosen[0]}, RMS {chosen[1]:.1f})")
        return chosen[0]

    def _detect_speech(self, audio_chunk):
        """Detect if audio chunk contains speech using VAD and/or energy"""
        # Energy-based detection
        if len(audio_chunk) > 0:
            rms = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
            has_energy = rms > self.ENERGY_THRESHOLD
        else:
            has_energy = False

        # VAD-based detection
        has_vad_speech = False
        if self.vad is not None:
            try:
                # VAD needs 10, 20, or 30ms frames
                frame_duration_ms = 20
                samples_per_frame = int(self.SAMPLE_RATE * frame_duration_ms / 1000)
                audio_bytes = audio_chunk.tobytes()

                # Check multiple frames
                for i in range(0, len(audio_bytes), samples_per_frame * 2):
                    frame = audio_bytes[i : i + samples_per_frame * 2]
                    if len(frame) == samples_per_frame * 2:
                        if self.vad.is_speech(frame, self.SAMPLE_RATE):
                            has_vad_speech = True
                            break
            except Exception as e:
                # Silently ignore VAD errors
                pass

        # Combine both methods (OR logic)
        result = has_energy or has_vad_speech

        # Show when speech starts (once per utterance)
        if result and not self.is_speaking:
            _console_print("🎙️ Voice detected...")

        return result

    def take_command(self):
        """Continuous listening with VAD-based speech detection"""
        # Use Whisper continuous mode if available
        if self.whisper_model is not None:
            return self._continuous_listen_whisper()
        else:
            # Fallback to old speech_recognition method
            return self._fallback_listen()

    def _continuous_listen_whisper(self):
        """Continuous listening with Faster-Whisper (no timeouts)"""
        _console_print("\n🎧 Listening... (speak naturally, pause when done)")
        try:
            # Initialize PyAudio
            audio = pyaudio.PyAudio()
            mic_index = self._get_working_microphone_index(audio)
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=self.CHUNK_SIZE,
            )

            self.gui.show_listen_image()

            # Reset state
            self.audio_buffer = []
            self.is_speaking = False
            self.silence_start_time = None
            self.speech_start_time = None
            self.consecutive_speech_chunks = 0
            self.consecutive_silence_chunks = 0

            chunk_count = 0
            # Continuous listening loop
            while True:
                # Read audio chunk
                audio_data = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                audio_chunk = np.frombuffer(audio_data, dtype=np.int16)
                chunk_count += 1

                # Detect speech
                has_speech = self._detect_speech(audio_chunk)
                current_time = time.time()

                # Update consecutive counters
                if has_speech:
                    self.consecutive_speech_chunks += 1
                    self.consecutive_silence_chunks = 0
                else:
                    self.consecutive_silence_chunks += 1
                    self.consecutive_speech_chunks = 0

                # Require multiple consecutive chunks to confirm speech/silence
                confirmed_speech = (
                    self.consecutive_speech_chunks >= self.SPEECH_CONFIRMATION_CHUNKS
                )
                confirmed_silence = (
                    self.consecutive_silence_chunks >= self.SPEECH_CONFIRMATION_CHUNKS
                )

                if confirmed_speech:
                    # Confirmed speech detected
                    if not self.is_speaking:
                        # Speech just started
                        self.is_speaking = True
                        self.speech_start_time = current_time
                        self.audio_buffer = []
                        self.silence_start_time = None  # Reset silence timer

                    # Add to buffer
                    self.audio_buffer.append(audio_chunk)

                    # Check if speech duration exceeded max
                    speech_duration_so_far = current_time - self.speech_start_time
                    if speech_duration_so_far >= self.MAX_SPEECH_DURATION:
                        _console_print("⏱️ Max duration reached, processing...")
                        stream.stop_stream()
                        stream.close()
                        audio.terminate()

                        self.gui.show_recognize_image()
                        _console_print("🧠 Processing speech...")
                        result = self._transcribe_buffer()
                        self.gui.hide_listen_image()
                        return result

                elif confirmed_silence and self.is_speaking:
                    # Confirmed silence during speech
                    if self.silence_start_time is None:
                        self.silence_start_time = current_time

                    # Continue buffering
                    self.audio_buffer.append(audio_chunk)

                    # Check if silence duration exceeded threshold
                    silence_duration = current_time - self.silence_start_time
                    if silence_duration >= self.MIN_SILENCE_DURATION:
                        # Silence long enough, process the speech
                        stream.stop_stream()
                        stream.close()
                        audio.terminate()

                        # Check if speech is long enough
                        speech_duration = (
                            len(self.audio_buffer) * self.CHUNK_SIZE / self.SAMPLE_RATE
                        )

                        if speech_duration >= self.MIN_SPEECH_DURATION:
                            self.gui.show_recognize_image()
                            _console_print("🧠 Processing speech...")

                            # Transcribe
                            result = self._transcribe_buffer()
                            self.gui.hide_listen_image()
                            return result
                        else:
                            # Too short, ignore
                            self.gui.hide_listen_image()
                            return ""
                elif self.is_speaking:
                    # Transitional state - buffer audio but don't change state
                    self.audio_buffer.append(audio_chunk)

        except Exception as e:
            _console_print(f"\n⚠️ Listening error: {e}", force=True)
            try:
                stream.stop_stream()
                stream.close()
                audio.terminate()
            except:
                pass
            self.gui.hide_listen_image()
            return ""

    def _transcribe_buffer(self):
        """Transcribe buffered audio with Faster-Whisper"""
        try:
            # Combine all chunks
            audio_array = np.concatenate(self.audio_buffer)

            # Calculate duration for display
            duration = len(audio_array) / self.SAMPLE_RATE

            # Convert to float32 normalized to [-1.0, 1.0]
            audio_float = audio_array.astype(np.float32) / 32768.0

            # Transcribe with Faster-Whisper
            segments, info = self.whisper_model.transcribe(
                audio_float,
                language="en",
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=int(self.MIN_SILENCE_DURATION * 1000),
                    threshold=0.3,
                ),
            )

            # Combine all segments
            transcription = " ".join([segment.text for segment in segments]).strip()

            # Show what was heard (the key user request!)
            if transcription:
                _console_print(f'\n👤 You said: "{transcription}"')
            else:
                _console_print("❓ Couldn't understand that")

            return transcription

        except Exception as e:
            _console_print(f"⚠️ Transcription error: {e}", force=True)
            return ""

    def _fallback_listen(self):
        """Fallback to old speech_recognition method"""
        mic_index = self._get_working_microphone_index()
        with sr.Microphone(device_index=mic_index) as source:
            self.gui.show_listen_image()
            _console_print(">>>", end="\r")
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source, 0, 8)

        try:
            self.gui.show_recognize_image()
            _console_print("<<<", end="\r")
            query = self.recognizer.recognize_google(audio, language="en-in")
        except Exception as e:
            _console_print("<!>", end="\r")
            self.gui.hide_listen_image()
            return ""
        return query


"---------------EXTRA----------------"


def music(Utility):
    Utility.intrOmsC()
    Utility.rockMsc(0.5)


if __name__ == "__main__":
    root = tk.Tk()
    gui = VoiceAssistantGUI(root)
    recog = VoiceRecognition(gui)
    spk = SpeechEngine()
    # utils = Utility(spk, recog)
    # utils.open_setting()
    # utils.get_window("Code.exe", "HelperPHNX.py")
    # spk.speak("oohoom..!")
    # spk.speak("What's up!")
    # recog.take_command()
    spk.speak("Yoi, I'm back , you can continue your business now.", 169)
    # music(recog)
    # print("oj")
    # opn = OpenAppHandler(recog)
    # utils.speak("hello, sir")
    # utils.desKtoP(2)
    # utils.open_brave()
    # spk.speak("hello there!, It's Phoenix-The Desktop Assistant.")
    # sleep(1)
    # # spk.speak(
    # #     "So, Normally Makbook provides Siri, Samsung Provides bixby, but windows doesn't provide any voice assistant like that.. "
    # # )
    # # sleep(1)
    # # spk.speak(
    # #     "there was one cortana before, but they discontinued that project, it didn't work."
    # # )
    # # sleep(1)
    # spk.speak(
    #     "i totally work on voice command. i do small tasks like open-close any applications,maximize-minimize tabs, switching apps and switching between desktops."
    # )
    # sleep(1)
    # spk.speak(
    #     "Also i can adjust device brightness and volume. and ofcourse as a desktop assistant i have to play desired songs for you, if you want to listen song and don't know the song name? no worries i can suggest you song just ask me."
    # )
    # sleep(1)
    # spk.speak(
    #     "just like google assistant i can also set alarms, reminders, timers etc."
    # )
    # sleep(1)
    # spk.speak(
    #     "basically google assistant is not supported by the windows, and moin was working on me so he added these functionality in me."
    # )

    # sleep(1)
    # spk.speak(
    #     "i keep track of battery status..like for some specific stages i keep remind you about the battery status and after one stage i will remind you to plug in the charger."
    # )
