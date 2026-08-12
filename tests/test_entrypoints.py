"""
Every entry point must import when run the way it is actually launched.

This exists because of a real outage on 2026-08-12. `core/launch_phoenix.py`
gained `from core.logging_setup import setup_logging` during the logging
unification, but that file had never needed a sys.path fix before - it only
called `logging.basicConfig()`, which imports nothing from the package.

Run as a script, `python core/launch_phoenix.py` puts `core/` on sys.path,
not the repo root, so `import core.*` raised ModuleNotFoundError at line 16.
The launcher died instantly, which meant no queue server, no listener and no
processor - and the TUI, which starts fine on its own, sat on
"Listening - say 'phoenix'..." forever with nothing behind it.

Nothing caught it. Every unit test imported these modules with the repo root
already on sys.path, which is exactly the condition that does not hold in
production. So this test spawns a real subprocess per entry point with
sys.path[0] set to the script's own directory, the way Python does it.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe -m pytest W:\\workplace-1\\Phoenix\\tests\\test_entrypoints.py -q
"""

import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Scripts the runtime launches as `python <path>`. Importing each one must
# succeed with only its own directory on sys.path.
ENTRY_POINTS = [
    os.path.join("core", "launch_phoenix.py"),
    os.path.join("core", "queue_server.py"),
    os.path.join("core", "continuous_listener.py"),
    os.path.join("Utils", "runners", "voice_command_processor.py"),
]


@pytest.mark.parametrize("relative", ENTRY_POINTS)
def test_entry_point_imports_as_a_script(relative):
    """
    Import the module with sys.path[0] = its own directory.

    Every one of these has an `if __name__ == "__main__"` guard, so importing
    runs the module body - imports, logging setup, class definitions - without
    starting a server, opening the microphone or spawning children.
    """
    path = os.path.join(ROOT, relative)
    assert os.path.exists(path), f"{relative} is missing"

    directory = os.path.dirname(path)
    module = os.path.splitext(os.path.basename(path))[0]

    probe = (
        "import sys\n"
        f"sys.path.insert(0, r'{directory}')\n"
        f"import {module}\n"
        "print('OK')\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )

    if result.returncode != 0 or "OK" not in result.stdout:
        tail = (result.stderr or result.stdout or "").strip().splitlines()[-12:]
        pytest.fail(
            f"{relative} does not import when launched as a script:\n"
            + "\n".join(tail),
            pytrace=False,
        )


@pytest.mark.parametrize("relative", ENTRY_POINTS)
def test_package_imports_come_after_the_path_fix(relative):
    """
    Static guard, so the failure is a red test rather than a dead assistant.

    A `from core.x` / `from Utils.x` line above the sys.path setup is the exact
    shape of the outage above.
    """
    import re

    lines = open(os.path.join(ROOT, relative), encoding="utf-8").read().splitlines()

    first_package_import = next(
        (i for i, line in enumerate(lines) if re.match(r"\s*from (core|Utils)[. ]", line)),
        None,
    )
    if first_package_import is None:
        return

    # Either insert() or append() counts - both put the repo root on the path.
    path_fix = next(
        (i for i, line in enumerate(lines) if re.search(r"sys\.path\.(insert|append)", line)),
        None,
    )

    assert path_fix is not None, (
        f"{relative} imports from the package at line {first_package_import + 1} "
        f"but never puts the repo root on sys.path"
    )
    assert path_fix < first_package_import, (
        f"{relative} sets sys.path at line {path_fix + 1}, which is AFTER its "
        f"first package import at line {first_package_import + 1}"
    )
