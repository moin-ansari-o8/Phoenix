"""
pytest entry point for the standalone suites.

Most of Phoenix's tests are self-contained scripts with their own `check()`
harness and a `__main__` block. That was a deliberate choice - they had to be
runnable when pytest was declared as a dev dependency but never actually
installed - and they stay that way, because running one directly is still the
fastest way to debug a single subsystem.

This file makes `pytest` run all of them, so there is one command that covers
everything:

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe -m pytest W:\\workplace-1\\Phoenix\\tests -q

Each suite runs in its own subprocess. That is the point: several of them
mutate AppConfig (web.enabled, offline_mode) and one replaces functions in
Utils.limbs.web_search with tripwires. Sharing an interpreter would let those
leak between suites and produce failures that depend on collection order.

Suites needing a live Ollama are marked `slow` and skipped by default:

    ... -m slow        run only those
    ... -m "not slow"  the default
"""

import os
import subprocess
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS_DIR)

# (module, needs_ollama)
SUITES = [
    ("test_startup_smoke", False),
    ("test_wake_gate", False),
    ("test_web_gate", False),
    ("test_offline_mode", False),
    ("test_listener_pipeline", False),
    ("test_lexicon", False),
    ("test_speaker_id", False),
    ("test_honesty", False),
    ("test_routing", True),
]


def _run(module):
    path = os.path.join(TESTS_DIR, f"{module}.py")
    if not os.path.exists(path):
        pytest.skip(f"{module}.py not present")
    proc = subprocess.run(
        [sys.executable, path],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if proc.returncode != 0:
        # Surface the suite's own output - its check() lines say which
        # assertion failed far better than a return code does.
        tail = "\n".join((proc.stdout or "").splitlines()[-40:])
        pytest.fail(f"{module} failed (exit {proc.returncode}):\n{tail}", pytrace=False)
    return proc.stdout


@pytest.mark.parametrize(
    "module", [m for m, slow in SUITES if not slow]
)
def test_suite(module):
    _run(module)


@pytest.mark.slow
@pytest.mark.parametrize("module", [m for m, slow in SUITES if slow])
def test_slow_suite(module):
    _run(module)
