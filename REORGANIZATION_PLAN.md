# Phoenix Folder Reorganization Plan

## 📊 Current State Analysis

**Total Files Analyzed:**
- 27 Markdown (.md) files
- 37+ Python (.py) files  
- 6 Batch (.bat) files
- Multiple subdirectories with scattered files

**Problem:** Files are mixed at root level, making it hard to navigate and maintain.

---

## 🎯 Proposed New Structure

```
Phoenix/
├── 📁 core/                          # Core application files
│   ├── launch_phoenix.py             # Main launcher
│   ├── MainPHNX.py                   # Original main file
│   ├── ListenerPHNX.py               # Audio listener
│   ├── queue_server.py               # IPC queue server
│   └── cmd_gui.py                    # Command GUI
│
├── 📁 helpers/                       # Helper modules (KEEP AS IS)
│   ├── HelperPHNX.py
│   ├── ProcessorPHNX.py
│   ├── QueueManagerPHNX.py
│   ├── ConsoleUI.py
│   ├── UtilitiesPHNX.py
│   ├── TimeBasedHandlePHNX.py
│   ├── TimeBasedRunPHNX.py
│   ├── PersonalManagerPHNX.py
│   └── OllamaHelperPHNX.py
│
├── 📁 bgprogs/                       # Background programs (KEEP AS IS)
│   └── BgVoiceProcessorPHNX.pyw
│
├── 📁 docs/                          # All documentation
│   ├── README.md                     # Main readme
│   ├── guides/                       # User guides
│   │   ├── CONTINUOUS_LISTENING_GUIDE.md
│   │   ├── HOW_TO_TEST_CONTINUOUS_LISTENING.md
│   │   ├── QUICK_TEST_GUIDE.md
│   │   ├── UV_GUIDE.md
│   │   ├── UV_README.md
│   │   └── PERSONAL_MANAGER_GUIDE.md
│   ├── analysis/                     # Analysis & architecture
│   │   ├── PHOENIX_COMPREHENSIVE_ANALYSIS.md
│   │   ├── SENIOR_AI_MENTOR_GUIDE.md
│   │   ├── PERFORMANCE_OPTIMIZATION.md
│   │   └── WAKE_WORD_FLOW.md
│   ├── fixes/                        # Fix documentation
│   │   ├── FIX_SELF_VOICE_AND_TIMESTAMPS.md
│   │   ├── FIX_APPLIED_NOW.md
│   │   ├── FIX_ACCESS_DENIED.md
│   │   ├── FINAL_FIX_SHARED_MEMORY.md
│   │   ├── SELF_VOICE_SUPPRESSION_ENHANCED.md
│   │   ├── FAN_NOISE_FIX.md
│   │   ├── QUEUE_SERVER_FIX.md
│   │   └── WHY_NOT_RESPONDING.md
│   ├── history/                      # Change history
│   │   ├── CHANGES_SUMMARY.md
│   │   ├── IMPLEMENTATION_SUMMARY.md
│   │   ├── BEFORE_AFTER_COMPARISON.md
│   │   ├── RECOVERY_AND_SETUP_COMPLETE.md
│   │   └── DEBUG_CONTINUOUS_LISTENING.md
│   └── troubleshooting/              # Troubleshooting guides
│       └── TROUBLESHOOTING.md
│
├── 📁 tests/                         # Test files (KEEP, organize better)
│   ├── unit/                         # Unit tests
│   │   ├── test_mic.py
│   │   └── test_final_verification.py
│   ├── integration/                  # Integration tests
│   │   ├── test_continuous_listen.py
│   │   ├── test_voice_command.py
│   │   ├── test_speak.py
│   │   └── test_whisper_quick.py
│   ├── experimental/                 # Trial/experimental tests
│   │   ├── test_bg_startup.py
│   │   ├── test_bg_time.py
│   │   ├── test_personal_manager.py
│   │   ├── test_fixes.py
│   │   ├── test_speaking_flag.py
│   │   ├── test_offline_tts.py
│   │   ├── test_coqui_tts.py
│   │   ├── test_piper_voice.py
│   │   ├── test_piper_voice_fixed.py
│   │   └── test_piper_working.py
│   ├── debug/                        # Debug utilities
│   │   └── debug_speaking_flag.py
│   ├── listen.py                     # Quick listen test
│   ├── run_listen.bat
│   └── README.md
│
├── 📁 scripts/                       # Automation scripts
│   ├── setup/                        # Setup scripts
│   │   ├── uv-setup.ps1
│   │   ├── uv-sync.bat
│   │   ├── uv-sync.ps1
│   │   └── rename_consoleui.bat
│   ├── utilities/                    # Utility scripts
│   │   ├── SortPythonProgram.py
│   │   ├── apply_queue_fix.py
│   │   ├── download_piper_voices.py
│   │   └── download_piper_voices_fixed.py
│   ├── startup/                      # Startup scripts
│   │   ├── phoenix.bat               # (from scripts/)
│   │   └── on_boot_startup.bat       # (from batch/)
│   └── main.bat                      # (from batch/)
│
├── 📁 assets/                        # Static assets (KEEP AS IS)
│   └── (images, sounds, etc.)
│
├── 📁 data/                          # Data files (KEEP AS IS)
│   └── (user data, configs, etc.)
│
├── 📁 gui/                           # GUI components (KEEP AS IS)
│   └── (GUI-related files)
│
├── 📁 trials/                        # Trial/experimental code (KEEP AS IS)
│   └── (old experiments)
│
├── 📁 NetMonitor/                    # Network monitoring (KEEP AS IS)
│   └── network_monitor.py
│
├── 📁 MDs/                           # OLD MD folder (TO BE DELETED/MERGED)
│   └── (merge into docs/)
│
├── 📁 batch/                         # OLD batch folder (TO BE DELETED/MERGED)
│   └── (merge into scripts/startup/)
│
├── 📁 logs/                          # Log files (NEW)
│   ├── phoenix_launcher.log
│   ├── phoenix_listener.log
│   ├── phoenix_queue.log
│   ├── bg_voice_processor.log
│   └── debug.log
│
├── 📁 temp/                          # Temporary files (NEW)
│   ├── coqui_test.wav
│   ├── test_piper_output.wav
│   └── (other temp files)
│
├── 📁 models/                        # AI Models (NEW)
│   └── piper_voices/                 # Voice models
│       ├── en_US-lessac-medium.onnx
│       ├── en_US-amy-medium.onnx
│       └── (other voice files)
│
├── 📁 .venv/                         # Virtual environment (KEEP AS IS)
├── 📁 .git/                          # Git folder (KEEP AS IS)
├── 📁 .github/                       # GitHub configs (KEEP AS IS)
│   └── ERROR_HANDLING_FIX.md         # (move to docs/fixes/)
│
├── 📄 .gitignore                     # Git ignore file
├── 📄 .python-version                # Python version
├── 📄 LICENSE                        # License file
├── 📄 Requirements.txt               # Dependencies
├── 📄 pyproject.toml                 # Project config
├── 📄 uv.lock                        # UV lock file
├── 📄 load.py                        # Load script (move to scripts/utilities/)
└── 📄 README.md                      # Main readme (link to docs/README.md)
```

---

## 📋 File Categorization

### 1. **Core Application Files** → `core/`
```
launch_phoenix.py          # Main launcher
MainPHNX.py               # Original main
ListenerPHNX.py           # Audio listener
queue_server.py           # Queue server
cmd_gui.py                # Command GUI
```

### 2. **Documentation Files** → `docs/`

**Guides** → `docs/guides/`
```
CONTINUOUS_LISTENING_GUIDE.md
HOW_TO_TEST_CONTINUOUS_LISTENING.md
QUICK_TEST_GUIDE.md
UV_GUIDE.md
UV_README.md
PERSONAL_MANAGER_GUIDE.md
```

**Analysis** → `docs/analysis/`
```
PHOENIX_COMPREHENSIVE_ANALYSIS.md
SENIOR_AI_MENTOR_GUIDE.md
PERFORMANCE_OPTIMIZATION.md
WAKE_WORD_FLOW.md
```

**Fixes** → `docs/fixes/`
```
FIX_SELF_VOICE_AND_TIMESTAMPS.md
FIX_APPLIED_NOW.md
FIX_ACCESS_DENIED.md
FINAL_FIX_SHARED_MEMORY.md
SELF_VOICE_SUPPRESSION_ENHANCED.md
FAN_NOISE_FIX.md
QUEUE_SERVER_FIX.md
WHY_NOT_RESPONDING.md
```

**History** → `docs/history/`
```
CHANGES_SUMMARY.md
IMPLEMENTATION_SUMMARY.md
BEFORE_AFTER_COMPARISON.md
RECOVERY_AND_SETUP_COMPLETE.md
DEBUG_CONTINUOUS_LISTENING.md
```

### 3. **Test Files** → `tests/`

**Unit Tests** → `tests/unit/`
```
test_mic.py
test_final_verification.py
```

**Integration Tests** → `tests/integration/`
```
test_continuous_listen.py
test_voice_command.py
test_speak.py
test_whisper_quick.py
```

**Experimental Tests** → `tests/experimental/`
```
test_bg_startup.py
test_bg_time.py
test_personal_manager.py
test_fixes.py
test_speaking_flag.py
test_offline_tts.py
test_coqui_tts.py
test_piper_voice.py
test_piper_voice_fixed.py
test_piper_working.py
```

### 4. **Scripts** → `scripts/`

**Setup** → `scripts/setup/`
```
uv-setup.ps1
uv-sync.bat
uv-sync.ps1
rename_consoleui.bat
```

**Utilities** → `scripts/utilities/`
```
SortPythonProgram.py
apply_queue_fix.py
download_piper_voices.py
download_piper_voices_fixed.py
load.py  (from root)
```

**Startup** → `scripts/startup/`
```
phoenix.bat  (from scripts/)
on_boot_startup.bat  (from batch/)
main.bat  (from batch/)
```

### 5. **Log Files** → `logs/`
```
phoenix_launcher.log
phoenix_listener.log
phoenix_queue.log
bg_voice_processor.log
debug.log
```

### 6. **Temporary Files** → `temp/`
```
coqui_test.wav
test_piper_output.wav
(any other temporary test outputs)
```

### 7. **Models** → `models/`
```
piper_voices/
├── en_US-lessac-medium.onnx
├── en_US-lessac-medium.onnx.json
├── en_US-amy-medium.onnx
└── (other voice models)
```

### 8. **Keep As-Is**
```
helpers/          # Helper modules
bgprogs/          # Background programs
assets/           # Static assets
data/             # Data files
gui/              # GUI components
trials/           # Old experiments
NetMonitor/       # Network monitor
.venv/            # Virtual environment
.git/             # Git
.github/          # GitHub configs
```

### 9. **To Delete/Merge**
```
MDs/              # Merge into docs/, then delete
batch/            # Merge into scripts/startup/, then delete
5.9.0/            # Unknown - check before deleting
```

---

## 🚀 Migration Script

I'll create a Python script to automate this reorganization!

**Next steps:**
1. Review this structure - any changes needed?
2. I'll create `reorganize_phoenix.py` script
3. Run the script to reorganize everything
4. Update imports in code files
5. Test that Phoenix still works

**Want me to proceed with creating the reorganization script?**
