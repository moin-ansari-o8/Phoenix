"""Utilities helpers package (migrated from legacy helpers/)."""

from .assistant_io import SpeechEngine, VoiceRecognition, VoiceAssistantGUI
from .action_utilities import Utility, OpenAppHandler, CloseAppHandler
from .command_processor import PhoenixAssistant
from .queue_manager import QueueManager, AudioChunk, create_audio_chunk
from .time_handlers import TimerHandle, AlarmHandle, ReminderHandle, ScheduleHandle
from .time_runner import (
    HandleTimeBasedFunctions,
    TimerManager,
    AlarmManager,
    ReminderManager,
    ScheduleManager,
)
from .personal_manager import PersonalManager

__all__ = [
    'SpeechEngine', 'VoiceRecognition', 'VoiceAssistantGUI',
    'Utility', 'OpenAppHandler', 'CloseAppHandler',
    'PhoenixAssistant',
    'QueueManager', 'AudioChunk', 'create_audio_chunk',
    'TimerHandle', 'AlarmHandle', 'ReminderHandle', 'ScheduleHandle',
    'HandleTimeBasedFunctions', 'TimerManager', 'AlarmManager', 'ReminderManager', 'ScheduleManager',
    'PersonalManager',
]
