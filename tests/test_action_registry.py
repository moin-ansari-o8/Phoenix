"""
Action dispatch tests.

The bug this replaces was invisible: four actions raised TypeError on every
invocation and the handler caught it and said "Sorry, I encountered an error
performing that action." Nothing crashed, nothing was logged as a defect, and
the tags were listed in a file that looked correct.

So these tests build the REAL action_map and check that every entry can
actually be called.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe -m pytest W:\\workplace-1\\Phoenix\\tests\\test_action_registry.py -q
"""

import inspect
import os
import re
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Utils.limbs.action_registry import (  # noqa: E402
    FLAG_ACTIONS,
    call_action,
    describe,
    required_positional,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSOR = os.path.join(ROOT, "Utils", "limbs", "command_processor.py")


# --------------------------------------------------------------- unit level


def test_required_positional_counts():
    assert required_positional(lambda: None) == 0
    assert required_positional(lambda a: None) == 1
    assert required_positional(lambda a, b: None) == 2
    assert required_positional(lambda a=1: None) == 0
    assert required_positional(lambda a, b=2: None) == 1
    assert required_positional(lambda *a: None) == 1
    assert required_positional(lambda **kw: None) == 0


def test_required_positional_survives_unreadable_signatures():
    """A C builtin has no signature; the old default branch called it bare."""
    assert required_positional(len) in (0, 1)
    assert required_positional(print) in (0, 1)


def test_call_action_routes_by_arity():
    seen = {}
    call_action(lambda: seen.setdefault("n", ()), "x")
    call_action(lambda q: seen.setdefault("q", q), "y", "hello")
    call_action(lambda q, r: seen.setdefault("qr", (q, r)), "z", "hello", "resp")
    assert seen["n"] == ()
    assert seen["q"] == "hello"
    assert seen["qr"] == ("hello", "resp")


def test_flag_actions_get_a_boolean_not_the_query():
    got = []
    for tag in FLAG_ACTIONS:
        call_action(lambda v: got.append(v), tag, "some spoken words")
    assert got == [True] * len(FLAG_ACTIONS)


# ------------------------------------------------------- against the real map


@pytest.fixture(scope="module")
def action_map():
    """Build the genuine action_map from a constructed PhoenixAssistant."""
    from Utils.limbs.action_utilities import (
        Utility,
        OpenAppHandler,
        CloseAppHandler,
    )
    from Utils.limbs.time_handlers import (
        TimerHandle,
        AlarmHandle,
        ReminderHandle,
        ScheduleHandle,
    )
    from Utils.limbs.command_processor import PhoenixAssistant

    utility = Utility(spk=None, reco=None)
    assistant = PhoenixAssistant(
        utility,
        OpenAppHandler(utility),
        CloseAppHandler(utility),
        TimerHandle(utility),
        AlarmHandle(utility),
        ScheduleHandle(utility),
        ReminderHandle(utility),
    )

    src = open(PROCESSOR, encoding="utf-8").read()
    block = src[
        src.index("        action_map = {") : src.index("        if tag in action_map:")
    ]
    namespace = {"self": assistant}
    exec(textwrap.dedent(block), namespace)
    return namespace["action_map"]


def test_every_action_is_callable_with_what_dispatch_would_send(action_map):
    """
    The regression guard. Not that each action *works* - most touch the OS -
    but that dispatch passes an argument count the callable accepts. A
    mismatch is a TypeError on every single use, silently swallowed.
    """
    wrong = []
    for tag, fn in action_map.items():
        arity = required_positional(fn)
        if tag in FLAG_ACTIONS:
            supplied = 1
        else:
            supplied = 0 if arity == 0 else (1 if arity == 1 else 2)
        if supplied < arity:
            wrong.append(f"{tag}: needs {arity}, dispatch sends {supplied}")
    assert not wrong, "actions dispatch would call incorrectly: " + "; ".join(wrong)


def test_the_four_previously_broken_actions(action_map):
    """type, press, addsong and play-game each require a query."""
    for tag in ("type", "press", "addsong", "play-game"):
        assert tag in action_map, f"{tag} vanished from action_map"
        assert required_positional(action_map[tag]) == 1, (
            f"{tag} no longer takes a query - re-check dispatch"
        )
        assert describe(action_map)[tag] == "query"


def test_no_hand_written_arity_lists_remain():
    """
    The lists are what drifted. If one comes back, so does the class of bug.
    """
    src = open(PROCESSOR, encoding="utf-8").read()
    body = src[src.index("if tag in action_map:") :][:1200]
    assert "type_text" not in body, "the dead 'type_text' arity entry is back"
    assert not re.search(r'tag in \[\s*"', body), (
        "a hand-written arity list has reappeared in _execute_action; "
        "arity belongs in action_registry, derived from the callable"
    )


def test_control_actions_are_reachable(action_map):
    """
    A tag the router may choose but that dispatch cannot run is a dead end:
    Phoenix says it did something and nothing happens.
    """
    from Utils.limbs.tool_registry import CONTROL_ACTIONS

    src = open(PROCESSOR, encoding="utf-8").read()
    unreachable = []
    for tag in CONTROL_ACTIONS:
        if tag in action_map:
            continue
        # Some tags are intercepted before routing (open/close app handlers)
        # or handled by the common_tags table rather than action_map.
        if f'"{tag}"' in src:
            continue
        unreachable.append(tag)
    assert not unreachable, f"router can choose these but nothing runs them: {unreachable}"


def test_describe_covers_every_action(action_map):
    described = describe(action_map)
    assert set(described) == set(action_map)
    assert set(described.values()) <= {"none", "query", "flag", "query+response"}
