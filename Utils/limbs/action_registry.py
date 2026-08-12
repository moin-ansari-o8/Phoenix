"""
How to call an action, derived from the action itself.

`_execute_action` used to decide an action's arguments from four hand-written
lists:

    if tag in ["adjustVolume", ..., "type_text", "setTimer", ..., "setTimer"]:
        action_map[tag](query)
    elif tag in ["maximize", "minimize"]:
        action_map[tag](True)
    elif tag in ["open", "close", "select"]:
        action_map[tag](query, self.tag_response)
    else:
        action_map[tag]()

A list of tags maintained by hand, next to a dict of tags maintained by hand,
drifts. It had:

  * `"type_text"` - not a tag. The real tag is `"type"`, which therefore fell
    to the `else` branch and was called with no arguments at all. Since
    `type_text(self, query)` requires one, **every "type ..." command raised
    TypeError** and answered "Sorry, I encountered an error performing that
    action." The same was true of `press`, `addsong` and `play-game`.
  * `"setTimer"` listed twice.
  * `"open"`, `"select"`, `"forward"`, `"backward"` - branches for tags that
    are not in `action_map` at all; they are handled earlier, so those arms
    were dead.

So the list is gone. Arity now comes from `inspect.signature` on the callable
that is about to be invoked, which cannot disagree with itself. Adding an
action is now just adding it to `action_map`; nothing else needs updating.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

# The one genuine exception. These take an argument, but it is a boolean flag
# rather than the user's words - `perform_window_action(True)` - so signature
# inspection alone cannot tell what to pass.
FLAG_ACTIONS = frozenset({"maximize", "minimize"})


def required_positional(fn: Callable) -> int:
    """
    How many positional arguments `fn` needs.

    Bound methods, plain functions and the lambdas in `action_map` all report
    correctly; anything whose signature cannot be read (a C builtin, say) is
    reported as 0, which matches the old default branch.
    """
    try:
        signature = inspect.signature(fn)
    except (TypeError, ValueError):
        return 0

    count = 0
    for parameter in signature.parameters.values():
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ) and parameter.default is inspect.Parameter.empty:
            count += 1
        elif parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            # *args - it will accept whatever we send, so send the query.
            return max(count, 1)
    return count


def call_action(fn: Callable, tag: str, query: str = "", response: str = "") -> Any:
    """
    Invoke `fn` with the arguments its own signature asks for.

    0 -> fn()
    1 -> fn(query), or fn(True) for the window flag actions
    2+ -> fn(query, response)
    """
    if tag in FLAG_ACTIONS:
        return fn(True)

    arity = required_positional(fn)
    if arity == 0:
        return fn()
    if arity == 1:
        return fn(query)
    return fn(query, response)


def describe(action_map: dict) -> dict:
    """
    tag -> calling convention, for tests and documentation.

    Generated rather than written down, so it is a description of what the code
    does rather than a second claim about it.
    """
    out = {}
    for tag, fn in action_map.items():
        if tag in FLAG_ACTIONS:
            out[tag] = "flag"
            continue
        arity = required_positional(fn)
        out[tag] = {0: "none", 1: "query"}.get(arity, "query+response")
    return out
