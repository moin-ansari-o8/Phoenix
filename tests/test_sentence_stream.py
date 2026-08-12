"""
SentenceSplitter tests.

Streaming only helps if the cuts land in the right places. A wrong cut is worse
than not streaming at all: TTS stops dead with falling intonation halfway
through a phrase, which sounds like a fault rather than a feature. So most of
this file is about NOT splitting.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe -m pytest W:\\workplace-1\\Phoenix\\tests\\test_sentence_stream.py -q
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Utils.limbs.sentence_stream import (  # noqa: E402
    SentenceSplitter,
    stream_sentences,
)


def split(text, **kw):
    """Feed `text` one character at a time - the worst case for a splitter."""
    return list(stream_sentences(list(text), **kw))


def test_simple_sentences_split():
    got = split("The capital of France is Paris. It has about two million people. ")
    assert got == [
        "The capital of France is Paris.",
        "It has about two million people.",
    ]


def test_first_sentence_is_available_before_the_rest():
    """The entire point: sentence one must be emitted before the stream ends."""
    splitter = SentenceSplitter()
    early = splitter.feed("Paris is the capital of France. Now let me ")
    assert early == ["Paris is the capital of France."]

    # The trailing partial stays buffered - it has no terminator yet - and the
    # rest of it arrives later, so flush() returns the whole second sentence.
    assert splitter.feed("tell you about its history.") == []
    assert splitter.flush() == ["Now let me tell you about its history."]


@pytest.mark.parametrize(
    "text",
    [
        "Dr. Ambedkar wrote the constitution and it was adopted later on.",
        "The meeting is at 5 p.m. tomorrow so please be ready by then.",
        "Mr. Sharma and Mrs. Sharma are both attending the ceremony today.",
        "That costs approx. two hundred rupees at the moment in most shops.",
    ],
)
def test_abbreviations_do_not_split(text):
    """'at 5 p.' spoken as a sentence is the failure this prevents."""
    assert split(text + " ") == [text]


@pytest.mark.parametrize(
    "text",
    [
        "Pi is roughly 3.14 which is close enough for most everyday purposes.",
        "You are running Python 3.11 on this machine at the present moment.",
    ],
)
def test_decimals_do_not_split(text):
    assert split(text + " ") == [text]


def test_short_fragments_are_merged():
    """'Yes.' alone is a whole TTS round trip for one word, and the pause after
    it reads as the answer being over."""
    got = split("Yes. The battery is at eighty percent right now. ")
    assert got[0].startswith("Yes."), got
    assert len(got[0]) > 12
    assert len(got) <= 2


def test_unpunctuated_run_on_still_flushes():
    """A model that forgets punctuation must not stall the audio forever."""
    text = "so " * 120
    got = split(text, max_chars=80)
    assert len(got) > 1
    assert all(len(s) <= 90 for s in got)
    # No word may be cut in half.
    assert " ".join(got).split() == text.split()


def test_no_text_is_lost():
    text = (
        "First sentence here. Second one follows it. Third has a question? "
        "And a fourth exclaims! Trailing words with no ending"
    )
    got = split(text)
    joined = " ".join(got)
    assert joined.split() == text.split()


def test_question_and_exclamation_end_sentences():
    got = split("Are you sure about that? I think it is correct! ")
    assert got == ["Are you sure about that?", "I think it is correct!"]


def test_quotes_after_terminator_stay_attached():
    got = split('She said "hello there everyone." Then she left the room. ')
    assert got[0].endswith('."'), got


def test_empty_and_whitespace():
    assert split("") == []
    assert split("    ") == []
    splitter = SentenceSplitter()
    assert splitter.feed("") == []
    assert splitter.flush() == []


def test_flush_is_idempotent():
    splitter = SentenceSplitter()
    splitter.feed("Half a thought")
    assert splitter.flush() == ["Half a thought"]
    assert splitter.flush() == []
