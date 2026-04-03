"""
Debug script to test .speaking file mechanism
Run this while Phoenix is speaking to see if the file is being created/deleted
"""

import os
import time
import sys

speaking_file = ".speaking"

print("=" * 60)
print("MONITORING .speaking FILE")
print("=" * 60)
print("Run Phoenix in another terminal and speak to it.")
print("This script will show when .speaking file appears/disappears.")
print("Press Ctrl+C to stop.")
print("=" * 60)
print()

last_state = None
speaking_start = None

try:
    while True:
        exists = os.path.exists(speaking_file)
        current_time = time.strftime("%H:%M:%S")

        if exists != last_state:
            if exists:
                speaking_start = time.time()
                try:
                    with open(speaking_file, "r") as f:
                        timestamp = f.read().strip()
                    print(
                        f"[{current_time}] 🔊 SPEAKING FLAG SET (timestamp: {timestamp})"
                    )
                except:
                    print(
                        f"[{current_time}] 🔊 SPEAKING FLAG SET (couldn't read timestamp)"
                    )
            else:
                if speaking_start:
                    duration = time.time() - speaking_start
                    print(
                        f"[{current_time}] 🎧 SPEAKING FLAG CLEARED (duration: {duration:.2f}s)"
                    )
                else:
                    print(f"[{current_time}] 🎧 SPEAKING FLAG CLEARED")
            last_state = exists

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\nMonitoring stopped.")
    if os.path.exists(speaking_file):
        print(f"⚠️  Warning: .speaking file still exists (orphaned)")
        try:
            os.remove(speaking_file)
            print("✅ Cleaned up orphaned .speaking file")
        except:
            print("❌ Could not remove .speaking file")
