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
    piper_voice = "en_US-ryan-medium"  # Fallback default
    wake_words = ["igris", "hey igris"]
    fallback_voice_index = 1
    tts_engine = "edge"  # default to edge
    show_routing = True  # print "-> tool arg" for each decision
    bg_progs = {
        "battery_check": False,
        "time_check": False,
        "todo_check": False,
        "hydration_reminder": False,
    }
    memory = {
        "auto_save": True,
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

    @classmethod
    def load(cls):
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cls.tts_engine = data.get("tts_engine", cls.tts_engine)
            cls.show_routing = bool(data.get("show_routing", cls.show_routing))

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
            cls.piper_voice = profile.get("piper_voice", cls.piper_voice)
            cls.wake_words = profile.get("wake_words", cls.wake_words)
            cls.fallback_voice_index = profile.get(
                "fallback_voice_index", cls.fallback_voice_index
            )

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
                "auto_save": mem.get("auto_save", True),
                "announce_saves": mem.get("announce_saves", False),
                "context_turns": mem.get("context_turns", 8),
                "max_remember_entries": mem.get("max_remember_entries", 200),
                "persist_chatlog": mem.get("persist_chatlog", True),
                "max_chatlog_entries": mem.get("max_chatlog_entries", 500),
            }

            web_data = data.get("web", {})
            cls.web = {
                "enabled": web_data.get("enabled", True),
                "max_results": web_data.get("max_results", 5),
                "fetch_timeout_seconds": web_data.get("fetch_timeout_seconds", 8),
                "max_context_chars": web_data.get("max_context_chars", 3000),
            }


AppConfig.load()
