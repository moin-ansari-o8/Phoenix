import json
import os
from dataclasses import dataclass, field


@dataclass
class QueueConfig:
    host: str = "127.0.0.1"
    port: int = 50000
    authkey: bytes = b"phoenix_audio_queue"


@dataclass
class RuntimeConfig:
    queue: QueueConfig = field(default_factory=QueueConfig)


class AppConfig:
    name = "Igris"
    user_name = "User"
    user_tags = ["Sir", "Boss"]
    modes = ["voice", "text"]
    current_mode = "voice"
    voice = "en-GB-RyanNeural"
    wake_words = ["igris", "hey igris"]
    fallback_voice_index = 1
    sapi_voice = "Zira"  # matched case-insensitively against the SAPI voice name
    tts_engine = "sapi5"
    show_routing = True  # print "-> tool arg" for each decision
    # "auto" (default) probes reachability and behaves as offline when there is
    # no network; true forces offline; false always allows. See
    # Utils/limbs/connectivity.py.
    offline_mode = "auto"
    # Irreversible actions (shutdown, restart, hibernate, taskkill python) ask
    # for a spoken confirmation first. See Utils/limbs/confirm_gate.py.
    confirm_destructive = True
    confirm_timeout_seconds = 30
    bg_progs = {
        "battery_check": False,
        "time_check": False,
        "todo_check": False,
        "hydration_reminder": False,
    }
    memory = {
        # NOTE: no "auto_save" key. It was parsed here and read by nothing for
        # its whole life; "persist_chatlog" is the switch that actually governs
        # whether conversations are written to disk.
        "announce_saves": False,
        "context_turns": 8,
        "max_remember_entries": 200,
        "persist_chatlog": True,
        "max_chatlog_entries": 500,
    }
    web = {
        "enabled": True,
        "max_results": 5,
        "fetch_timeout_seconds": 8,
        "max_context_chars": 3000,
    }
    # Listening pipeline. echo_mode is the one you actually change day to day:
    #   "gate" - speakers. The mic is gated while Phoenix talks so it cannot
    #            hear itself. Barge-in is off, because it would trigger on
    #            Phoenix's own voice.
    #   "open" - headphones. The mic never hears Phoenix, so the gate is off,
    #            listening is truly full-duplex and barge-in is enabled.
    audio = {
        "echo_mode": "gate",
        "vad_threshold": 0.5,
        # Tolerance for a mid-sentence pause is hangover_ms + stitch_window_ms,
        # but only a sentence that actually continues pays the stitch window; a
        # finished command still goes out after hangover_ms. Raising hangover_ms
        # alone would tax every command equally. See CapturePipeline's docstring.
        "hangover_ms": 800,
        "stitch_window_ms": 900,
        "min_voiced_ms": 400,
        # Must stay comfortably above hangover + stitch: a slow speaker running
        # past this cap gets truncated mid-word, which is worse than being cut
        # off at a pause.
        "max_utterance_ms": 20000,
        "pre_roll_ms": 300,
        "noise_multiplier": 3.0,
        "noise_absolute_min": 120.0,
        "barge_in": True,
        # null = auto-select a mic that is actually delivering audio, and move
        # to another one if the current mic goes dead (a call taking it over).
        # Set an integer device index to pin one and disable switching.
        "input_device": None,
        "mic_silence_timeout_seconds": 20,
        # How long Phoenix keeps answering without a wake word after being
        # addressed. Refreshed on every answered turn; expiring returns it to
        # dormant, where it transcribes but does not respond.
        "followup_window_seconds": 30,
    }
    # Speaker verification. A convenience filter, NOT a security control - a
    # recording of the owner passes it. See Utils/limbs/speaker_id.py.
    #
    # mode "log"  - score every utterance, suppress nothing. THE DEFAULT.
    # mode "gate" - actually drop utterances that score below threshold.
    #
    # Stay in "log" until you have looked at real scores for yourself and for
    # other people in the room, then set the threshold from that data. Guessing
    # it is how this ends up ignoring you when you have a cold.
    security = {
        "speaker_verification": {
            "enabled": True,
            "mode": "log",
            "threshold": 0.72,
            # Below this there is not enough voiced audio for a stable
            # embedding, and the utterance passes unjudged.
            "min_duration_s": 0.8,
        }
    }
    # base.en, not small.en: Whisper pads every input to a 30s mel window, so
    # encoder cost barely depends on how long the utterance actually is.
    # Measured on this machine for a 3s command: base.en 0.74s vs small.en
    # 2.36s, for identical output on the test phrase.
    # Mirrors the ai_manager block of config.json. AIDecisionMaker used to open
    # and parse config.json itself, making two independent readers of the same
    # file that could disagree - and its path was relative, so it sometimes read
    # nothing at all and fell back to a model that does not fit in 4 GB.
    ai_manager = {
        "current_mode": "local",
        "router_mode": "json",
        "router_model": "llama3.2:latest",
        "answer_model": "llama3.2:latest",
    }
    # TUI appearance. "dark" | "light" | "auto" (follows Windows). See core/theme.py.
    ui = {"theme": "auto"}
    # Speak each sentence as the model writes it, instead of waiting for the
    # whole answer. Measured: first word at ~0.8 s instead of ~4.9 s.
    stream_answers = True
    stt = {
        "model": "base.en",
        "device": "auto",  # "auto" | "cpu" | "cuda"
        "beam_size": 1,
        "max_no_speech_prob": 0.6,
        "min_avg_logprob": -1.0,
    }

    # SAPI5 is the default and the tested path. Piper was evaluated and dropped:
    # it shells out per utterance to write a .wav, which is too slow for a
    # conversational turn and was intermittently glitchy. Edge is kept because
    # it is the only better-sounding option, but it is a CLOUD endpoint and so
    # can never be the default for a local-first assistant.
    TTS_ENGINES = ("sapi5", "edge")
    # Historic value. It matched no branch in SpeechEngine and fell through to
    # SAPI5 by accident; that turned out to be the wanted engine, so it is kept
    # as an explicit alias rather than a silent fallthrough.
    TTS_ALIASES = {"local": "sapi5", "pyttsx3": "sapi5", "windows": "sapi5"}

    @classmethod
    def _resolve_tts_engine(cls, value):
        """Map and validate tts_engine, warning instead of degrading silently."""
        name = str(value or "").strip().lower()
        name = cls.TTS_ALIASES.get(name, name)
        if name in cls.TTS_ENGINES:
            return name
        print(
            f"[WARN] Unknown tts_engine {value!r} in config.json. "
            f"Expected one of {', '.join(cls.TTS_ENGINES)} "
            f"(aliases: {', '.join(cls.TTS_ALIASES)}). Using 'sapi5'.",
            flush=True,
        )
        return "sapi5"

    @classmethod
    def load(cls):
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cls.tts_engine = cls._resolve_tts_engine(
                data.get("tts_engine", cls.tts_engine)
            )
            cls.show_routing = bool(data.get("show_routing", cls.show_routing))
            cls.offline_mode = data.get("offline_mode", cls.offline_mode)
            cls.confirm_destructive = bool(
                data.get("confirm_destructive", cls.confirm_destructive)
            )
            cls.confirm_timeout_seconds = float(
                data.get("confirm_timeout_seconds", cls.confirm_timeout_seconds)
            )
            cls.stream_answers = bool(
                data.get("stream_answers", cls.stream_answers)
            )

            # An offline assistant must not be one config typo away from a
            # cloud model. `ollama list` on this box shows several ":cloud"
            # tags; picking one silently turns every answer into a network call.
            for key in ("router_model", "answer_model"):
                model = str(data.get("ai_manager", {}).get(key, ""))
                if ":cloud" in model:
                    print(
                        f"[WARN] ai_manager.{key} is {model!r}, a CLOUD model. "
                        f"Phoenix is local-first; this sends every query to a "
                        f"remote endpoint.",
                        flush=True,
                    )

            # Parse modes based on index
            raw_modes = data.get("modes", ["[0]voice", "[1]text"])
            modes_list = [m.split("]", 1)[1].lower().strip() if "]" in m else m.lower().strip() for m in raw_modes]
            cls.modes = modes_list
            current_mode_val = data.get("current_mode", 0)
            current_mode_idx = int(current_mode_val) if str(current_mode_val).isdigit() else 0
            if 0 <= current_mode_idx < len(modes_list):
                cls.current_mode = modes_list[current_mode_idx]

            user_data = data.get("user", {})
            cls.user_name = user_data.get("name", cls.user_name)
            cls.user_tags = user_data.get("tags", cls.user_tags)

            # Parse profiles based on index
            raw_profiles = data.get("profiles", ["[0]Phoenix", "[1]Igris"])
            profiles_list = [p.split("]", 1)[1].lower().strip() if "]" in p else p.lower().strip() for p in raw_profiles]
            active_profile_val = data.get("active_profile", 0)
            
            if isinstance(active_profile_val, str) and not active_profile_val.isdigit():
                active = active_profile_val.lower()
            else:
                active_profile_idx = int(active_profile_val) if str(active_profile_val).isdigit() else 0
                active = profiles_list[active_profile_idx] if 0 <= active_profile_idx < len(profiles_list) else "phoenix"

            # Use the "profile" key
            profile = data.get("profile", {}).get(active, {})
            cls.name = profile.get("name", cls.name)
            cls.voice = profile.get("voice", cls.voice)
            cls.wake_words = profile.get("wake_words", cls.wake_words)
            cls.fallback_voice_index = profile.get(
                "fallback_voice_index", cls.fallback_voice_index
            )
            # SAPI voice picked by NAME. fallback_voice_index is an offset into
            # a registry enumeration whose order differs per install, so index 1
            # is Zira here and something else on any other machine. The index is
            # kept only as a last resort when no name matches.
            cls.sapi_voice = profile.get("sapi_voice", cls.sapi_voice)

            # Load background programs toggle
            bg_progs_data = data.get("bg_progs", {})
            cls.bg_progs = {
                "battery_check": bg_progs_data.get("battery_check", True),
                "time_check": bg_progs_data.get("time_check", True),
                "todo_check": bg_progs_data.get("todo_check", True),
                "hydration_reminder": bg_progs_data.get("hydration_reminder", True),
            }

            mem = data.get("memory", {})
            cls.memory = {
                "announce_saves": mem.get("announce_saves", False),
                "context_turns": mem.get("context_turns", 8),
                "max_remember_entries": mem.get("max_remember_entries", 200),
                "persist_chatlog": mem.get("persist_chatlog", True),
                "max_chatlog_entries": mem.get("max_chatlog_entries", 500),
            }

            audio_data = data.get("audio", {})
            cls.audio = {**cls.audio, **audio_data}
            if cls.audio.get("echo_mode") not in ("gate", "open"):
                cls.audio["echo_mode"] = "gate"

            stt_data = data.get("stt", {})
            cls.stt = {**cls.stt, **stt_data}

            cls.ai_manager = {**cls.ai_manager, **data.get("ai_manager", {})}
            cls.ui = {**cls.ui, **data.get("ui", {})}

            # Merged one level deep so config.json can override a single key
            # (say, just the threshold) without having to restate the block.
            security_data = data.get("security", {})
            cls.security = {
                **cls.security,
                **{k: v for k, v in security_data.items() if k != "speaker_verification"},
                "speaker_verification": {
                    **cls.security["speaker_verification"],
                    **security_data.get("speaker_verification", {}),
                },
            }
            if cls.security["speaker_verification"].get("mode") not in ("log", "gate"):
                cls.security["speaker_verification"]["mode"] = "log"

            web_data = data.get("web", {})
            cls.web = {
                "enabled": web_data.get("enabled", True),
                "max_results": web_data.get("max_results", 5),
                "fetch_timeout_seconds": web_data.get("fetch_timeout_seconds", 8),
                "max_context_chars": web_data.get("max_context_chars", 3000),
            }


AppConfig.load()
