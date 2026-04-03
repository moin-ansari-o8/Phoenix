# Phoenix Reorganization - Quick Reference

## 📁 New Folder Structure Summary

```
Phoenix/
├── core/              # Main application files
├── helpers/           # Helper modules (unchanged)
├── bgprogs/           # Background processors (unchanged)
├── docs/              # ALL documentation organized
│   ├── guides/
│   ├── analysis/
│   ├── fixes/
│   ├── history/
│   └── troubleshooting/
├── tests/             # ALL tests organized
│   ├── unit/
│   ├── integration/
│   ├── experimental/
│   └── debug/
├── scripts/           # ALL scripts organized
│   ├── setup/
│   ├── utilities/
│   └── startup/
├── logs/              # Log files
├── temp/              # Temporary files
├── models/            # AI models (Piper voices)
└── [other folders unchanged]
```

## 🚀 How to Reorganize

**Option 1: Automated (Recommended)**
```bash
python reorganize_phoenix.py
```
- Automatically moves all files
- Creates new folder structure
- Shows progress and summary
- Safe: Won't overwrite existing files

**Option 2: Manual**
- Follow REORGANIZATION_PLAN.md
- Move files according to categories
- Update imports manually

## ⚠️ Before Running

1. **Backup your work** (optional but recommended)
   ```bash
   # Copy Phoenix folder to backup location
   ```

2. **Close Phoenix** if running

3. **Review the plan**
   - Open `REORGANIZATION_PLAN.md`
   - Check file categorization
   - Suggest changes if needed

## ✅ After Reorganization

1. **Update launch command:**
   ```bash
   # Old:
   python launch_phoenix.py
   
   # New:
   python core/launch_phoenix.py
   ```

2. **Check imports:**
   - Most imports should work (helpers/, bgprogs/ unchanged)
   - Only core files moved, imports shouldn't break

3. **Update .gitignore:**
   ```
   logs/
   temp/
   models/piper_voices/
   ```

4. **Test Phoenix:**
   ```bash
   python core/launch_phoenix.py
   ```

## 📊 What Gets Moved

| Category | From → To |
|----------|-----------|
| **Core Files** | Root → `core/` |
| **Documentation** | Root → `docs/[category]/` |
| **Test Files** | Root/tests → `tests/[type]/` |
| **Scripts** | Root/batch → `scripts/[type]/` |
| **Logs** | Root → `logs/` |
| **Temp Files** | Root → `temp/` |
| **Voice Models** | `piper_voices/` → `models/piper_voices/` |

## 🔧 Troubleshooting

**If imports break after reorganization:**

1. **Update import paths in moved files**
   ```python
   # If file moved to core/, update:
   from helpers.HelperPHNX import SpeechEngine
   # to:
   from ..helpers.HelperPHNX import SpeechEngine
   ```

2. **Or add to Python path**
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent))
   ```

**If reorganization script fails:**
- Check error messages
- Manually move failed files
- Report errors for script update

## 📝 Files That Stay in Root

- `.gitignore`
- `.python-version`
- `LICENSE`
- `README.md`
- `Requirements.txt`
- `pyproject.toml`
- `uv.lock`
- `.venv/`
- `.git/`
- `assets/`
- `data/`
- `gui/`
- `trials/`
- `NetMonitor/`

## 🎯 Benefits After Reorganization

✅ **Clear structure** - Easy to find files  
✅ **Better navigation** - Logical grouping  
✅ **Easier maintenance** - Separate concerns  
✅ **Professional** - Industry-standard layout  
✅ **Scalable** - Room to grow  

---

**Ready to reorganize?** Run: `python reorganize_phoenix.py`
