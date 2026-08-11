"""
Pure-function coverage for the three most intricate untested units.

These are pytest-native (unlike the standalone suites) because they are
ordinary input -> output functions with no process, device or model behind
them. They were flagged in the audit as todo-F2: every defensive rule in them
exists because of a real observed misbehaviour, and none had a single test.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe -m pytest W:\\workplace-1\\Phoenix\\tests\\test_units.py -q
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Utils.limbs.intent_router import _match_command_grammar  # noqa: E402
from Utils.limbs.memory_manager import RememberStore  # noqa: E402
from Utils.limbs import tool_registry as tr  # noqa: E402


# ---------------------------------------------------------------------------
# _match_command_grammar - the zero-cost path. Anything it resolves never
# reaches the LLM, saving 1.5-3 s; anything it resolves WRONGLY is a silent
# misfire that never gets a second opinion. Both directions matter.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query,subject,mode",
    [
        ("increase brightness", "brightness", "increase"),
        ("increase the brightness by 30%", "brightness", "increase"),
        ("decrease brightness", "brightness", "decrease"),
        ("dim the screen", "brightness", "decrease"),
        ("set brightness to 50", "brightness", "set"),
        ("turn up the volume", "volume", "increase"),
        ("turn down the volume", "volume", "decrease"),
        ("set volume to 40", "volume", "set"),
    ],
)
def test_grammar_matches_real_commands(query, subject, mode):
    got = _match_command_grammar(query)
    assert got is not None, f"{query!r} should resolve without the LLM"
    assert got["subject"] == subject
    assert got["mode"] == mode


@pytest.mark.parametrize(
    "query",
    [
        # Definitional questions are not commands. "what does brighten mean"
        # used to fire adjustBrightness.
        "what does brighten mean",
        "what is the meaning of volume",
        "define brightness",
        # No control verb.
        "the brightness is fine",
        # No subject at all.
        "increase it",
        # Plain questions.
        "what is the capital of france",
        "who was mahatma gandhi",
        "",
    ],
)
def test_grammar_declines_non_commands(query):
    assert _match_command_grammar(query) is None, f"{query!r} must reach the router"


def test_pronoun_needs_a_prior_device():
    """A bare pronoun is only a command once we know what 'it' referred to."""
    assert _match_command_grammar("decrease it") is None
    resolved = _match_command_grammar("decrease it", last_device="brightness")
    assert resolved is not None
    assert resolved["subject"] == "brightness"
    assert resolved["mode"] == "decrease"


@pytest.mark.parametrize("query", ["turn it up", "turn it down", "make it louder"])
def test_idiomatic_volume_phrases_need_no_antecedent(query):
    """
    'turn it up' carries its own subject - in English it means volume, and
    nothing else. These resolve without `last_device` on purpose; treating them
    as ambiguous would push a trivially clear command to the LLM.
    """
    got = _match_command_grammar(query)
    assert got is not None
    assert got["subject"] == "volume"


def test_amount_is_extracted():
    got = _match_command_grammar("increase brightness by 30%")
    assert got["amount"] == 30

    got = _match_command_grammar("set volume to 40")
    assert got["amount"] == 40


# ---------------------------------------------------------------------------
# RememberStore._is_grounded - every rule here exists because Phoenix once
# stored something the user never said.
# ---------------------------------------------------------------------------


def test_grounded_accepts_facts_present_in_the_source():
    assert RememberStore._is_grounded("moin is my friend", "moin is my friend")
    assert RememberStore._is_grounded("i prefer dark mode", "remember i prefer dark mode")


def test_grounded_rejects_invented_facts():
    """The model paraphrasing beyond the utterance is the failure mode."""
    assert not RememberStore._is_grounded(
        "the user's favourite colour is blue", "remember that i like dogs"
    )
    # The real case from the audit: 'dragon' and 'game' were never said.
    assert not RememberStore._is_grounded(
        "rohit tells kaly he is a dragon in the game",
        "my friend rohit told me about this",
    )


def test_grounded_is_only_about_invention():
    """
    Empty/short/subjectless facts are add_fact()'s job, not _is_grounded()'s.
    _is_grounded answers exactly one question: did every content word come from
    the user? Asserting more here would test the wrong layer.
    """
    assert RememberStore._is_grounded("", "remember something")
    assert RememberStore._is_grounded("anything at all", "")  # no source to check


@pytest.mark.parametrize(
    "fact",
    [
        "",                       # empty
        "moin",                   # bare name, under three words
        "is a foreman",           # no subject - the model dropped who
        "x" * 250,                # over the 200-char cap
    ],
)
def test_add_fact_rejects_junk(fact, tmp_path):
    store = RememberStore(path=str(tmp_path / "remember.md"))
    assert store.add_fact("general", fact, source=fact) is False


def test_forget_request_parsing():
    """A deletion must never be stored as an insertion."""
    assert tr._forget_request("forget that") is not None
    assert tr._forget_request("forget everything you know about me") is not None
    assert tr._forget_request("remember that i like dogs") is None
    assert tr._forget_request("what is the time") is None


# ---------------------------------------------------------------------------
# needs_fresh_data - decides whether an answer may come from training data.
# Wrong in one direction it invents a stale fact; wrong in the other it burns
# a web round-trip on "what is 2+2".
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        "who is the current prime minister of india",
        "what is the latest python version",
        "what is the price of bitcoin",
        "latest news about isro",
    ],
)
def test_volatile_queries_need_fresh_data(query):
    assert tr.needs_fresh_data(query) is True


@pytest.mark.parametrize(
    "query",
    [
        "what is the capital of france",
        "who was mahatma gandhi",
        "what is 15 percent of 240",
        # Device questions are about THIS pc and must never hit the web, even
        # though "current" reads as volatile.
        "what is the current battery level",
        "what is the current volume",
    ],
)
def test_settled_and_device_queries_do_not(query):
    assert tr.needs_fresh_data(query) is False


def test_offline_notice_is_a_refusal_not_an_answer():
    """The refusal must not look like a successful lookup."""
    for notice in (tr.OFFLINE_NOTICE, tr.NO_NETWORK_NOTICE):
        assert notice
        assert "can't" in notice.lower() or "cannot" in notice.lower()
