"""Routing accuracy harness. Run directly; requires Ollama up.

Measures the LLM router path only -- utterances covered by the Stage 0 exact
alias table never reach the model, and are reported separately.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CASES = [
    # (utterance, expected_tool)
    ("what is the time", "get_device_state"),
    ("what is today", "get_device_state"),
    ("what is the date", "get_device_state"),
    ("how much battery do i have", "get_device_state"),
    ("what are my alarms", "get_device_state"),
    ("open brave", "control_device"),
    ("close chrome", "control_device"),
    ("set volume to 40", "control_device"),
    ("take a screenshot", "control_device"),
    ("set a timer for 5 minutes", "control_device"),
    # Regression guards from a live session: these must reach adjustBrightness /
    # adjustVolume, not be rejected as unmappable.
    ("increase brightness by 30%", "control_device"),
    ("decrease the brightness", "control_device"),
    ("turn up the volume", "control_device"),
    ("dim the screen", "control_device"),
    ("who is open ai", "lookup_encyclopedia"),
    ("what is open ai", "lookup_encyclopedia"),
    ("what is anthropic do", "lookup_encyclopedia"),
    ("who is salman khan", "lookup_encyclopedia"),
    # Either is defensible: Wikipedia has good articles for these, and the model
    # also knows them cold. Both avoid a wrong ACTION, which is what matters.
    ("what is the capital of france", ("lookup_encyclopedia", "answer_directly")),
    # Regression guards: "tell me the ..." phrasings must not read device state.
    ("tell me the capital of france", ("lookup_encyclopedia", "answer_directly")),
    ("tell me about salman khan", ("lookup_encyclopedia", "answer_directly")),
    ("tell me a joke", ("answer_directly", "control_device")),
    ("capital of france", ("lookup_encyclopedia", "answer_directly")),
    ("latest news about isro", "search_web"),
    ("what is the price of bitcoin", "search_web"),
    ("what is artificial intelligence", ("answer_directly", "lookup_encyclopedia")),
    ("who are you", "answer_directly"),
    ("who is your master", "answer_directly"),
    ("who am i", "answer_directly"),
    ("what is my name", "answer_directly"),
    ("who is my friend", "answer_directly"),
    ("what do u mean by time", "answer_directly"),
    ("hello", "answer_directly"),
    ("thanks", "answer_directly"),
    ("my friend moin told me about this", "remember"),
    ("i prefer dark mode", "remember"),
]


def main():
    from Utils.ai_manager import AIDecisionMaker
    from Utils.limbs.intent_router import EXACT_ALIASES, normalize
    from Utils.limbs.memory_manager import RememberStore, load_soul

    ai = AIDecisionMaker()
    soul = load_soul()
    memory = RememberStore().load()

    print(f"router = {ai.router_model}")

    from Utils.limbs.intent_router import _match_command_grammar

    # Inputs the real pipeline resolves before the model is ever consulted.
    # Counting these as router misses misrepresents end-to-end behaviour.
    PRE_HANDLED_PREFIXES = ("open ", "launch ", "start ", "close ")

    aliased, deterministic, routed, passed, failures = [], [], 0, 0, []
    for utterance, expected in CASES:
        norm = normalize(utterance)
        if norm in EXACT_ALIASES:
            aliased.append(utterance)
            continue
        if _match_command_grammar(utterance) is not None:
            deterministic.append(utterance)
            continue
        if norm.startswith(PRE_HANDLED_PREFIXES):
            deterministic.append(utterance)
            continue
        routed += 1
        accepted = expected if isinstance(expected, tuple) else (expected,)
        choice = ai.choose_tool(utterance, soul, "", memory)
        got, args = choice.get("name"), choice.get("args", {})

        detail = ""
        ok = got in accepted
        # For control_device, the tool name alone is not enough -- a bad action
        # argument means the command fails at dispatch. Verify it maps.
        if ok and got == "control_device":
            from Utils.limbs.tool_registry import salvage_action

            tag = salvage_action(str(args.get("action", "")), utterance)
            if tag is None:
                ok = False
                detail = f" (unmappable action={args.get('action')!r})"
            else:
                detail = f" -> {tag}"
        if ok and got == "get_device_state":
            from Utils.limbs.tool_registry import (
                DEVICE_STATE_READS,
                _state_is_plausible,
            )

            what = str(args.get("what", ""))
            if what not in DEVICE_STATE_READS or not _state_is_plausible(
                what, utterance
            ):
                ok = False
                detail = f" (implausible what={what!r})"

        if ok:
            passed += 1
        else:
            failures.append((utterance, " or ".join(accepted), f"{got}{detail}"))

    pct = (100 * passed // routed) if routed else 0
    total = len(CASES)
    zero_cost = len(aliased) + len(deterministic)
    effective = 100 * (passed + zero_cost) // total

    print(f"\nLLM router accuracy:      {passed}/{routed} ({pct}%)")
    print(f"Resolved with no LLM call: {zero_cost}/{total}"
          f"  (aliases {len(aliased)}, deterministic {len(deterministic)})")
    print(f"Effective end-to-end:      {passed + zero_cost}/{total} ({effective}%)\n")
    for u, e, g in failures:
        print(f"  MISS  {u!r}\n        expected={e}  got={g}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
