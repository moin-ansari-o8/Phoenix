from dataclasses import dataclass, field


@dataclass
class QueueConfig:
    host: str = "127.0.0.1"
    port: int = 50000
    authkey: bytes = b"phoenix_audio_queue"


@dataclass
class RuntimeConfig:
    queue: QueueConfig = field(default_factory=QueueConfig)
