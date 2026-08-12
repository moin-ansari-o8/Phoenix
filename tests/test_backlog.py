"""
Two fixes for the same real failure: Phoenix hearing the music it plays.

Observed in a live session on 2026-08-12. Phoenix played a song on YouTube,
the microphone picked it up through the speakers, and because the follow-up
window was open every mangled lyric was treated as a command:

    19:31:28  Transcribed: 'waalakhua, ari waalakhua'
    19:31:36  wiki -> 200 ... grokipedia -> 200 ... brave -> 200

It ran a four-engine web search on song lyrics. Meanwhile transcription times
climbed to 21.0s, 20.2s, 18.9s as the single-threaded loop ground through a
backlog of music, so real questions were answered half a minute late, over the
song - which is what "sometimes she speaks, sometimes she doesn't" actually was.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe -m pytest W:\\workplace-1\\Phoenix\\tests\\test_backlog.py -q
"""

import os
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import AppConfig  # noqa: E402
from Utils.limbs.action_registry import MEDIA_ACTIONS  # noqa: E402


# --------------------------------------------------------------- stale audio


class FakeChunk:
    def __init__(self, age_seconds, duration=2.0):
        self.timestamp = time.time() - age_seconds
        self.duration = duration


def make_checker(max_age=12):
    """
    The staleness check, isolated from VoiceProcessor's heavy __init__ (Tk,
    Whisper, a queue-server connection). Bound as a real method so the code
    under test is the shipped code.
    """
    from Utils.runners.voice_command_processor import VoiceProcessor

    stub = types.SimpleNamespace(chunks_dropped=0, _runtime_trace=lambda *a: None)
    original = AppConfig.audio.get("max_chunk_age_seconds", 12)
    AppConfig.audio["max_chunk_age_seconds"] = max_age
    checker = VoiceProcessor._is_stale.__get__(stub, VoiceProcessor)
    return checker, stub, original


def restore(original):
    AppConfig.audio["max_chunk_age_seconds"] = original


def test_fresh_audio_is_processed():
    checker, _, original = make_checker(12)
    try:
        assert checker(FakeChunk(0.0)) is False
        assert checker(FakeChunk(5.0)) is False
        assert checker(FakeChunk(11.9)) is False
    finally:
        restore(original)


def test_stale_audio_is_dropped():
    """A question from 30 seconds ago has missed its moment."""
    checker, stub, original = make_checker(12)
    try:
        assert checker(FakeChunk(12.1)) is True
        assert checker(FakeChunk(30.0)) is True
        assert checker(FakeChunk(120.0)) is True
        assert stub.chunks_dropped == 3
    finally:
        restore(original)


def test_dropping_can_be_disabled():
    """0 means never drop - for anyone who would rather have a late answer."""
    checker, _, original = make_checker(0)
    try:
        assert checker(FakeChunk(600.0)) is False
    finally:
        restore(original)


def test_a_drop_is_announced_not_silent():
    """Silently discarding audio would look like the mic had died."""
    checker, stub, original = make_checker(12)
    traced = []
    stub._runtime_trace = lambda tag, msg: traced.append((tag, msg))
    try:
        checker(FakeChunk(40.0))
        assert traced, "dropping audio emitted no trace"
        assert traced[0][0] == "STALE"
        assert "40s" in traced[0][1] or "40" in traced[0][1]
    finally:
        restore(original)


def test_chunk_without_a_timestamp_is_kept():
    """Unknown age must not mean discarded."""
    checker, _, original = make_checker(12)
    try:
        assert checker(types.SimpleNamespace(duration=1.0)) is False
    finally:
        restore(original)


# ------------------------------------------------------- dormant after media


def test_media_actions_are_declared():
    assert "playsong" in MEDIA_ACTIONS
    assert "suggestsong" in MEDIA_ACTIONS
    # Things that make no lasting sound must NOT be in here, or Phoenix would
    # go dormant after ordinary commands.
    for tag in ("battery", "saytime", "screenshot", "adjustVolume", "dateday"):
        assert tag not in MEDIA_ACTIONS


def test_media_actions_exist_in_dispatch():
    """A tag that no longer exists silently protects nothing."""
    src = open(
        os.path.join(
            os.path.dirname(__file__), "..", "Utils", "limbs", "command_processor.py"
        ),
        encoding="utf-8",
    ).read()
    for tag in MEDIA_ACTIONS:
        assert f'"{tag}"' in src, f"{tag} is not a real action tag"


def test_starting_media_sets_the_flag(monkeypatch):
    """
    Run a real action through the real dispatcher and check the flag.

    play_song is stubbed - the point is the bookkeeping, not opening YouTube.
    """
    from Utils.limbs.action_utilities import Utility, OpenAppHandler, CloseAppHandler
    from Utils.limbs.time_handlers import (
        TimerHandle,
        AlarmHandle,
        ReminderHandle,
        ScheduleHandle,
    )
    from Utils.limbs.command_processor import PhoenixAssistant

    utility = Utility(spk=None, reco=None)
    monkeypatch.setattr(utility, "play_random_song", lambda query: True)

    assistant = PhoenixAssistant(
        utility,
        OpenAppHandler(utility),
        CloseAppHandler(utility),
        TimerHandle(utility),
        AlarmHandle(utility),
        ScheduleHandle(utility),
        ReminderHandle(utility),
    )

    assert assistant.started_media is False
    assistant._execute_action_now("playsong", "sahiba")
    assert assistant.started_media is True, "playsong did not flag media"
    assert assistant.last_action_tag == "playsong"


def test_ordinary_actions_do_not_set_the_flag(monkeypatch):
    from Utils.limbs.action_utilities import Utility, OpenAppHandler, CloseAppHandler
    from Utils.limbs.time_handlers import (
        TimerHandle,
        AlarmHandle,
        ReminderHandle,
        ScheduleHandle,
    )
    from Utils.limbs.command_processor import PhoenixAssistant

    utility = Utility(spk=None, reco=None)
    monkeypatch.setattr(utility, "battery_check", lambda: True)

    assistant = PhoenixAssistant(
        utility,
        OpenAppHandler(utility),
        CloseAppHandler(utility),
        TimerHandle(utility),
        AlarmHandle(utility),
        ScheduleHandle(utility),
        ReminderHandle(utility),
    )
    assistant._execute_action_now("battery", "")
    assert assistant.started_media is False, (
        "an ordinary command flagged media - Phoenix would go dormant after it"
    )
