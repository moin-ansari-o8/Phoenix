# Quick UV Commands for Phoenix

## 🚀 First Time Setup

### 1. Install UV (if not installed):
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Run setup (choose one method):

**Method A - PowerShell (Recommended):**
```powershell
.\uv-sync.ps1
# Choose option 1 for fresh install
```

**Method B - Batch file:**
```cmd
uv-sync.bat
```

**Method C - Manual:**
```powershell
# If .venv is active, deactivate first
deactivate

# Fresh install
Remove-Item .venv -Recurse -Force
uv sync

# Activate and run
.\.venv\Scripts\Activate.ps1
python MainPHNX.py
```

---

## 📦 Daily Usage

```powershell
# Update dependencies (if pyproject.toml changed)
uv sync

# Add a new package
uv add package-name

# Add dev dependency
uv add --group dev pytest

# Remove a package
uv remove package-name

# Update all packages
uv lock --upgrade

# Run without activating venv
uv run python MainPHNX.py

# Install from requirements.txt (if needed)
uv pip install -r Requirements.txt
```

---

## 💡 Why UV is Better than pip

✅ **10-100x faster** installation  
✅ **Proper dependency resolution** (no more conflicts!)  
✅ **Reproducible builds** with lock files  
✅ **Virtual environment** management built-in  
✅ **Cross-platform** - works everywhere  
✅ **No pip hell** - actually works!  

**Example speed:**
- pip: 2-5 minutes for all packages
- UV: 10-30 seconds for all packages

---

## 🛠️ Troubleshooting

### "Access is denied" when running uv sync
**Solution:**
1. Close VS Code terminal
2. Deactivate venv: `deactivate`
3. Close all Python processes
4. Run: `.\uv-sync.ps1` and choose option 1

### "uv: command not found"
**Solution:**
```powershell
# Restart PowerShell after installing UV
# Or check if UV is in PATH:
$env:PATH -split ';' | Select-String uv
```

### "Package not found"
**Solution:**
```powershell
# Some packages might have different names
# Check available versions:
uv pip search package-name
```

### "Permission denied"
**Solution:**
```powershell
# Run PowerShell as Administrator, then:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Dependencies not updating
**Solution:**
```powershell
# Force update lock file
uv lock --upgrade

# Then sync
uv sync
```

---

## 📁 Files Created

- **pyproject.toml** - Modern Python project config (UV uses this)
- **.python-version** - Specifies Python 3.14.0  
- **uv.lock** - Dependency lock file (auto-generated)
- **uv-sync.ps1** - Interactive setup script (PowerShell)
- **uv-sync.bat** - Quick setup script (Windows)
- **uv-setup.ps1** - Detailed setup with verification

---

## 🔄 Migration from pip

Your old `Requirements.txt` is kept for reference. UV uses `pyproject.toml`.

**If you have packages not in pyproject.toml:**
```powershell
# Install from requirements.txt
uv pip install -r Requirements.txt

# Or add them properly:
uv add package-name
```

**Converting requirements.txt to pyproject.toml:**
```powershell
# UV can read requirements.txt
uv pip compile Requirements.txt -o uv.lock
```

---

## ⚡ Quick Commands

```powershell
# One-liner: setup + activate + run
uv sync; .\.venv\Scripts\Activate.ps1; python MainPHNX.py

# Update everything
uv lock --upgrade && uv sync

# Check what's installed
uv pip list

# Check for outdated packages
uv pip list --outdated

# Create requirements.txt from current environment
uv pip freeze > Requirements-new.txt
```

---

## 🎯 Best Practices

1. **Always use `uv sync`** instead of `pip install -r requirements.txt`
2. **Add packages with `uv add`** not `pip install`
3. **Commit `uv.lock`** to git for reproducible builds
4. **Keep `pyproject.toml`** as source of truth
5. **Use `.python-version`** to specify Python version

---

## 📊 Project Structure

```
Phoenix/
├── pyproject.toml      # Dependencies (edit this)
├── uv.lock            # Lock file (auto-generated)
├── .python-version    # Python 3.14.0
├── uv-sync.ps1        # Setup script (run this)
├── uv-sync.bat        # Quick setup (alternative)
├── Requirements.txt   # Old format (kept for reference)
└── .venv/            # Virtual environment (auto-created)
```

---

## 🚀 Quick Start (TL;DR)

```powershell
# First time:
.\uv-sync.ps1  # Choose option 1

# Daily use:
.\.venv\Scripts\Activate.ps1
python MainPHNX.py

# Update packages:
uv sync
```

**That's it! No more pip install errors! 🎉**
