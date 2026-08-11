"""
Standalone checks for Utils/limbs/wake_gate.WakeGate.

No pytest, no mic, no audio - the gate is a pure state machine with an
injectable clock, which is the whole reason it was extracted from the
processor. Run it directly:

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\tests\\test_wake_gate.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Utils.limbs.wake_gate import WakeGate  # noqa: E402

PASS = 0
FAIL = 0


def check(label, got, want):
    global PASS, FAIL
    if got == want:
        PASS += 1
        print(f"  [ok]   {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}\n           got:  {got!r}\n           want: {want!r}")


class FakeClock:
    """Controllable time source, so a 30s window costs no wall-clock seconds."""

    def __init__(self, start=1000.0):
        self.t = start

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


PROFILE = ["phoenix", "babe", "baby", "yo", "yoi", "hey phoenix", "ok phoenix"]


def gate(words=None, window=30.0, clock=None):
    return WakeGate(
        wake_words=words if words is not None else PROFILE,
        followup_window_seconds=window,
        time_source=clock or FakeClock(),
    )


# --------------------------------------------------------------------------
def test_the_original_bug():
    """The reported defect: 'yo' matched inside 'you' and 'your'."""
    print("\n[1] substring false positives (the A1 bug)")
    g = gate()

    check("'you' does not contain a wake word", g.find_wake("what about you"), None)
    check("'your' does not contain a wake word", g.find_wake("is that your bag"), None)
    check("'maybe' does not match 'babe'", g.find_wake("maybe later"), None)
    check("'yoga' does not match 'yo'", g.find_wake("i did yoga today"), None)
    check("'babysit' does not match 'baby'", g.find_wake("babysitting tonight"), None)
    # ...but the words themselves still work as wake words
    check("bare 'yo' still matches", g.find_wake("yo what time is it"), "yo")
    check("bare 'babe' still matches", g.find_wake("babe open chrome"), "babe")


def test_matching_positions():
    print("\n[2] wake word anywhere in the sentence")
    g = gate()

    check("at the start", g.find_wake("phoenix what time is it"), "phoenix")
    check("in the middle", g.find_wake("so phoenix turn it down"), "phoenix")
    check("at the end", g.find_wake("what time is it phoenix"), "phoenix")
    check("with punctuation", g.find_wake("Phoenix, what time is it?"), "phoenix")
    check("case insensitive", g.find_wake("PHOENIX open chrome"), "phoenix")
    check("no wake word", g.find_wake("what time is it"), None)
    check("empty string", g.find_wake(""), None)


def test_longest_match_wins():
    """Alternation is first-match; without longest-first sorting 'hey phoenix'
    would match the bare 'phoenix' branch and leave a dangling 'hey'."""
    print("\n[3] multi-word wake words win over their prefixes")
    g = gate()

    check("'hey phoenix' matched whole", g.find_wake("hey phoenix hello"), "hey phoenix")
    check("'ok phoenix' matched whole", g.find_wake("ok phoenix hello"), "ok phoenix")
    check("no dangling 'hey'", g.strip_wake("hey phoenix turn it down"), "turn it down")
    check("no dangling 'ok'", g.strip_wake("ok phoenix turn it down"), "turn it down")


def test_stripping():
    print("\n[4] stripping leaves a clean query")
    g = gate()

    check("leading", g.strip_wake("phoenix what time is it"), "what time is it")
    check("leading + comma", g.strip_wake("Phoenix, what time is it"), "what time is it")
    check("trailing", g.strip_wake("what time is it phoenix"), "what time is it")
    check("middle", g.strip_wake("so phoenix turn it down"), "so turn it down")
    check("repeated", g.strip_wake("phoenix phoenix turn it off"), "turn it off")
    check("wake word only", g.strip_wake("phoenix"), "")
    check("wake word + punctuation only", g.strip_wake("Phoenix!"), "")
    check("no wake word is untouched", g.strip_wake("turn it down"), "turn it down")
    check("no double spaces left", g.strip_wake("turn phoenix it down"), "turn it down")


def test_protected_follower():
    """'phoenix folder' names a directory - stripping it would route 'open folder'."""
    print("\n[5] 'phoenix folder' is protected")
    g = gate()

    check("folder survives strip", g.strip_wake("open phoenix folder"), "open phoenix folder")
    check("folder is not a wake trigger", g.find_wake("open phoenix folder"), None)
    # but an address in the same sentence still wakes it
    check(
        "address + folder",
        g.strip_wake("phoenix open the phoenix folder"),
        "open the phoenix folder",
    )


def test_dormant_by_default():
    print("\n[6] boots dormant")
    g = gate()

    check("not awake at boot", g.is_awake, False)
    d = g.evaluate("what time is it")
    check("unaddressed speech ignored", d.action, "ignore")
    check("still dormant after ignoring", g.is_awake, False)


def test_wake_answers_that_same_sentence():
    """The requirement: saying the wake word in a sentence answers THAT sentence."""
    print("\n[7] wake word answers the sentence it appeared in")
    g = gate()

    d = g.evaluate("phoenix what time is it")
    check("action", d.action, "respond")
    check("trigger", d.trigger, "wake")
    check("query has wake word stripped", d.query, "what time is it")


def test_bare_wake_word_acknowledges():
    print("\n[8] bare wake word wakes without routing an empty query")
    g = gate()

    d = g.evaluate("phoenix")
    check("action", d.action, "acknowledge")
    check("no empty query routed", d.query, "")


def test_followup_needs_no_wake_word():
    print("\n[9] follow-ups need no wake word")
    clock = FakeClock()
    g = gate(clock=clock)

    g.evaluate("phoenix what time is it")
    g.refresh()  # processor refreshes after an answered turn
    check("awake now", g.is_awake, True)

    clock.advance(5)
    d = g.evaluate("and the date")
    check("follow-up responds", d.action, "respond")
    check("trigger is followup", d.trigger, "followup")
    check("query untouched", d.query, "and the date")


def test_window_expires():
    """The A2 bug: follow-up mode latched on forever."""
    print("\n[10] awake window expires after the idle timeout")
    clock = FakeClock()
    g = gate(window=30.0, clock=clock)

    g.evaluate("phoenix hello")
    g.refresh()
    check("awake", g.is_awake, True)

    clock.advance(29)
    check("still awake at 29s", g.is_awake, True)

    clock.advance(2)  # 31s total
    check("dormant at 31s", g.is_awake, False)
    d = g.evaluate("some ambient conversation")
    check("ignores speech again", d.action, "ignore")


def test_window_refreshes_on_each_turn():
    print("\n[11] each answered turn refreshes the window")
    clock = FakeClock()
    g = gate(window=30.0, clock=clock)

    g.evaluate("phoenix hello")
    g.refresh()

    for i in range(5):
        clock.advance(20)  # inside the window each time
        d = g.evaluate("and another thing")
        check(f"turn {i + 1} still responds", d.action, "respond")
        g.refresh()

    # total elapsed is 100s, far beyond one window, but it stayed awake
    clock.advance(31)
    check("expires once the user stops", g.is_awake, False)


def test_silence_cannot_be_kept_alive():
    """Silence produces no utterances, so nothing can refresh the deadline."""
    print("\n[12] silence always returns to dormant")
    clock = FakeClock()
    g = gate(window=30.0, clock=clock)

    g.evaluate("phoenix hello")
    g.refresh()
    clock.advance(3600)
    check("dormant after an hour of silence", g.is_awake, False)


def test_wake_word_while_awake():
    print("\n[13] wake word while already awake is still stripped")
    clock = FakeClock()
    g = gate(clock=clock)

    g.evaluate("phoenix hello")
    g.refresh()

    d = g.evaluate("phoenix what time is it")
    check("responds", d.action, "respond")
    check("trigger is wake, not followup", d.trigger, "wake")
    check("wake word stripped, not routed", d.query, "what time is it")


def test_sleep_forces_dormant():
    print("\n[14] sleep() returns to dormant immediately")
    clock = FakeClock()
    g = gate(clock=clock)

    g.evaluate("phoenix hello")
    g.refresh()
    check("awake", g.is_awake, True)
    g.sleep()
    check("dormant after sleep()", g.is_awake, False)


def test_config_driven():
    """Wake words come from config, so switching profile switches them."""
    print("\n[15] wake words are config-driven, not hardcoded")
    igris = gate(words=["igris", "hey igris", "arise igris", "arise"])

    check("igris wakes", igris.find_wake("igris what time is it"), "igris")
    check("arise wakes", igris.find_wake("arise open chrome"), "arise")
    check("phoenix does NOT wake igris", igris.find_wake("phoenix hello"), None)
    check("igris is stripped", igris.strip_wake("igris open chrome"), "open chrome")
    check(
        "'arise igris' matched whole",
        igris.find_wake("arise igris"),
        "arise igris",
    )


def test_no_wake_words_configured():
    """A config typo should make Phoenix quiet, never permanently open."""
    print("\n[16] empty wake word list matches nothing")
    g = gate(words=[])

    check("nothing matches", g.find_wake("phoenix hello"), None)
    check("strip is a no-op", g.strip_wake("phoenix hello"), "phoenix hello")
    check("dormant stays dormant", g.evaluate("phoenix hello").action, "ignore")


def test_whitespace_and_junk():
    print("\n[17] messy input")
    g = gate()

    check("empty transcript ignored", g.evaluate("").action, "ignore")
    check("whitespace only ignored", g.evaluate("   ").action, "ignore")
    check("None-ish ignored", g.evaluate(None).action, "ignore")
    check("duplicate config entries tolerated", len(gate(["yo", "yo", "YO"]).wake_words), 1)


if __name__ == "__main__":
    print("=" * 62)
    print("WakeGate - dormant/awake state machine")
    print("=" * 62)

    for fn in [
        test_the_original_bug,
        test_matching_positions,
        test_longest_match_wins,
        test_stripping,
        test_protected_follower,
        test_dormant_by_default,
        test_wake_answers_that_same_sentence,
        test_bare_wake_word_acknowledges,
        test_followup_needs_no_wake_word,
        test_window_expires,
        test_window_refreshes_on_each_turn,
        test_silence_cannot_be_kept_alive,
        test_wake_word_while_awake,
        test_sleep_forces_dormant,
        test_config_driven,
        test_no_wake_words_configured,
        test_whitespace_and_junk,
    ]:
        fn()

    print("\n" + "=" * 62)
    print(f"  {PASS} passed, {FAIL} failed")
    print("=" * 62)
    sys.exit(1 if FAIL else 0)
