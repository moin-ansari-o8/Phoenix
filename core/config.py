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
    voice = "en-GB-RyanNeural"
    wake_words = ["igris", "hey igris"]

    @classmethod
    def load(cls):
        config_path = os.path.join(os.path.dirname(__file__), "config.json")    
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            user_data = data.get("user", {})
            cls.user_name = user_data.get("name", cls.user_name)
            cls.user_tags = user_data.get("tags", cls.user_tags)

            active = data.get("active_profile", "igris")
            profile = data.get("profiles", {}).get(active, {})
            cls.name = profile.get("name", cls.name)
            cls.voice = profile.get("voice", cls.voice)
            cls.wake_words = profile.get("wake_words", cls.wake_words)

AppConfig.load()
