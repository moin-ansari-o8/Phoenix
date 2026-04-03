# Phoenix Project - Agent Instructions

## 🎯 Purpose
These instructions guide AI agents (GitHub Copilot, etc.) to maintain Phoenix's organized folder structure and prevent file clutter.

---

## 📁 Phoenix Folder Structure

```
Phoenix/
├── core/              # Main application entry points
├── helpers/           # Reusable helper modules
├── bgprogs/           # Background processors
├── docs/              # ALL documentation (organized by type)
├── tests/             # ALL tests (organized by type)
├── scripts/           # ALL scripts (organized by purpose)
├── logs/              # Log files (gitignored)
├── temp/              # Temporary files (gitignored)
├── models/            # AI models and voice files
├── assets/            # Static assets (images, sounds)
├── data/              # User data and configs
├── gui/               # GUI components
├── trials/            # Experimental/legacy code
└── NetMonitor/        # Network monitoring module
```

---

## 🚨 CRITICAL RULES - Always Follow

### 1. **NEVER Create Files at Root Level**
❌ **DON'T:**
```
Phoenix/
├── new_feature_doc.md        # ❌ WRONG
├── test_something.py         # ❌ WRONG
├── fix_bug.md                # ❌ WRONG
└── temp_script.py            # ❌ WRONG
```

✅ **DO:**
```
Phoenix/
├── docs/analysis/new_feature_doc.md      # ✅ CORRECT
├── tests/experimental/test_something.py  # ✅ CORRECT
├── docs/fixes/fix_bug.md                 # ✅ CORRECT
└── scripts/utilities/temp_script.py      # ✅ CORRECT
```

**Exception:** Only these files allowed at root:
- Configuration: `.gitignore`, `pyproject.toml`, `Requirements.txt`, `uv.lock`
- Documentation: `README.md`, `LICENSE`
- Special: `.python-version`

---

## 📋 File Placement Rules

### Documentation Files (.md, .txt, .pdf)

**Ask yourself: What is this document about?**

| Document Type | Location | Examples |
|--------------|----------|----------|
| **User guides** | `docs/guides/` | How-to guides, tutorials, usage instructions |
| **Architecture/Analysis** | `docs/analysis/` | Code analysis, system design, architecture docs |
| **Bug fixes** | `docs/fixes/` | Fix documentation, issue resolutions |
| **Change history** | `docs/history/` | Changelogs, implementation summaries |
| **Troubleshooting** | `docs/troubleshooting/` | Problem-solving guides, FAQ |
| **Feature specs** | `docs/specs/` | Feature specifications, requirements (create if needed) |

**Examples:**
```markdown
# ✅ CORRECT placements:
docs/guides/HOW_TO_USE_WHISPER.md              # User guide
docs/analysis/VOICE_PIPELINE_ARCHITECTURE.md   # Architecture
docs/fixes/FIX_MICROPHONE_ISSUE.md            # Bug fix doc
docs/history/VERSION_2_MIGRATION.md            # Change history
docs/troubleshooting/EDGE_TTS_ISSUES.md        # Troubleshooting
```

---

### Python Files (.py)

**Ask yourself: What does this file do?**

| File Type | Location | Naming Convention |
|-----------|----------|-------------------|
| **Main entry points** | `core/` | `*PHNX.py`, `launch_*.py` |
| **Helper modules** | `helpers/` | `*PHNX.py` (reusable utilities) |
| **Background processes** | `bgprogs/` | `Bg*.pyw` (hidden processes) |
| **Unit tests** | `tests/unit/` | `test_*.py` (single module tests) |
| **Integration tests** | `tests/integration/` | `test_*.py` (multi-module tests) |
| **Experimental tests** | `tests/experimental/` | `test_*.py` (trials, POCs) |
| **Debug utilities** | `tests/debug/` | `debug_*.py` (debugging tools) |
| **Setup scripts** | `scripts/setup/` | `*setup*.py`, `install*.py` |
| **Utility scripts** | `scripts/utilities/` | One-off scripts, converters |
| **Startup scripts** | `scripts/startup/` | Auto-run scripts |

**Decision Tree:**
```
Is it a test?
├─ Yes → tests/[unit|integration|experimental|debug]/
└─ No → Is it a script/utility?
    ├─ Yes → scripts/[setup|utilities|startup]/
    └─ No → Is it core functionality?
        ├─ Yes → Is it reusable?
        │   ├─ Yes → helpers/
        │   └─ No → core/
        └─ No → Is it background process?
            ├─ Yes → bgprogs/
            └─ No → trials/ (if experimental)
```

**Examples:**
```python
# ✅ CORRECT placements:
core/launch_phoenix.py                    # Main launcher
helpers/AudioProcessorPHNX.py             # Reusable audio helper
bgprogs/BgVoiceProcessorPHNX.pyw         # Background processor
tests/unit/test_speech_engine.py          # Unit test
tests/integration/test_full_pipeline.py   # Integration test
tests/experimental/test_new_tts.py        # Experimental feature
scripts/utilities/convert_audio.py        # Utility script
```

---

### Script Files (.bat, .ps1, .sh)

| Script Purpose | Location |
|----------------|----------|
| **Environment setup** | `scripts/setup/` |
| **Build/install scripts** | `scripts/setup/` |
| **Utility/helper scripts** | `scripts/utilities/` |
| **Startup/boot scripts** | `scripts/startup/` |

**Examples:**
```bash
# ✅ CORRECT:
scripts/setup/uv-setup.ps1           # Environment setup
scripts/utilities/clean_logs.bat     # Utility
scripts/startup/phoenix.bat          # Startup script
```

---

### Log Files (.log)

**ALL log files → `logs/`**

```bash
# ✅ CORRECT:
logs/phoenix_launcher.log
logs/debug.log
logs/error.log
```

**Configure logging in code:**
```python
import logging
from pathlib import Path

log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(filename=log_dir / "mymodule.log")
```

---

### Temporary Files (.wav, .mp3, .tmp, test outputs)

**ALL temporary files → `temp/`**

```bash
# ✅ CORRECT:
temp/test_audio.wav
temp/cached_response.json
temp/debug_output.txt
```

**Configure in code:**
```python
from pathlib import Path

temp_dir = Path(__file__).parent.parent / "temp"
temp_dir.mkdir(exist_ok=True)
output_file = temp_dir / "test_audio.wav"
```

---

### Model Files (.onnx, .pt, .pth, voice files)

**ALL AI models → `models/[model_name]/`**

```bash
# ✅ CORRECT:
models/piper_voices/en_US-lessac-medium.onnx
models/whisper/medium.pt
models/custom/my_model.pth
```

---

## 🔄 Refactoring Existing Code

**When moving files, update imports!**

### Example: Moving file from root to organized folder

**Before:**
```
Phoenix/
├── my_helper.py          # ❌ Root level
└── core/
    └── main.py           # imports ../my_helper
```

**After:**
```
Phoenix/
├── helpers/
│   └── my_helper.py      # ✅ Moved to helpers/
└── core/
    └── main.py           # Update: from helpers.my_helper import ...
```

**Update imports in `core/main.py`:**
```python
# ❌ OLD (breaks after move):
from my_helper import something

# ✅ NEW (works after move):
from helpers.my_helper import something
# OR
from ..helpers.my_helper import something  # relative import
```

---

## 🆕 Creating New Features

**Before creating files, ask:**
1. What is the file's purpose?
2. Which category does it belong to?
3. Does the target folder exist? (Create if needed)

**Example: Adding new TTS system**

```
1. Create feature branch
2. Add implementation:
   ✅ helpers/TTSEnginePHNX.py       # Core implementation
   
3. Add tests:
   ✅ tests/unit/test_tts_engine.py           # Unit tests
   ✅ tests/integration/test_tts_pipeline.py  # Integration tests
   
4. Add documentation:
   ✅ docs/guides/HOW_TO_USE_TTS.md           # User guide
   ✅ docs/analysis/TTS_ARCHITECTURE.md       # Technical doc
   
5. Add utilities (if needed):
   ✅ scripts/utilities/download_tts_models.py  # Helper script
```

---

## 🛠️ Common Scenarios

### Scenario 1: "I'm creating a quick test"
```python
# ❌ DON'T: Phoenix/quick_test.py
# ✅ DO:     Phoenix/tests/experimental/quick_test.py
```

### Scenario 2: "I'm documenting a bug fix"
```markdown
# ❌ DON'T: Phoenix/BUG_FIX.md
# ✅ DO:     Phoenix/docs/fixes/FIX_AUDIO_LATENCY.md
```

### Scenario 3: "I need a utility script"
```python
# ❌ DON'T: Phoenix/convert_data.py
# ✅ DO:     Phoenix/scripts/utilities/convert_data.py
```

### Scenario 4: "I'm adding a new helper module"
```python
# ❌ DON'T: Phoenix/utils.py
# ✅ DO:     Phoenix/helpers/UtilsPHNX.py
```

### Scenario 5: "I'm creating debug output"
```python
# ❌ DON'T: output.log, debug.txt (at root)
# ✅ DO:     logs/module_debug.log, temp/debug_output.txt
```

---

## 📊 Folder-Specific Guidelines

### `core/` - Application Entry Points
- **What goes here:** Main launchers, primary application files
- **Characteristics:** Files that start the application
- **Naming:** `launch_*.py`, `Main*.py`, `*PHNX.py`
- **Size:** Keep small (< 10 files)

### `helpers/` - Reusable Modules
- **What goes here:** Shared utilities used by multiple modules
- **Characteristics:** Pure functionality, no main() execution
- **Naming:** `*PHNX.py` (follows Phoenix convention)
- **Design:** Each file should have single responsibility

### `bgprogs/` - Background Processors
- **What goes here:** Long-running background processes
- **Characteristics:** Hidden windows (.pyw), continuous execution
- **Naming:** `Bg*PHNX.pyw`
- **Size:** Keep minimal, one per background task

### `docs/` - ALL Documentation
- **Subfolders:** guides, analysis, fixes, history, troubleshooting
- **Rule:** No markdown files outside docs/ (except root README.md)
- **Naming:** `UPPERCASE_WITH_UNDERSCORES.md` for visibility

### `tests/` - ALL Tests
- **Subfolders:** unit, integration, experimental, debug
- **Naming:** `test_*.py` or `debug_*.py`
- **Rule:** Test files NEVER in root or other folders

### `scripts/` - ALL Scripts
- **Subfolders:** setup, utilities, startup
- **Characteristics:** Standalone executables
- **Rule:** Batch/PS1 files NEVER in root

### `logs/` - Ephemeral Logs
- **Gitignored:** Yes (add to .gitignore)
- **Auto-cleanup:** Consider log rotation
- **Naming:** `[module]_[purpose].log`

### `temp/` - Temporary Files
- **Gitignored:** Yes (add to .gitignore)
- **Auto-cleanup:** Clean regularly
- **Purpose:** Test outputs, cached data, temporary audio

### `models/` - AI Models
- **Subfolders:** One per model type
- **Size:** Large files, consider .gitignore
- **Versioning:** Include version in folder name if multiple versions

---

## ✅ Pre-Commit Checklist

Before committing, verify:

- [ ] No new files at root level (except config files)
- [ ] All .md files in `docs/[subfolder]/`
- [ ] All test files in `tests/[subfolder]/`
- [ ] All scripts in `scripts/[subfolder]/`
- [ ] Log files in `logs/` and gitignored
- [ ] Temp files in `temp/` and gitignored
- [ ] Imports updated after moving files
- [ ] No broken imports (test with: `python -m py_compile [file]`)

---

## 🚫 Anti-Patterns (DON'T DO THIS)

```
❌ Phoenix/test.py                    # Test at root
❌ Phoenix/FIX.md                     # Doc at root
❌ Phoenix/script.bat                 # Script at root
❌ Phoenix/output.log                 # Log at root
❌ Phoenix/helpers/test_helper.py    # Test in helpers/
❌ Phoenix/core/documentation.md      # Doc in core/
❌ Phoenix/temp_file.wav              # Temp at root
```

---

## 🎓 Learning Resources

- **See reorganization plan:** `REORGANIZATION_PLAN.md`
- **Quick reference:** `REORGANIZATION_QUICKSTART.md`
- **Project overview:** `docs/analysis/PHOENIX_COMPREHENSIVE_ANALYSIS.md`

---

## 🤖 For AI Agents

**When generating code/files:**

1. **Determine file type and purpose FIRST**
2. **Choose correct folder from structure above**
3. **Create subfolder if it doesn't exist**
4. **Use proper naming conventions**
5. **Update related files if moving existing code**
6. **Add to .gitignore if ephemeral (logs, temp)**

**Never assume root is appropriate unless:**
- It's a standard config file (pyproject.toml, Requirements.txt)
- It's the main README.md or LICENSE

**When in doubt:**
- Tests → `tests/experimental/`
- Docs → `docs/guides/`
- Scripts → `scripts/utilities/`
- Temp outputs → `temp/`

---

## 📞 Questions?

If uncertain about file placement:
1. Check similar existing files
2. Review folder descriptions above
3. Use decision trees provided
4. Default to more specific over general (e.g., `tests/experimental/` over `trials/`)

**Maintain this structure religiously to keep Phoenix organized and maintainable! 🚀**
