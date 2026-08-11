"""
Construction smoke test.

Every unit test in this repo can pass while Phoenix is completely dead, because
the failure that actually costs time is not a wrong answer - it is an object
that raises while being built. When that happens in the voice processor there
is no console handler on its logger, so the crash lands in a log file and the
TUI just keeps showing its last status. It looks like a hang.

That is exactly what happened on 2026-08-12: a module-level
`from core.config import AppConfig` was added to command_processor.py while a
function-local import of the same name still existed further down __init__.
Python marks the name local for the whole function body, so the earlier
reference raised UnboundLocalError, PhoenixAssistant never constructed, the
processor exited, and nothing drained the audio queue.

So: actually build the objects. No mocks - a mock would have been built from
the same wrong assumption. No audio device, no Whisper, no Ollama call.

    W:\\workplace-1\\Phoenix\\.venv\\Scripts\\python.exe W:\\workplace-1\\Phoenix\\tests\\test_startup_smoke.py
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PASS = 0
FAIL = 0


def check(label, fn):
    """Run fn(); pass if it returns without raising. Returns its value or None."""
    global PASS, FAIL
    try:
        value = fn()
        PASS += 1
        print(f"  [ok]   {label}")
        return value
    except Exception as exc:
        FAIL += 1
        print(f"  [FAIL] {label}")
        print(f"           {type(exc).__name__}: {exc}")
        for line in traceback.format_exc().splitlines()[-4:-1]:
            print(f"           {line.strip()}")
        return None


def test_imports():
    print("\n[1] every live module imports")
    for name in [
        "core.config",
        "core.queue_server",
        "core.continuous_listener",
        "Utils.ai_manager",
        "Utils.limbs.wake_gate",
        "Utils.limbs.confirm_gate",
        "Utils.limbs.connectivity",
        "Utils.limbs.speech_filters",
        "Utils.limbs.audio_capture",
        "Utils.limbs.queue_manager",
        "Utils.limbs.intent_router",
        "Utils.limbs.tool_registry",
        "Utils.limbs.memory_manager",
        "Utils.limbs.command_processor",
        "Utils.limbs.action_utilities",
        "Utils.limbs.time_handlers",
        "Utils.runners.voice_command_processor",
    ]:
        check(name, lambda n=name: __import__(n, fromlist=["_"]))


def test_config_keys():
    print("\n[2] config keys the code reads actually exist")
    from core.config import AppConfig

    check(
        "audio.followup_window_seconds is a number",
        lambda: float(AppConfig.audio["followup_window_seconds"]),
    )
    check("wake_words is a non-empty list", lambda: AppConfig.wake_words[0])
    check("audio.echo_mode is valid", lambda: {"gate": 1, "open": 1}[AppConfig.audio["echo_mode"]])
    check(
        "tts_engine is a validated value",
        lambda: {"sapi5": 1, "edge": 1}[AppConfig.tts_engine],
    )
    check("sapi_voice is set", lambda: AppConfig.sapi_voice or _raise("empty"))
    check("offline_mode is set", lambda: AppConfig.offline_mode)
    check("confirm_destructive is a bool", lambda: bool(AppConfig.confirm_destructive))
    # Removed keys must stay removed: a stale reader would silently see a default.
    check("piper_voice is gone", lambda: _expect(not hasattr(AppConfig, "piper_voice")))
    check(
        "memory.auto_save is gone",
        lambda: _expect("auto_save" not in AppConfig.memory),
    )


def _raise(msg):
    raise AssertionError(msg)


def _expect(condition):
    if not condition:
        raise AssertionError("condition is false")
    return True


def test_constructs_the_real_objects():
    """The bug this file exists for: __init__ raising, not a method misbehaving."""
    print("\n[3] the objects the processor builds at startup construct")
    from Utils.limbs.action_utilities import Utility, OpenAppHandler, CloseAppHandler
    from Utils.limbs.time_handlers import (
        TimerHandle,
        AlarmHandle,
        ReminderHandle,
        ScheduleHandle,
    )
    from Utils.limbs.command_processor import PhoenixAssistant

    utility = check("Utility()", lambda: Utility(spk=None, reco=None))
    if utility is None:
        return None

    handlers = {}
    for label, cls in [
        ("OpenAppHandler", OpenAppHandler),
        ("CloseAppHandler", CloseAppHandler),
        ("TimerHandle", TimerHandle),
        ("AlarmHandle", AlarmHandle),
        ("ReminderHandle", ReminderHandle),
        ("ScheduleHandle", ScheduleHandle),
    ]:
        handlers[label] = check(f"{label}()", lambda c=cls: c(utility))

    if any(h is None for h in handlers.values()):
        return None

    return check(
        "PhoenixAssistant()  <- the 2026-08-12 UnboundLocalError",
        lambda: PhoenixAssistant(
            utility,
            handlers["OpenAppHandler"],
            handlers["CloseAppHandler"],
            handlers["TimerHandle"],
            handlers["AlarmHandle"],
            handlers["ScheduleHandle"],
            handlers["ReminderHandle"],
        ),
    )


def test_wake_stripping_on_the_live_object(assistant):
    print("\n[4] wake stripping works on the constructed assistant")
    if assistant is None:
        global FAIL
        FAIL += 1
        print("  [FAIL] skipped - PhoenixAssistant did not construct")
        return

    from core.config import AppConfig

    wake = AppConfig.wake_words[0]

    def stripped():
        got = assistant.remove_phoenix_except_folder(f"{wake} what time is it")
        assert got == "what time is it", got
        return got

    def folder_preserved():
        got = assistant.remove_phoenix_except_folder("open phoenix folder")
        assert got == "open phoenix folder", got
        return got

    def plain_untouched():
        got = assistant.remove_phoenix_except_folder("turn it down")
        assert got == "turn it down", got
        return got

    check("wake word stripped", stripped)
    check("'phoenix folder' preserved", folder_preserved)
    check("plain sentence untouched", plain_untouched)


def test_no_local_shadowing_of_module_imports():
    """Static guard against re-introducing the exact 2026-08-12 footgun."""
    print("\n[5] no function-local import shadows a module-level one")
    import ast

    targets = [
        "Utils/limbs/command_processor.py",
        "Utils/runners/voice_command_processor.py",
        "Utils/limbs/intent_router.py",
        "Utils/limbs/tool_registry.py",
    ]
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    for rel in targets:
        path = os.path.join(root, rel)

        def scan(p=path, r=rel):
            tree = ast.parse(open(p, encoding="utf-8").read())
            module_names = set()
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for a in node.names:
                        module_names.add(a.asname or a.name.split(".")[0])

            clashes = []
            for fn in ast.walk(tree):
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for node in ast.walk(fn):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        for a in node.names:
                            name = a.asname or a.name.split(".")[0]
                            if name in module_names:
                                clashes.append(f"{fn.name}() re-imports {name}")
            assert not clashes, f"{r}: " + "; ".join(sorted(set(clashes)))
            return True

        check(rel, scan)


if __name__ == "__main__":
    print("=" * 62)
    print("Startup smoke - does Phoenix actually build?")
    print("=" * 62)

    test_imports()
    test_config_keys()
    assistant = test_constructs_the_real_objects()
    test_wake_stripping_on_the_live_object(assistant)
    test_no_local_shadowing_of_module_imports()

    print("\n" + "=" * 62)
    print(f"  {PASS} passed, {FAIL} failed")
    print("=" * 62)
    sys.exit(1 if FAIL else 0)
