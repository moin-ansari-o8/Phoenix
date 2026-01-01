# SIMPLE FIX for "Access Denied" Error

## Problem
UV can't update .venv because files are locked by VS Code/Python

## Solution (Choose ONE):

### Option 1: Restart VS Code (EASIEST)
1. Close VS Code completely
2. Open VS Code again
3. Open terminal
4. Run: `uv sync`

### Option 2: Use pip instead (WORKS NOW)
```powershell
pip install -r Requirements.txt
```
(Slower but works without closing anything)

### Option 3: Don't update yet
Your existing venv works fine! Only update when you need new packages.

---

## Why This Happens
- VS Code locks Python files
- UV tries to replace them = Access Denied

## Prevention
Always close VS Code terminal before running `uv sync`

---

**TL;DR: Close VS Code → Reopen → `uv sync`**
