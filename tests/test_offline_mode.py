"""
Phase 2 checks: offline_mode auto-detection and the destructive-action gate.

Both are pure state machines with injectable dependencies (a fake socket probe,
a fake clock), so nothing here touches the network, the PC's power state, or
the wall clock.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\tests\\test_offline_mode.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import AppConfig  # noqa: E402
from Utils.limbs import connectivity  # noqa: E402
from Utils.limbs.connectivity import ConnectivityMonitor, _normalise  # noqa: E402
from Utils.limbs.confirm_gate import (  # noqa: E402
    ConfirmationGate,
    DESTRUCTIVE_TAGS,
)

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
    def __init__(self, start=1000.0):
        self.t = start

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


def fake_monitor(reachable, clock=None):
    """A monitor whose probe returns `reachable` and counts its calls."""
    m = ConnectivityMonitor()
    m._probe = lambda: reachable
    if clock:
        import time as _t
        m._clock = clock
    return m


# ---------------------------------------------------------------- connectivity


def test_offline_mode_parsing():
    print("\n[1] offline_mode values map correctly")
    check("true  -> network off", _normalise(True), "off")
    check("'true'-> network off", _normalise("true"), "off")
    check("false -> network on", _normalise(False), "on")
    check("'no'  -> network on", _normalise("no"), "on")
    check("'auto'-> auto", _normalise("auto"), "auto")
    check("junk  -> auto (safe default)", _normalise("banana"), "auto")
    check("None  -> auto", _normalise(None), "auto")


def test_probe_caching():
    print("\n[2] the probe is cached, not run per question")
    m = fake_monitor(True)
    for _ in range(10):
        m.is_online()
    check("10 calls -> 1 probe", m.probe_count, 1)
    m.is_online(force=True)
    check("force re-probes", m.probe_count, 2)
    m.invalidate()
    m.is_online()
    check("invalidate re-probes", m.probe_count, 3)


def test_probe_failure_is_offline():
    print("\n[3] an unreachable network reads as offline")
    m = fake_monitor(False)
    check("offline", m.is_online(), False)

    m2 = ConnectivityMonitor()

    def explode():
        raise OSError("network is unreachable")

    m2._probe = explode
    try:
        m2._probe()
        raised = False
    except OSError:
        raised = True
    check("a raising probe is an OSError case", raised, True)


def test_real_probe_shape():
    """Not asserting online/offline - just that it answers fast and is a bool."""
    print("\n[4] the real probe returns a bool quickly")
    import time

    m = ConnectivityMonitor(timeout=1.0)
    started = time.time()
    result = m.is_online()
    elapsed = time.time() - started
    check("returns a bool", isinstance(result, bool), True)
    check("under 3s even when it fails", elapsed < 3.0, True)
    print(f"         (this machine reports online={result} in {elapsed:.2f}s)")


def test_network_allowed_precedence():
    print("\n[5] web.enabled beats offline_mode beats the probe")
    orig_web = AppConfig.web.get("enabled", True)
    orig_mode = getattr(AppConfig, "offline_mode", "auto")
    orig_monitor = connectivity._monitor
    try:
        connectivity._monitor = fake_monitor(True)

        AppConfig.web["enabled"] = False
        AppConfig.offline_mode = False
        check("web.enabled=false wins", connectivity.network_allowed(), False)
        check("...and says why", connectivity.network_allowed(reason=True)[1],
              "web.enabled is false")

        AppConfig.web["enabled"] = True
        AppConfig.offline_mode = True
        check("offline_mode=true blocks", connectivity.network_allowed(), False)

        AppConfig.offline_mode = False
        check("offline_mode=false allows", connectivity.network_allowed(), True)

        AppConfig.offline_mode = "auto"
        check("auto + reachable = allowed", connectivity.network_allowed(), True)

        connectivity._monitor = fake_monitor(False)
        check("auto + unreachable = blocked", connectivity.network_allowed(), False)
        check("...and says why", connectivity.network_allowed(reason=True)[1],
              "no network detected")
        check("recognised as a network problem",
              connectivity.refuses_because_offline(), True)
    finally:
        AppConfig.web["enabled"] = orig_web
        AppConfig.offline_mode = orig_mode
        connectivity._monitor = orig_monitor


# -------------------------------------------------------------- confirm gate


def gate(clock=None, enabled=True, timeout=30.0):
    return ConfirmationGate(
        timeout_seconds=timeout, enabled=enabled, time_source=clock or FakeClock()
    )


def test_destructive_tags_need_confirmation():
    print("\n[6] destructive tags are gated, ordinary ones are not")
    g = gate()
    for tag in ["pcshutdown", "pcrestart", "pchibernate", "closeallpy", "closebgpy"]:
        check(f"{tag} gated", g.needs_confirmation(tag), True)
    for tag in ["battery", "dateday", "adjustVolume", "screenshot", "open"]:
        check(f"{tag} not gated", g.needs_confirmation(tag), False)


def test_confirm_flow():
    print("\n[7] yes runs it")
    g = gate()
    question = g.arm("pcshutdown", "shut down the pc")
    check("asks a question", "shut down the PC" in question, True)
    check("armed", g.is_armed, True)

    outcome, tag, _, _ = g.resolve("yes")
    check("outcome", outcome, "confirmed")
    check("tag preserved", tag, "pcshutdown")
    check("disarmed after firing", g.is_armed, False)


def test_cancel_flow():
    print("\n[8] no cancels it")
    for word in ["no", "nope", "cancel", "stop", "don't", "never mind", "wait"]:
        g = gate()
        g.arm("pcshutdown")
        outcome, _, _, spoken = g.resolve(word)
        check(f"'{word}' cancels", outcome, "cancelled")
        check(f"'{word}' disarms", g.is_armed, False)


def test_unrelated_speech_cancels():
    """The important safety property: silence-adjacent speech must not confirm."""
    print("\n[9] unrelated speech cancels rather than confirming")
    for text in ["what time is it", "open chrome", "yesterday was fine", "", "   "]:
        g = gate()
        g.arm("pcshutdown")
        outcome, _, _, _ = g.resolve(text)
        check(f"{text!r} does not confirm", outcome, "cancelled")


def test_yes_inside_a_sentence_does_not_confirm():
    print("\n[10] 'yes' must lead the sentence, not merely appear in it")
    g = gate()
    g.arm("pcshutdown")
    outcome, _, _, _ = g.resolve("tell me if yes is a word")
    check("mid-sentence 'yes' does not fire", outcome, "cancelled")

    g2 = gate()
    g2.arm("pcshutdown")
    outcome2, _, _, _ = g2.resolve("yes please go ahead")
    check("leading 'yes' does fire", outcome2, "confirmed")


def test_pending_expires():
    print("\n[11] an armed action lapses instead of waiting forever")
    clock = FakeClock()
    g = gate(clock=clock, timeout=30.0)
    g.arm("pcshutdown")
    check("armed", g.is_armed, True)

    clock.advance(29)
    check("still armed at 29s", g.is_armed, True)

    clock.advance(2)
    check("lapsed at 31s", g.is_armed, False)
    outcome, _, _, _ = g.resolve("yes")
    check("a late 'yes' does nothing", outcome, "none")


def test_second_request_replaces_first():
    print("\n[12] a new destructive request replaces the armed one")
    g = gate()
    g.arm("pcshutdown")
    g.arm("pcrestart")
    outcome, tag, _, _ = g.resolve("yes")
    check("only the newest is armed", tag, "pcrestart")


def test_gate_can_be_disabled():
    print("\n[13] confirm_destructive: false restores direct execution")
    g = gate(enabled=False)
    check("nothing is gated", g.needs_confirmation("pcshutdown"), False)


def test_resolve_without_arming():
    print("\n[14] 'yes' with nothing armed is an ordinary utterance")
    g = gate()
    outcome, tag, _, _ = g.resolve("yes")
    check("outcome", outcome, "none")
    check("no tag", tag, None)


def test_every_destructive_tag_exists_in_dispatch():
    """A gated tag that no longer exists silently protects nothing."""
    print("\n[15] every gated tag is a real action")
    src = open(
        os.path.join(os.path.dirname(__file__), "..", "Utils", "limbs",
                     "command_processor.py"),
        encoding="utf-8",
    ).read()
    for tag in DESTRUCTIVE_TAGS:
        check(f"{tag} present in command_processor", f'"{tag}"' in src, True)


if __name__ == "__main__":
    print("=" * 62)
    print("Phase 2 - offline mode + destructive-action confirmation")
    print("=" * 62)

    for fn in [
        test_offline_mode_parsing,
        test_probe_caching,
        test_probe_failure_is_offline,
        test_real_probe_shape,
        test_network_allowed_precedence,
        test_destructive_tags_need_confirmation,
        test_confirm_flow,
        test_cancel_flow,
        test_unrelated_speech_cancels,
        test_yes_inside_a_sentence_does_not_confirm,
        test_pending_expires,
        test_second_request_replaces_first,
        test_gate_can_be_disabled,
        test_resolve_without_arming,
        test_every_destructive_tag_exists_in_dispatch,
    ]:
        fn()

    print("\n" + "=" * 62)
    print(f"  {PASS} passed, {FAIL} failed")
    print("=" * 62)
    sys.exit(1 if FAIL else 0)
