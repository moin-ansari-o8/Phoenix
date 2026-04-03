"""Final verification test for Personal Manager integration."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers.PersonalManagerPHNX import PersonalManager
from helpers.HelperPHNX import SpeechEngine


def test_speech_engine():
    """Test SpeechEngine initialization."""
    print("\n=== Testing SpeechEngine ===")
    try:
        engine = SpeechEngine()
        print(f"✓ SpeechEngine initialized successfully")
        print(
            f"  Engine status: {'Available' if engine.engine is not None else 'Print-only mode'}"
        )

        # Test speaking
        engine.speak("Phoenix is now ready")
        print("✓ Speech test completed")
        return True
    except Exception as e:
        print(f"✗ SpeechEngine test failed: {e}")
        return False


def test_personal_manager():
    """Test Personal Manager functionality."""
    print("\n=== Testing Personal Manager ===")
    try:
        pm = PersonalManager()
        print("✓ PersonalManager initialized")

        # Get startup summary
        summary = pm.get_startup_summary()
        formatted_msg = pm.format_startup_message(summary)
        print(f"✓ Startup message: {formatted_msg}")

        # Test adding a todo
        pm.todos.add_todo("Test Phoenix setup", "today")
        print("✓ Added test todo")

        # Get pending todos
        pending_today = pm.todos.get_pending_todos("today")
        pending_tomorrow = pm.todos.get_pending_todos("tomorrow")
        print(
            f"✓ Pending todos: {len(pending_today)} today, {len(pending_tomorrow)} tomorrow"
        )

        # Mark as completed
        if pending_today:
            pm.todos.mark_completed(pending_today[0]["id"])
            print("✓ Marked todo as completed")

        return True
    except Exception as e:
        print(f"✗ Personal Manager test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ollama_helper():
    """Test Ollama helper functionality."""
    print("\n=== Testing Ollama Helper ===")
    try:
        from helpers.OllamaHelperPHNX import OllamaHelper

        helper = OllamaHelper()

        # Check status
        status = helper.check_ollama_status()
        print(f"  Ollama status: {status['status']}")
        if status["status"] == "online":
            print(f"  Model available: {status['model_available']}")
            print(f"  Available models: {', '.join(status['available_models'])}")

        if status["status"] != "online":
            print("  ⚠ Ollama not running, skipping LLM tests")
            return True

        # Test intent extraction
        test_text = "Add a project called Test Project with status in progress"
        intent = helper.extract_intent(test_text)
        print(f"✓ Intent extraction: {intent}")

        return True
    except Exception as e:
        print(f"✗ Ollama helper test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("PHOENIX PERSONAL MANAGER - FINAL VERIFICATION")
    print("=" * 60)

    results = []

    # Test 1: Speech Engine
    results.append(("SpeechEngine", test_speech_engine()))

    # Test 2: Personal Manager
    results.append(("Personal Manager", test_personal_manager()))

    # Test 3: Ollama Helper
    results.append(("Ollama Helper", test_ollama_helper()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All systems ready! Phoenix Personal Manager is operational.")
    else:
        print("\n⚠ Some tests failed. Please check the errors above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
