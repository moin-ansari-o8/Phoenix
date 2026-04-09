"""
Phoenix Folder Structure Validator
Checks if files are in correct locations according to organization rules
"""

from pathlib import Path
import re

ROOT = Path(__file__).parent
ISSUES = []
WARNINGS = []

# Files allowed at root
ALLOWED_ROOT_FILES = {
    ".gitignore",
    ".python-version",
    "LICENSE",
    "README.md",
    "Requirements.txt",
    "pyproject.toml",
    "uv.lock",
    "reorganize_phoenix.py",
    "validate_structure.py",
    "REORGANIZATION_PLAN.md",
    "REORGANIZATION_QUICKSTART.md",
    "main.py",
}

ALLOWED_ROOT_DIRS = {
    ".git",
    ".github",
    ".venv",
    "__pycache__",
    "core",
    "utils",
    "docs",
    "tests",
    "scripts",
    "logs",
    "temp",
    "models",
    "assets",
    "data",
    "gui",
    "trials",
    "NetMonitor",
    "5.9.0",
    "MDs",
    "batch",  # Legacy folders
}

print("=" * 70)
print("PHOENIX FOLDER STRUCTURE VALIDATOR")
print("=" * 70)
print()

# Check 1: Files at root level
print("1️⃣  Checking root level files...")
root_files = [f for f in ROOT.iterdir() if f.is_file()]
for file in root_files:
    if file.name not in ALLOWED_ROOT_FILES:
        if file.suffix in [
            ".md",
            ".py",
            ".bat",
            ".ps1",
            ".log",
            ".wav",
            ".mp3",
            ".tmp",
        ]:
            ISSUES.append(f"❌ File at root should be moved: {file.name}")
        else:
            WARNINGS.append(f"⚠️  Unexpected file at root: {file.name}")

# Check 2: Markdown files outside docs/
print("2️⃣  Checking markdown file locations...")
md_files = list(ROOT.glob("**/*.md"))
for md_file in md_files:
    rel_path = md_file.relative_to(ROOT)

    # Skip if in docs/ or allowed at root
    if str(rel_path).startswith("docs" + ("\\" if "\\" in str(rel_path) else "/")):
        continue
    if md_file.parent == ROOT and md_file.name in ALLOWED_ROOT_FILES:
        continue
    if str(rel_path).startswith(".github"):
        continue
    if str(rel_path).startswith(".venv"):
        continue
    if str(rel_path).startswith("tests") and md_file.name == "README.md":
        continue

    # Issue: MD file not in docs/
    ISSUES.append(f"❌ Markdown file should be in docs/: {rel_path}")

# Check 3: Test files outside tests/
print("3️⃣  Checking test file locations...")
test_files = list(ROOT.glob("**/*.py"))
for test_file in test_files:
    if test_file.name.startswith("test_") or test_file.name.startswith("debug_"):
        rel_path = test_file.relative_to(ROOT)

        # Skip if already in tests/ or .venv
        if str(rel_path).startswith("tests" + ("\\" if "\\" in str(rel_path) else "/")):
            continue
        if str(rel_path).startswith(".venv"):
            continue

        # Issue: Test file not in tests/
        ISSUES.append(f"❌ Test file should be in tests/: {rel_path}")

# Check 4: Scripts outside scripts/
print("4️⃣  Checking script locations...")
script_files = list(ROOT.glob("**/*.bat")) + list(ROOT.glob("**/*.ps1"))
for script in script_files:
    rel_path = script.relative_to(ROOT)

    # Skip if in scripts/ or .venv
    if str(rel_path).startswith("scripts" + ("\\" if "\\" in str(rel_path) else "/")):
        continue
    if str(rel_path).startswith(".venv"):
        continue
    if str(rel_path).startswith("batch"):  # Legacy folder
        WARNINGS.append(f"⚠️  Script in legacy batch/ folder: {rel_path}")
        continue

    # Issue: Script not in scripts/
    ISSUES.append(f"❌ Script should be in scripts/: {rel_path}")

# Check 5: Log files
print("5️⃣  Checking log file locations...")
log_files = list(ROOT.glob("**/*.log"))
for log_file in log_files:
    rel_path = log_file.relative_to(ROOT)

    # Skip if in logs/ or .venv
    if str(rel_path).startswith("logs" + ("\\" if "\\" in str(rel_path) else "/")):
        continue
    if str(rel_path).startswith(".venv"):
        continue

    # Issue: Log file not in logs/
    ISSUES.append(f"❌ Log file should be in logs/: {rel_path}")

# Check 6: Temp audio files
print("6️⃣  Checking temporary file locations...")
temp_patterns = ["*.wav", "*.mp3", "*_output.*", "*.tmp"]
for pattern in temp_patterns:
    temp_files = list(ROOT.glob(pattern))
    for temp_file in temp_files:
        rel_path = temp_file.relative_to(ROOT)

        # Skip if in temp/, models/, or .venv
        if any(
            str(rel_path).startswith(f) for f in ["temp", "models", ".venv", "assets"]
        ):
            continue

        # Issue: Temp file not in temp/
        if temp_file.parent == ROOT:
            ISSUES.append(f"❌ Temporary file should be in temp/: {rel_path}")

# Check 7: Legacy folders
print("7️⃣  Checking for legacy folders...")
legacy_folders = ["MDs", "batch"]
for folder in legacy_folders:
    if (ROOT / folder).exists():
        contents = list((ROOT / folder).iterdir())
        if contents:
            WARNINGS.append(
                f"⚠️  Legacy folder '{folder}/' still has {len(contents)} items - consider moving"
            )

# Print results
print()
print("=" * 70)
print("VALIDATION RESULTS")
print("=" * 70)
print()

if not ISSUES and not WARNINGS:
    print("✅ PERFECT! All files are correctly organized!")
    print()
    print("Your folder structure follows all guidelines.")
else:
    if ISSUES:
        print(f"❌ {len(ISSUES)} ISSUE(S) FOUND:")
        print()
        for issue in ISSUES:
            print(f"  {issue}")
        print()

    if WARNINGS:
        print(f"⚠️  {len(WARNINGS)} WARNING(S):")
        print()
        for warning in WARNINGS:
            print(f"  {warning}")
        print()

    print("📋 Suggested Actions:")
    print()
    if ISSUES:
        print("  1. Run: python reorganize_phoenix.py")
        print("     (Automatically moves files to correct locations)")
        print()
        print("  2. Or move files manually according to guidelines:")
        print("     - See .github/AGENT.md for full rules")
        print("     - See .github/copilot-instructions.md for quick ref")
        print()

    if any("Legacy folder" in w for w in WARNINGS):
        print("  3. Merge legacy folders:")
        print("     - Move MDs/ contents to docs/")
        print("     - Move batch/ contents to scripts/startup/")
        print("     - Delete empty folders")
        print()

print("=" * 70)
print("📖 Documentation: .github/AGENT.md")
print("=" * 70)
