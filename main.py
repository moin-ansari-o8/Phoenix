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
from core.trace import parse as parse_trace

from Utils.runners.manager import RuntimeConfig, PhoenixRuntimeManager
from Utils.runners.battery_monitor import BatteryMonitorConfig
from Utils.runners.time_monitor import TimeMonitorConfig
from Utils.runners.voice_processor import VoiceProcessorConfig


import pythoncom


class GlobalSpeechWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="global-speech-worker")
        self.q = queue.Queue()
        self.engine = None
        self._current_speech = ""

    def run(self):
        import Utils.limbs.console_ui

        Utils.limbs.console_ui.phoenix_said = lambda x: None

        from Utils.limbs.assistant_io import SpeechEngine

        try:
            pythoncom.CoInitialize()
        except Exception:
            pass

        try:
            self.engine = SpeechEngine.shared()
        except Exception:
            return

        while True:
            item = self.q.get()
            if item is None:
                break

            text, event, tui = item

            # Set callback so text appears when audio starts playing
            def _on_play(t=text, u=tui):
                if u:
                    u.log_chat("Phoenix", t)

            self.engine.on_playback_start = _on_play

            try:
                self._current_speech = text
                self.engine.speak(text)
            except Exception:
                # If speak fails, still show the text
                if tui:
                    tui.log_chat("Phoenix", text)
            finally:
                self.engine.on_playback_start = None
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
        # Every style the TUI uses is named in core/theme.py. Nothing here
        # writes a colour inline - a style that is not in the palette is, by
        # definition, outside it, which is how the old six-hue rainbow grew.
        from core.theme import build_theme, get_setting, resolve_mode

        self.theme_mode = resolve_mode(get_setting())
        self.theme = build_theme(get_setting())
        self.console = Console(theme=self.theme)

        # Mirrors the processor's wake gate, updated from [VOICE_STATE] traces.
        # Display only - the processor owns the real state.
        self._awake = False

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
            # Dormant means Phoenix is hearing but not answering. Show it, or
            # the user has no way to tell that state from a broken mic.
            if getattr(self, "_awake", False):
                self._set_status("Listening (follow-up)...")
            else:
                self._set_status(f"Listening - say '{AppConfig.wake_words[0]}'...")

    def _set_status(self, status: str):
        with self._ui_lock:
            if status == self._current_status:
                return
            self._current_status = status
            self._render_status()

    def log_route(self, label):
        """Show which tool handled the query, e.g. '-> search_web population of france'.

        Borrowed from IGRS, whose classifier emitted a visible 'general <query>' /
        'realtime <query>' prefix. Seeing the decision makes misroutes obvious
        instead of silent. Toggle with "show_routing" in core/config.json.
        """
        with self._ui_lock:
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()
            self.console.print(Text(f"  -> {label}", style="route"))
            self._render_status()

    def _handle_trace(self, event):
        """
        Render one structured trace from the voice processor.

        One dispatch table, one place. The old design string-matched tags in
        two files that then drifted apart - manager.py was still matching emoji
        prefixes that no longer existed, so it had quietly stopped working.
        """
        kind = event.get("event", "")
        text = (event.get("text") or "").strip()

        if kind == "fatal":
            self.log_fatal(text)
            return

        if kind == "voice_state":
            state = text.lower()
            if state == "listening":
                self._set_idle_status()
            elif state == "processing":
                self._set_status("Processing...")
            elif state == "interrupt":
                self._set_status("Interrupted - listening...")
            elif state == "awake":
                self._awake = True
                self._set_idle_status()
            elif state == "dormant":
                self._awake = False
                self._set_idle_status()
            return

        if kind == "heard":
            if text and text != "<empty>":
                self.log_chat("You", text)
            self._set_idle_status()
            return

        if kind == "ignored_heard":
            if text and text != "<empty>":
                self.log_chat("You", text, is_ignored=True)
            self._set_idle_status()
            return

        if kind in ("discarded", "self_echo"):
            # Audio the pipeline captured but deliberately did not act on.
            # Shown so that silence stays visibly silent, rather than Whisper's
            # invented "Thank you." looking like real user input.
            if AppConfig.show_routing and text:
                label = "self-voice ignored" if kind == "self_echo" else "discarded"
                self.log_route(f"{label}: {text}")
            self._set_idle_status()
            return

        # Diagnostics. All render the same way - a dim "-> ..." line under
        # show_routing - but they are listed explicitly rather than caught by a
        # fallback, so a new event type fails the test in tests/test_trace.py
        # instead of vanishing silently, which is how the old parsers rotted.
        #   stt         transcription timing
        #   gate        how long the follow-up window has left
        #   intent      whether routing matched
        #   speaker     speaker-verification score (see speaker_id.py)
        #   repaired    lexicon fixes, e.g. "phonix -> phoenix"
        #   song_rerank a second STT pass changed the chosen song
        if kind in ("stt", "gate", "intent", "speaker", "repaired", "song_rerank"):
            if AppConfig.show_routing and text:
                prefix = {
                    "repaired": "repaired: ",
                    "song_rerank": "song: ",
                    "speaker": "speaker: ",
                }.get(kind, "")
                self.log_route(f"{prefix}{text}")
            if kind == "intent":
                self._set_idle_status()
            return

        if kind == "processing":
            self._set_status("Thinking...")
            return

    def log_fatal(self, detail):
        """Surface a dead subprocess. Silence here reads as a hang, not a crash."""
        with self._ui_lock:
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()
            self.console.print(
                Text(f"  [!] Voice processor stopped: {detail}", style="error")
            )
            self.console.print(
                Text("      Details in logs/phoenix_processor.log", style="hint")
            )
            self._current_status = "Voice processor stopped - restart Phoenix"
            self._render_status()

    def log_chat(self, speaker, message, is_ignored=False):
        with self._ui_lock:
            # Clear status line
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()

            timestamp = datetime.now().strftime("%H:%M:%S")
            time_txt = Text(f"[{timestamp}] ", style="time")

            if is_ignored:
                # Same quiet grey as other secondary text. Yellow made every
                # cough and passing conversation look like a warning.
                speaker_txt = Text("heard: ", style="ignored_label")
                msg_txt = Text(message, style="ignored")
            elif speaker == "You":
                user_name = getattr(AppConfig, "user_name", "User")
                speaker_txt = Text(f"{user_name}: ", style="user")
                msg_txt = Text(message, style="said")
            else:
                speaker_txt = Text(AppConfig.name + ": ", style="phoenix")
                msg_txt = Text(message, style="reply")

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
            from Utils.limbs.action_utilities import (
                Utility,
                OpenAppHandler,
                CloseAppHandler,
            )
            from Utils.limbs.time_handlers import (
                TimerHandle,
                AlarmHandle,
                ReminderHandle,
                ScheduleHandle,
            )
            from Utils.limbs.command_processor import PhoenixAssistant

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

        # Header. The name in the accent, everything else on the grey ramp,
        # and one hairline rule instead of two heavy bars: the old block of
        # bold-magenta heavy bar was the loudest thing on screen and carried no
        # information. What replaces it is information - which engines are
        # actually loaded, which is the thing you want to know at a glance.
        from core.theme import safe_chars

        glyph = safe_chars()
        width = min(self.console.width, 72)
        self.console.print()
        header = Text()
        header.append(AppConfig.name, style="banner")
        header.append(f"   {AppConfig.user_name}", style="muted")
        header.append(
            f"   {AppConfig.stt['model']} {glyph['sep']} "
            f"{AppConfig.ai_manager['answer_model'].split(':')[0]} {glyph['sep']} "
            f"{AppConfig.tts_engine}",
            style="hint",
        )
        self.console.print(header)
        self.console.print(Text(glyph["rule"] * width, style="rule"))
        self.console.print()

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

                        # Structured traces first. A line either carries the
                        # sentinel and is an event, or it is ordinary output -
                        # there is no guessing, so a stray print() in 3,500
                        # lines of action code can no longer be mistaken for
                        # one. See core/trace.py.
                        parsed = parse_trace(clean)
                        if parsed is not None:
                            self._handle_trace(parsed)
                            continue

                        if clean.startswith("[FATAL]"):
                            self.log_fatal(clean.removeprefix("[FATAL]").strip())
                            continue

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
                            elif state == "interrupt":
                                self._set_status("Interrupted - listening...")
                            elif state == "awake":
                                # Follow-ups need no wake word until this expires.
                                self._awake = True
                                self._set_idle_status()
                            elif state == "dormant":
                                self._awake = False
                                self._set_idle_status()
                            elif state == "detected":
                                pass
                            continue

                        # Audio the listener captured but deliberately did not
                        # act on. Shown so silence stays visibly silent instead
                        # of the old behaviour where Whisper's invented
                        # "Thank you." looked like real user input.
                        if clean.startswith("[DISCARDED]") or clean.startswith(
                            "[SELF_ECHO]"
                        ):
                            if AppConfig.show_routing:
                                label = (
                                    "self-voice ignored"
                                    if clean.startswith("[SELF_ECHO]")
                                    else "discarded"
                                )
                                detail = clean.split("]", 1)[1].strip()
                                self.log_route(f"{label}: {detail}")
                            self._set_idle_status()
                            continue

                        if clean.startswith("[STT]"):
                            if AppConfig.show_routing:
                                self.log_route(clean.removeprefix("[STT]").strip())
                            continue

                        if clean.startswith("[GATE]"):
                            if AppConfig.show_routing:
                                self.log_route(clean.removeprefix("[GATE]").strip())
                            continue

                        # The listener goes back to "listening" the moment it
                        # hands off an utterance -- which is now literally true,
                        # the mic never stops. These two mark the separate
                        # window where the processor is still working on it.
                        if clean.startswith("[PROCESSING]"):
                            self._set_status("Thinking...")
                            continue

                        if clean.startswith("[INTENT]"):
                            self._set_idle_status()
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


def _configure_logging():
    """Send all library logging to a file, never to the chat.

    tool_registry / web_search / ai_manager use logging.info/warning for
    diagnostics. Without this they print straight into the conversation, e.g.
    the optional queue server's absence appeared after every reply.

    Delegates to core.logging_setup so every Phoenix process shares one
    format, one directory and one level. See that module for what the five
    competing configurations used to do.
    """
    from core.logging_setup import setup_logging

    setup_logging("tui")

    # A Windows console still on cp1252 raises UnicodeEncodeError on any glyph
    # outside it - box drawing in the header, and every Hindi/Gujarati word the
    # lexicon repairs. That exception kills the printing thread rather than
    # showing a wrong character, so force UTF-8 and degrade to "?" if a
    # character truly cannot be represented.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main():
    _configure_logging()
    manager = AdvancedTUIManager(config=RUNTIME_CONFIG)
    manager.run_forever()


if __name__ == "__main__":
    main()
