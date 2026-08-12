"""
Structured trace tests.

The property that matters is the negative one: ordinary output must never be
readable as a trace. The old tag protocol failed exactly there - a `print()`
anywhere in the action layer could look like a UI event, and the guard against
it was a heuristic that dropped any line containing "|" or "---".

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe -m pytest W:\\workplace-1\\Phoenix\\tests\\test_trace.py -q
"""

import io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.trace import PREFIX, emit, parse  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def emitted(event, **fields):
    buf = io.StringIO()
    emit(event, stream=buf, **fields)
    return buf.getvalue()


def test_round_trip():
    line = emitted("heard", text="what time is it")
    got = parse(line)
    assert got == {"event": "heard", "text": "what time is it"}


def test_fields_are_named_not_positional():
    got = parse(emitted("stt", text="ok", seconds=0.42, device="cpu"))
    assert got["seconds"] == 0.42
    assert got["device"] == "cpu"


def test_none_fields_are_dropped():
    got = parse(emitted("intent", text="matched", tool=None))
    assert "tool" not in got


@pytest.mark.parametrize(
    "line",
    [
        "",
        "   ",
        "Loading Whisper on cpu...",
        "Traceback (most recent call last):",
        "  File \"x.py\", line 1, in <module>",
        "| a | table | row |",
        "----------------------------",
        "[VOICE_STATE] listening",          # the OLD tag format
        "[HEARD] something",
        "{\"event\": \"heard\"}",           # bare JSON, no sentinel
        "@@PHX@@not json at all",
        "@@PHX@@[1,2,3]",                   # valid JSON, wrong shape
        "@@PHX@@{\"no_event_key\": 1}",
    ],
)
def test_ordinary_output_is_never_a_trace(line):
    assert parse(line) is None


def test_a_transcript_that_looks_like_a_trace_is_still_not_one():
    """Someone can say anything into a microphone, including punctuation."""
    assert parse("the user said [VOICE_STATE] out loud") is None
    assert parse("event: heard") is None


def test_emit_never_raises_on_unserialisable_input():
    class Weird:
        def __repr__(self):
            raise RuntimeError("nope")

    buf = io.StringIO()
    emit("odd", stream=buf, thing=Weird())     # must not propagate
    assert PREFIX in buf.getvalue()


def test_emit_survives_a_dead_stream():
    class Closed:
        def write(self, _):
            raise ValueError("I/O operation on closed file")

        def flush(self):
            raise ValueError("closed")

    emit("heard", stream=Closed(), text="x")   # must not propagate


def test_unicode_survives_the_round_trip():
    """The lexicon repairs Hindi/Gujarati words; they travel over this channel."""
    for text in ["sahiba", "vhalam aavo ne", "नमस्ते", "ગુજરાતી"]:
        assert parse(emitted("heard", text=text))["text"] == text


def test_trace_is_one_line():
    """A multi-line payload would be read as several events, most of them junk."""
    payload = emitted("heard", text="line one\nline two\nline three")
    body = [ln for ln in payload.splitlines() if PREFIX in ln]
    assert len(body) == 1
    assert parse(body[0])["text"] == "line one\nline two\nline three"


def test_both_parsers_handle_every_emitted_event():
    """
    Every event name the processor emits must be handled by both UIs.

    The two parsers drifting apart is precisely what happened before - one was
    still matching emoji prefixes that had been removed from the emitter.
    """
    processor = open(
        os.path.join(ROOT, "Utils", "runners", "voice_command_processor.py"),
        encoding="utf-8",
    ).read()

    emitted_names = set(re.findall(r'_runtime_trace\(\s*"([A-Z_]+)"', processor))
    emitted_names |= set(re.findall(r'trace_emit\(\s*"([a-z_]+)"', processor))
    emitted_names = {n.lower() for n in emitted_names}
    assert emitted_names, "found no trace emissions to check"

    for path in (
        os.path.join(ROOT, "main.py"),
        os.path.join(ROOT, "Utils", "runners", "manager.py"),
    ):
        src = open(path, encoding="utf-8").read()

        handled = set(re.findall(r'kind == "([a-z_]+)"', src))
        # `if kind in ("a", "b", "c"):` - collect every name in the tuple.
        for group in re.findall(r"kind in \(([^)]*)\)", src):
            handled |= set(re.findall(r'"([a-z_]+)"', group))
        # dict-dispatch form: {"listening": ..., "dormant": ...}
        handled |= set(re.findall(r'"([a-z_]+)":\s', src))

        missing = emitted_names - handled
        assert not missing, (
            f"{os.path.basename(path)} does not handle: {sorted(missing)}"
        )
