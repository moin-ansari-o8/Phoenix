"""
Phoenix Folder Reorganization Script
Automatically reorganizes Phoenix folder structure according to REORGANIZATION_PLAN.md
"""

import os
import shutil
from pathlib import Path

# Get root directory
ROOT = Path(__file__).parent

print("=" * 70)
print("PHOENIX FOLDER REORGANIZATION")
print("=" * 70)
print(f"\nRoot: {ROOT}")
print("\n⚠️  WARNING: This will reorganize your entire Phoenix folder!")
print("   - Files will be moved to new organized structure")
print("   - Old folders (MDs/, batch/) will be deleted")
print("   - A backup will NOT be created automatically")
print()

confirm = input("Do you want to proceed? (yes/no): ").strip().lower()
if confirm != "yes":
    print("\n❌ Reorganization cancelled.")
    exit(0)

print("\n" + "=" * 70)
print("STARTING REORGANIZATION...")
print("=" * 70)

# Track moved files
moved_count = 0
error_count = 0


def move_file(src, dest_folder, filename=None):
    """Move file to destination folder"""
    global moved_count, error_count
    try:
        src_path = ROOT / src
        if not src_path.exists():
            print(f"  ⚠️  Skip (not found): {src}")
            return

        dest_path = ROOT / dest_folder
        dest_path.mkdir(parents=True, exist_ok=True)

        if filename:
            dest_file = dest_path / filename
        else:
            dest_file = dest_path / src_path.name

        if dest_file.exists():
            print(f"  ⚠️  Skip (exists): {dest_file.relative_to(ROOT)}")
            return

        shutil.move(str(src_path), str(dest_file))
        print(f"  ✅ {src} → {dest_file.relative_to(ROOT)}")
        moved_count += 1
    except Exception as e:
        print(f"  ❌ Error moving {src}: {e}")
        error_count += 1


# 1. Create new folder structure
print("\n1️⃣  Creating new folders...")
new_folders = [
    "core",
    "docs/guides",
    "docs/analysis",
    "docs/fixes",
    "docs/history",
    "docs/troubleshooting",
    "tests/unit",
    "tests/integration",
    "tests/experimental",
    "tests/debug",
    "scripts/setup",
    "scripts/utilities",
    "scripts/startup",
    "logs",
    "temp",
    "models",
]

for folder in new_folders:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)
    print(f"  📁 Created: {folder}/")

# 2. Move core files
print("\n2️⃣  Moving core application files...")
core_files = [
    "launch_phoenix.py",
    "MainPHNX.py",
    "ListenerPHNX.py",
    "queue_server.py",
    "cmd_gui.py",
]
for f in core_files:
    move_file(f, "core")

# 3. Move documentation - Guides
print("\n3️⃣  Moving documentation - Guides...")
guide_files = [
    "CONTINUOUS_LISTENING_GUIDE.md",
    "HOW_TO_TEST_CONTINUOUS_LISTENING.md",
    "QUICK_TEST_GUIDE.md",
    "UV_GUIDE.md",
    "UV_README.md",
    "PERSONAL_MANAGER_GUIDE.md",
]
for f in guide_files:
    move_file(f, "docs/guides")

# 4. Move documentation - Analysis
print("\n4️⃣  Moving documentation - Analysis...")
analysis_files = [
    "PHOENIX_COMPREHENSIVE_ANALYSIS.md",
    "SENIOR_AI_MENTOR_GUIDE.md",
    "PERFORMANCE_OPTIMIZATION.md",
    "WAKE_WORD_FLOW.md",
]
for f in analysis_files:
    move_file(f, "docs/analysis")

# 5. Move documentation - Fixes
print("\n5️⃣  Moving documentation - Fixes...")
fix_files = [
    "FIX_SELF_VOICE_AND_TIMESTAMPS.md",
    "FIX_APPLIED_NOW.md",
    "FIX_ACCESS_DENIED.md",
    "FINAL_FIX_SHARED_MEMORY.md",
    "SELF_VOICE_SUPPRESSION_ENHANCED.md",
    "FAN_NOISE_FIX.md",
    "QUEUE_SERVER_FIX.md",
    "WHY_NOT_RESPONDING.md",
]
for f in fix_files:
    move_file(f, "docs/fixes")

# 6. Move documentation - History
print("\n6️⃣  Moving documentation - History...")
history_files = [
    "CHANGES_SUMMARY.md",
    "IMPLEMENTATION_SUMMARY.md",
    "BEFORE_AFTER_COMPARISON.md",
    "RECOVERY_AND_SETUP_COMPLETE.md",
    "DEBUG_CONTINUOUS_LISTENING.md",
]
for f in history_files:
    move_file(f, "docs/history")

# 7. Move GitHub docs
print("\n7️⃣  Moving GitHub documentation...")
if (ROOT / ".github/ERROR_HANDLING_FIX.md").exists():
    move_file(".github/ERROR_HANDLING_FIX.md", "docs/fixes")
if (ROOT / ".github/TROUBLESHOOTING.md").exists():
    move_file(".github/TROUBLESHOOTING.md", "docs/troubleshooting")

# 8. Move test files - Unit
print("\n8️⃣  Moving test files - Unit...")
unit_tests = [
    "tests/test_mic.py",
    "tests/test_final_verification.py",
]
for f in unit_tests:
    if (ROOT / f).exists():
        move_file(f, "tests/unit")

# 9. Move test files - Integration
print("\n9️⃣  Moving test files - Integration...")
integration_tests = [
    "test_continuous_listen.py",
    "test_voice_command.py",
    "test_speak.py",
    "test_whisper_quick.py",
]
for f in integration_tests:
    move_file(f, "tests/integration")

# 10. Move test files - Experimental
print("\n🔟 Moving test files - Experimental...")
experimental_tests = [
    "test_bg_startup.py",
    "test_bg_time.py",
    "test_personal_manager.py",
    "test_fixes.py",
    "test_speaking_flag.py",
    "test_offline_tts.py",
    "test_coqui_tts.py",
    "test_piper_voice.py",
    "test_piper_voice_fixed.py",
    "test_piper_working.py",
]
for f in experimental_tests:
    move_file(f, "tests/experimental")

# 11. Move debug files
print("\n1️⃣1️⃣  Moving debug files...")
move_file("debug_speaking_flag.py", "tests/debug")

# 12. Move test utilities
print("\n1️⃣2️⃣  Moving test utilities...")
if (ROOT / "tests/listen.py").exists():
    # Keep in tests root
    pass
if (ROOT / "tests/run_listen.bat").exists():
    # Keep in tests root
    pass

# 13. Move scripts - Setup
print("\n1️⃣3️⃣  Moving scripts - Setup...")
setup_scripts = [
    "uv-setup.ps1",
    "uv-sync.bat",
    "uv-sync.ps1",
    "rename_consoleui.bat",
]
for f in setup_scripts:
    move_file(f, "scripts/setup")

# 14. Move scripts - Utilities
print("\n1️⃣4️⃣  Moving scripts - Utilities...")
utility_scripts = [
    "SortPythonProgram.py",
    "apply_queue_fix.py",
    "download_piper_voices.py",
    "download_piper_voices_fixed.py",
    "load.py",
]
for f in utility_scripts:
    move_file(f, "scripts/utilities")

# 15. Move scripts - Startup
print("\n1️⃣5️⃣  Moving scripts - Startup...")
if (ROOT / "scripts/phoenix.bat").exists():
    move_file("scripts/phoenix.bat", "scripts/startup")
if (ROOT / "batch/on_boot_startup.bat").exists():
    move_file("batch/on_boot_startup.bat", "scripts/startup")
if (ROOT / "batch/main.bat").exists():
    move_file("batch/main.bat", "scripts/startup")

# 16. Move log files
print("\n1️⃣6️⃣  Moving log files...")
log_files = [
    "phoenix_launcher.log",
    "phoenix_listener.log",
    "phoenix_queue.log",
    "bg_voice_processor.log",
    "debug.log",
]
for f in log_files:
    move_file(f, "logs")

# 17. Move temporary files
print("\n1️⃣7️⃣  Moving temporary files...")
temp_files = [
    "coqui_test.wav",
    "test_piper_output.wav",
]
for f in temp_files:
    move_file(f, "temp")

# 18. Move voice models
print("\n1️⃣8️⃣  Moving voice models...")
if (ROOT / "piper_voices").exists():
    try:
        dest = ROOT / "models/piper_voices"
        if not dest.exists():
            shutil.move(str(ROOT / "piper_voices"), str(dest))
            print(f"  ✅ piper_voices/ → models/piper_voices/")
            moved_count += 1
        else:
            print(f"  ⚠️  models/piper_voices/ already exists")
    except Exception as e:
        print(f"  ❌ Error moving piper_voices: {e}")
        error_count += 1

# 19. Delete empty old folders
print("\n1️⃣9️⃣  Cleaning up old folders...")
old_folders = ["MDs", "batch", "scripts"]  # scripts folder if empty
for folder in old_folders:
    folder_path = ROOT / folder
    if folder_path.exists():
        try:
            # Check if empty
            if not list(folder_path.iterdir()):
                folder_path.rmdir()
                print(f"  🗑️  Deleted empty folder: {folder}/")
            else:
                print(f"  ⚠️  {folder}/ not empty, keeping it")
        except Exception as e:
            print(f"  ⚠️  Could not delete {folder}/: {e}")

# Summary
print("\n" + "=" * 70)
print("REORGANIZATION COMPLETE!")
print("=" * 70)
print(f"\n📊 Summary:")
print(f"  ✅ Files moved: {moved_count}")
print(f"  ❌ Errors: {error_count}")
print()
print("📋 Next steps:")
print("  1. Review the new structure")
print("  2. Update import paths in code (if needed)")
print("  3. Update .gitignore for new folders")
print("  4. Test Phoenix: python core/launch_phoenix.py")
print()
print("📝 Note: README.md and other config files kept at root")
print("=" * 70)
