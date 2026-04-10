## ⚡ UV Setup - Fast Python Packages

### 🚀 Quick Start

**First time:**
```powershell
deactivate          # If venv is active
uv sync            # Install everything (10-30 seconds!)
.\.venv\Scripts\Activate.ps1
python main_assistant.py
```

**That's it!**

### 📦 Common Commands

```powershell
uv sync              # Update dependencies
uv add requests      # Add package
uv remove requests   # Remove package
```

### 🆘 If Error "Access Denied"

1. **Close this terminal**
2. **Open new terminal**
3. **Run:** `uv sync`

### Why UV?

- pip: 2-5 minutes ❌
- UV: 10-30 seconds ✅

**10-100x faster than pip!**
