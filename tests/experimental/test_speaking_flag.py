"""
Quick test to verify shared memory speaking flag works
"""

import time
import sys

print("=" * 60)
print("TESTING SHARED MEMORY SPEAKING FLAG")
print("=" * 60)

try:
    from Utils.limbs.queue_manager import QueueManager

    print("\n1. Connecting to queue server...")
    qm = QueueManager()
    print("   ✅ Connected!")

    print("\n2. Testing speaking flag...")

    # Test initial state
    is_speaking = qm.is_speaking()
    print(f"   Initial state: is_speaking = {is_speaking}")
    if is_speaking:
        print("   ⚠️  Warning: Speaking flag should be False initially")

    # Test setting flag
    print("\n3. Setting speaking flag to True...")
    qm.set_speaking(True)
    time.sleep(0.1)

    is_speaking = qm.is_speaking()
    print(f"   Result: is_speaking = {is_speaking}")
    if is_speaking:
        print("   ✅ Speaking flag set successfully!")
    else:
        print("   ❌ ERROR: Flag should be True but it's False")

    # Test clearing flag
    print("\n4. Setting speaking flag to False...")
    qm.set_speaking(False)
    time.sleep(0.1)

    is_speaking = qm.is_speaking()
    print(f"   Result: is_speaking = {is_speaking}")
    if not is_speaking:
        print("   ✅ Speaking flag cleared successfully!")
    else:
        print("   ❌ ERROR: Flag should be False but it's True")

    print("\n" + "=" * 60)
    print("TEST COMPLETE!")
    print("=" * 60)
    print("\nIf all tests passed, the shared memory flag is working.")
    print("You can now run Phoenix and it should NOT hear itself!")
    print("\nNext: python launch_phoenix.py")

except ConnectionRefusedError:
    print("\n❌ ERROR: Queue server not running!")
    print("   Start it first: python queue_server.py")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback

    traceback.print_exc()
