"""
Proves `web.enabled: false` actually stops network access.

Before 2026-08-12 this key was parsed by core/config.py and read by nobody, so
the one switch a user would reach for to make Phoenix offline did nothing at
all. A test that only checked the config value would still have passed. So this
test does the opposite: it makes the network layer EXPLODE if touched, then
asserts every path refuses cleanly instead.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\tests\\test_web_gate.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config import AppConfig  # noqa: E402
from Utils.limbs import tool_registry  # noqa: E402
import Utils.limbs.web_search as web_search  # noqa: E402

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


class NetworkTouched(AssertionError):
    """Raised if anything reaches for the network while the web is disabled."""


def arm_tripwire():
    """Replace every outbound helper with something that fails loudly."""
    def boom(*a, **k):
        raise NetworkTouched("network helper called while web.enabled is false")

    web_search.gather_context = boom
    web_search.wiki_summary = boom


def call(name, args, query=""):
    """dispatch() returning either its result kind or the tripwire failure."""
    try:
        res = tool_registry.dispatch(name, args, original_query=query)
        return res.get("kind"), (res.get("spoken") or "")
    except NetworkTouched:
        return "NETWORK_TOUCHED", ""


def test_gate_reads_config():
    print("\n[1] web_allowed() reflects config")
    AppConfig.web["enabled"] = True
    check("enabled -> True", tool_registry.web_allowed(), True)
    AppConfig.web["enabled"] = False
    check("disabled -> False", tool_registry.web_allowed(), False)


def blocked_ok(kind, spoken):
    """
    A blocked lookup may end two legitimate ways, and which one depends on
    whether an offline archive happens to be installed:

      "direct"   + a refusal notice        - nothing local to say
      "evidence" + text from data/zim/*    - answered from the local archive

    Both are correct. The thing that must NEVER happen is reaching the network,
    which the tripwire turns into "NETWORK_TOUCHED", or quietly answering from
    the model's training data, which would return "direct" with no notice.
    """
    if kind == "evidence":
        return True
    return kind == "direct" and spoken in (
        tool_registry.OFFLINE_NOTICE,
        tool_registry.NO_NETWORK_NOTICE,
    )


def test_search_web_blocked():
    print("\n[2] search_web answers locally or refuses - never fetches")
    AppConfig.web["enabled"] = False
    kind, spoken = call("search_web", {"query": "population of france"})
    check("does not reach the network", kind != "NETWORK_TOUCHED", True)
    check("refuses or answers from the local archive", blocked_ok(kind, spoken), True)


def test_encyclopedia_blocked():
    print("\n[3] lookup_encyclopedia answers locally or refuses")
    AppConfig.web["enabled"] = False
    kind, spoken = call("lookup_encyclopedia", {"topic": "ada lovelace"})
    check("does not reach the network", kind != "NETWORK_TOUCHED", True)
    check("refuses or answers from the local archive", blocked_ok(kind, spoken), True)


def test_refusal_without_an_archive():
    """With no local archive there is nothing to fall back on - it must refuse."""
    print("\n[3b] with the archive stubbed out, a refusal is still a refusal")
    AppConfig.web["enabled"] = False
    original = tool_registry._offline_evidence
    try:
        tool_registry._offline_evidence = lambda topic: None
        kind, spoken = call("search_web", {"query": "population of france"})
        check("refuses", kind, "direct")
        check(
            "says so out loud",
            spoken in (tool_registry.OFFLINE_NOTICE, tool_registry.NO_NETWORK_NOTICE),
            True,
        )
    finally:
        tool_registry._offline_evidence = original


def test_fresh_data_upgrade_blocked():
    """The important one: this path used to silently become a web search."""
    print("\n[4] the answer_directly -> search_web upgrade is blocked")
    AppConfig.web["enabled"] = False

    query = "who is the current prime minister"
    check("query is recognised as time-sensitive",
          tool_registry.needs_fresh_data(query), True)

    kind, spoken = call("answer_directly", {"answer": ""}, query=query)
    check("does not reach the network", kind != "NETWORK_TOUCHED", True)
    check(
        "never answers a time-sensitive question from stale training data",
        blocked_ok(kind, spoken),
        True,
    )


def test_device_queries_unaffected():
    print("\n[5] local queries still work with the web off")
    AppConfig.web["enabled"] = False
    kind, _ = call("answer_directly", {"answer": "It is 5 pm."},
                   query="what time is it")
    check("no refusal for a local question", kind != "NETWORK_TOUCHED", True)
    check("not time-sensitive", tool_registry.needs_fresh_data("what time is it"), False)


if __name__ == "__main__":
    print("=" * 62)
    print("web.enabled gate - does 'offline' actually mean offline?")
    print("=" * 62)

    arm_tripwire()
    original = AppConfig.web.get("enabled", True)
    try:
        test_gate_reads_config()
        test_search_web_blocked()
        test_encyclopedia_blocked()
        test_refusal_without_an_archive()
        test_fresh_data_upgrade_blocked()
        test_device_queries_unaffected()
    finally:
        AppConfig.web["enabled"] = original

    print("\n" + "=" * 62)
    print(f"  {PASS} passed, {FAIL} failed")
    print("=" * 62)
    sys.exit(1 if FAIL else 0)
