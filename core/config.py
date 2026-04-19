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

    @classmethod
    def load(cls):
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cls.tts_engine = data.get("tts_engine", cls.tts_engine)
            cls.modes = data.get("modes", cls.modes)
            cls.current_mode = data.get("current_mode", cls.current_mode)

            user_data = data.get("user", {})
            cls.user_name = user_data.get("name", cls.user_name)
            cls.user_tags = user_data.get("tags", cls.user_tags)

            active = data.get("active_profile", "igris")
            profile = data.get("profiles", {}).get(active, {})
            cls.name = profile.get("name", cls.name)
            cls.voice = profile.get("voice", cls.voice)
            cls.piper_voice = profile.get("piper_voice", cls.piper_voice)
            cls.wake_words = profile.get("wake_words", cls.wake_words)
            cls.fallback_voice_index = profile.get(
                "fallback_voice_index", cls.fallback_voice_index
            )


AppConfig.load()
