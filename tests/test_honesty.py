"""
Regression tests for the "I don't know" path.

Two halves, and the SECOND one matters more:

  1. A decline or a hedge must be detected, so the router can escalate to a web
     search instead of speaking a guess.
  2. Ordinary confident answers must NOT be detected. The failure mode of this
     feature is over-deflection - a Phoenix that says "I don't know" to "what is
     the capital of France" is worse than the fabrication it was built to stop.

Runs offline: these test the detector, not the model.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\tests\\test_honesty.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Utils.ai_manager import UNKNOWN_SENTINEL, is_unknown

_RESULTS = []


def check(name, condition, detail=""):
    _RESULTS.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f"  -- {detail}" if detail and not condition else ""))


def section(title):
    print(f"\n{title}\n{'-' * len(title)}")


def test_sentinel_detected():
    section("The sentinel is detected")

    declines = [
        "UNKNOWN",
        "unknown",
        "  UNKNOWN  ",
        "UNKNOWN.",
        # Small models like to answer anyway right after emitting the sentinel.
        # That trailing guess is exactly what the sentinel exists to suppress.
        "UNKNOWN. But I think it might be around 1947.",
        "UNKNOWN - I was not told that.",
    ]
    for text in declines:
        check(f"'{text.strip()}' reads as a decline", is_unknown(text))

    check("empty output is a decline", is_unknown(""))
    check("None is a decline", is_unknown(None))


def test_hedges_detected():
    section("Hedged non-answers are detected")

    hedges = [
        "As of my last update, the population was around 67 million.",
        "As of my latest training data, that was still under construction.",
        "I don't have access to real-time information, but it is probably raining.",
        "I do not have real-time data on that.",
        "I can't browse the internet, so I'm not sure.",
        "I'm not entirely sure, but I believe it was Tuesday.",
        "I might be wrong, but I think he retired in 2013.",
        "I don't have that information about your friend.",
        "Without more context, I would guess it is about ten kilometres.",
        "My knowledge cutoff only goes up to early last year.",
    ]
    for text in hedges:
        check(f"hedge detected: '{text[:45]}...'", is_unknown(text), text)


def test_real_answers_survive():
    section("Confident answers are NOT deflected")

    # If any of these trip the detector, Phoenix starts refusing to answer
    # things it knows perfectly well. That is a worse regression than the bug
    # this feature fixes.
    answers = [
        "Paris.",
        "The capital of France is Paris.",
        "It's twenty past four, sir.",
        "Python is a high-level programming language known for readable syntax.",
        "You're Kaly, my developer.",
        "Your battery is at sixty two percent and charging.",
        "Mahatma Gandhi led India's independence movement through non-violent resistance.",
        "Fifteen percent of two hundred and forty is thirty six.",
        "The moon is about three hundred and eighty four thousand kilometres away.",
        "I've set a timer for ten minutes.",
        "Moin is a friend of yours - you told me about him last week.",
        "Sure, here it is again: the capital of France is Paris.",
        # Contains "know" and "sure" but is a confident, complete answer.
        "I know that one - it's Mount Everest, at eight thousand eight hundred metres.",
        "Sure thing, opening Brave now.",
        # Mentions uncertainty as SUBJECT MATTER rather than as a hedge.
        "Heisenberg's uncertainty principle says you cannot know both precisely.",
    ]
    for text in answers:
        check(f"answer survives: '{text[:45]}...'", not is_unknown(text), text)


def test_sentinel_is_never_spoken():
    section("The sentinel never reaches the speaker")

    # The contract the router relies on: anything is_unknown() accepts gets
    # replaced upstream, so the literal token can never be spoken aloud.
    check(
        "the sentinel constant is a bare token",
        UNKNOWN_SENTINEL.isupper() and " " not in UNKNOWN_SENTINEL,
        UNKNOWN_SENTINEL,
    )
    check(
        "a reply that is only the sentinel is caught",
        is_unknown(UNKNOWN_SENTINEL),
    )


if __name__ == "__main__":
    print("Phoenix honesty regression tests")
    test_sentinel_detected()
    test_hedges_detected()
    test_real_answers_survive()
    test_sentinel_is_never_spoken()

    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    failed = [(name, detail) for name, ok, detail in _RESULTS if not ok]

    print(f"\n{'=' * 60}")
    print(f"{passed}/{len(_RESULTS)} checks passed")
    if failed:
        print("\nFailures:")
        for name, detail in failed:
            print(f"  - {name}" + (f"  ({detail})" if detail else ""))
    sys.exit(1 if failed else 0)
