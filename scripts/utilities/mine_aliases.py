"""
Find utterances that pay for the LLM router but do not need to.

Every utterance the router resolves at Stage 0 (exact alias) or Stage 0b
(command grammar) costs 0 ms. Everything else costs a model call - measured at
1.66 s mean on this machine. So the cheapest available speed-up is not a faster
model, it is moving real, repeated utterances into the alias table.

This reads data/ChatLog.json, replays each user message through the same two
deterministic stages the live router uses, and reports what still falls through
to the model, most frequent first.

It PROPOSES, it does not edit. An alias is a permanent claim that a phrase
always means one thing, and that judgement is the author's - "play something"
looks aliasable until the day it should have meant a specific song.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\scripts\\utilities\\mine_aliases.py
"""

import json
import os
import sys
from collections import Counter

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from Utils.limbs.intent_router import (  # noqa: E402
    EXACT_ALIASES,
    _match_command_grammar,
    normalize,
)
from Utils.limbs.wake_gate import WakeGate  # noqa: E402
from core.config import AppConfig  # noqa: E402

CHATLOG = os.path.join(_ROOT, "data", "ChatLog.json")

# Handled before the router is ever consulted, in command_processor.main().
PRE_HANDLED = ("open ", "launch ", "start ", "close ")


def classify(utterance, gate):
    """Which stage resolves this? Mirrors the live order exactly."""
    stripped = gate.strip_wake(utterance)
    norm = normalize(stripped)
    if not norm:
        return "empty", stripped
    if norm in EXACT_ALIASES:
        return "alias", stripped
    if norm.startswith(PRE_HANDLED):
        return "handler", stripped
    if _match_command_grammar(stripped) is not None:
        return "grammar", stripped
    return "llm", stripped


def main():
    if not os.path.exists(CHATLOG):
        print(f"No chat log at {CHATLOG}")
        return 1

    with open(CHATLOG, encoding="utf-8") as fh:
        entries = json.load(fh)

    gate = WakeGate(wake_words=AppConfig.wake_words)
    counts = Counter()
    llm_bound = Counter()

    for entry in entries:
        if entry.get("role") != "user":
            continue
        message = (entry.get("message") or "").strip()
        if not message:
            continue
        stage, stripped = classify(message, gate)
        counts[stage] += 1
        if stage == "llm":
            llm_bound[normalize(stripped)] += 1

    total = sum(counts.values())
    if not total:
        print("No user messages in the log.")
        return 0

    zero_cost = counts["alias"] + counts["grammar"] + counts["handler"]
    print(f"user utterances analysed : {total}")
    print(f"  exact alias   (0 ms)   : {counts['alias']}")
    print(f"  open/close    (0 ms)   : {counts['handler']}")
    print(f"  grammar       (0 ms)   : {counts['grammar']}")
    print(f"  -> LLM      (~1.7 s)   : {counts['llm']}")
    print(f"\nzero-cost share: {100 * zero_cost // total}%")
    print(f"time spent on the model : ~{counts['llm'] * 1.66:.0f}s across this log\n")

    repeated = [(u, n) for u, n in llm_bound.most_common() if n > 1]
    if repeated:
        print("Repeated, and therefore worth an alias:")
        for utterance, n in repeated:
            print(f"  {n:3d}x  {utterance!r}")
    else:
        print("No LLM-bound utterance repeats in this log - nothing to propose.")

    once = [u for u, n in llm_bound.items() if n == 1]
    if once:
        print(f"\nSeen once ({len(once)}) - review before aliasing any of these:")
        for utterance in sorted(once)[:25]:
            print(f"        {utterance!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
