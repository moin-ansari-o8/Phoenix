# Phoenix Project - Copilot Instructions

> **Note:** Full detailed instructions in `AGENT.md`. This file provides quick reference.

## 🎯 Core Principle
**Keep files organized! Never scatter files in root directory.**

---

## 📁 Quick Folder Reference

| File Type | Location | Example |
|-----------|----------|---------|
| **Documentation** | `docs/[category]/` | `docs/guides/HOWTO.md` |
| **Tests** | `tests/[type]/` | `tests/experimental/test_feature.py` |
| **Scripts** | `scripts/[purpose]/` | `scripts/utilities/helper.py` |
| **Logs** | `logs/` | `logs/debug.log` |
| **Temp files** | `temp/` | `temp/output.wav` |
| **Models** | `models/` | `models/piper_voices/` |
| **Helpers** | `helpers/` | `helpers/HelperPHNX.py` |
| **Core app** | `core/` | `core/launch_phoenix.py` |
| **Background** | `bgprogs/` | `bgprogs/BgProcessor.pyw` |

---

## 🚨 Critical Rules

1. **NO files at root** (except config: .gitignore, pyproject.toml, Requirements.txt, README.md, LICENSE)

2. **Documentation:**
   - User guides → `docs/guides/`
   - Architecture → `docs/analysis/`
   - Bug fixes → `docs/fixes/`
   - History → `docs/history/`
   - Troubleshooting → `docs/troubleshooting/`

3. **Tests:**
   - Unit → `tests/unit/`
   - Integration → `tests/integration/`
   - Experimental → `tests/experimental/`
   - Debug tools → `tests/debug/`

4. **Scripts:**
   - Setup → `scripts/setup/`
   - Utilities → `scripts/utilities/`
   - Startup → `scripts/startup/`

5. **Always update imports** when moving files

---

## 🤖 For AI: Quick Decision Tree

```
Creating new file?
├─ Is it documentation (.md)?
│  └─ Yes → docs/[guides|analysis|fixes|history|troubleshooting]/
├─ Is it a test (.py with "test_" prefix)?
│  └─ Yes → tests/[unit|integration|experimental|debug]/
├─ Is it a script (.bat, .ps1)?
│  └─ Yes → scripts/[setup|utilities|startup]/
├─ Is it a log file (.log)?
│  └─ Yes → logs/
├─ Is it temporary output?
│  └─ Yes → temp/
└─ Is it core functionality?
   ├─ Reusable helper? → helpers/
   ├─ Main entry point? → core/
   └─ Background process? → bgprogs/
```

---

## ✅ Quick Examples

```bash
# ✅ CORRECT
docs/guides/HOW_TO_USE_WHISPER.md
tests/experimental/test_new_feature.py
scripts/utilities/download_models.py
logs/debug.log
temp/test_output.wav

# ❌ WRONG
HOW_TO_USE_WHISPER.md              # Missing docs/guides/
test_new_feature.py                # Missing tests/experimental/
download_models.py                 # Missing scripts/utilities/
debug.log                          # Missing logs/
test_output.wav                    # Missing temp/
```

---

## 📖 Full Documentation

See `AGENT.md` for comprehensive guidelines including:
- Detailed folder descriptions
- Code examples for each scenario
- Import update instructions
- Anti-patterns to avoid
- Pre-commit checklist

**Keep Phoenix organized! 🚀**
