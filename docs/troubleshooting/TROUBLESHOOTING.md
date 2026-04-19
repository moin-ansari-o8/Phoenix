# Common Issues & Troubleshooting - Phoenix

Quick reference for resolving Phoenix Desktop Assistant issues.

---

## 🔴 COM/RPC Errors

### Error Message
```
_ctypes.COMError: (-2147023174, 'The RPC server is unavailable.')
```

### Solution
✅ **Already handled** - Program now continues with warnings instead of crashing.

### If Still Occurring
1. Restart Windows Explorer:
   ```powershell
   taskkill /F /IM explorer.exe
   start explorer.exe
   ```

2. Check Virtual Desktop service:
   ```powershell
   Get-Service -Name "Virtual Desktop*"
   ```

3. Disable virtual desktop features (if not needed):
   - Comment out `get_cur_desk()` calls
   - Use basic window management instead

---

## 🔴 Background Process Not Running

### Symptoms
- Alarms don't trigger
- Time announcements missing
- Battery warnings absent

### Solution
1. Check if processes are running:
   ```powershell
   Get-Process pythonw*
   ```

2. Manually start background processes:
   ```powershell
   cd C:\Path\To\Phoenix
   pythonw bgprogs\battery_monitor.pyw
   pythonw bgprogs\time_monitor.pyw
   ```

3. Check for errors in console output

---

## 🔴 Voice Recognition Not Working

### Symptoms
- Phoenix doesn't respond to voice
- "Listening..." but no response

### Solutions
1. **Check microphone permissions:**
   - Settings → Privacy → Microphone
   - Ensure Python has access

2. **Test microphone:**
   ```python
   import speech_recognition as sr
   r = sr.Recognizer()
   with sr.Microphone() as source:
       print("Say something...")
       audio = r.listen(source)
       print(r.recognize_google(audio))
   ```

3. **Adjust energy threshold:**
   - Edit `helpers/HelperPHNX.py`
   - Increase `recognizer.energy_threshold`

---

## 🔴 Import Errors

### Error Message
```
ModuleNotFoundError: No module named 'pyvda'
```

### Solution
```powershell
cd W:\workplace-1\DeskAssistants\Phoenix
.venv\Scripts\activate
pip install -r Requirements.txt
```

### If specific module fails
```powershell
pip install pyvda --upgrade
pip install pywin32 --upgrade
pip install pyaudio --upgrade
```

---

## 🔴 Window Management Fails

### Symptoms
- Can't maximize/minimize windows
- Desktop switching doesn't work
- Window moving fails

### Solutions
1. **Run as Administrator** (required for some operations)

2. **Check pygetwindow:**
   ```python
   import pygetwindow as gw
   print(gw.getAllTitles())
   ```

3. **Use alternative methods:**
   - Win32 API directly
   - PowerShell commands
   - AutoHotkey integration

---

## 🔴 Alarm/Timer Not Triggering

### Symptoms
- Alarm set but doesn't sound
- Timer completes silently

### Solutions
1. **Check background process:**
   ```powershell
   Get-Process pythonw | Where-Object {$_.Path -like "*Phoenix*"}
   ```

2. **Verify JSON files:**
   ```powershell
   cd W:\workplace-1\DeskAssistants\Phoenix\data
   Get-Content TimeData.json
   ```

3. **Check speaker volume/mute**

4. **Restart background time process:**
   ```powershell
   taskkill /F /IM pythonw.exe
   pythonw bgprogs\time_monitor.pyw
   ```

---

## 🔴 High CPU/Memory Usage

### Causes
- GUI objects leaking
- Multiple instances running
- Infinite loops in error handling

### Solutions
1. **Kill duplicate processes:**
   ```powershell
   Get-Process python* | Where-Object {$_.Path -like "*Phoenix*"}
   taskkill /F /IM pythonw.exe
   ```

2. **Reduce polling frequency:**
   - Edit `time_monitor.pyw`
   - Increase `time.sleep(1)` to `time.sleep(5)`

3. **Disable unused features:**
   - Comment out network monitor
   - Disable GUI if using voice only

---

## 🔴 Tkinter GUI Issues

### Error Message
```
_tkinter.TclError: can't invoke "wm" command
```

### Solution
This happens when GUI is created but not properly managed.

**In time_monitor.pyw** (background process):
- GUI is created but never used
- This is by design (needed for dependencies)
- Ignore Tkinter warnings in background processes

**If GUI crashes:**
```python
# Wrap GUI operations
try:
    root = tk.Tk()
    root.withdraw()  # Hide window
except Exception as e:
    print(f"GUI error: {e}")
    # Continue without GUI
```

---

## 🟡 Performance Optimization

### Issue: Slow Response Time

1. **Reduce wake word sensitivity:**
   ```python
   # In HelperPHNX.py
   recognizer.pause_threshold = 0.5  # Decrease
   ```

2. **Use faster speech engine:**
   ```python
   # Switch from edge-tts to pyttsx3
   import pyttsx3
   engine = pyttsx3.init()
   engine.setProperty('rate', 200)
   ```

3. **Cache API responses:**
   - Weather data
   - Search results
   - Model predictions

---

## 🟢 Debugging Tips

### Enable Debug Mode
```python
# Add to top of main_assistant.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Track Function Calls
```python
import traceback

def debug_wrapper(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"ERROR in {func.__name__}: {e}")
            traceback.print_exc()
    return wrapper
```

### Monitor Resources
```powershell
# PowerShell command
while ($true) {
    Get-Process python* | Select Name, CPU, WS | Format-Table
    Start-Sleep -Seconds 2
}
```

---

## 📞 Getting Help

1. **Check logs:**
   - `W:\workplace-1\DeskAssistants\Phoenix\debug.log`
   - Windows Event Viewer

2. **Test individual components:**
   - Run `test_speak.py`
   - Test voice recognition separately
   - Verify utilities one by one

3. **Create minimal test case:**
   ```python
   # test_minimal.py
   from Utils.limbs.action_utilities import Utility
   # Test specific failing function
   ```

---

## ✅ Health Check Script

```python
# health_check.py
import sys
import subprocess

def check_processes():
    result = subprocess.run(['tasklist'], capture_output=True, text=True)
    return 'pythonw.exe' in result.stdout

def check_imports():
    try:
        import pyvda
        import pyaudio
        import speech_recognition
        return True
    except ImportError as e:
        print(f"Missing: {e}")
        return False

def main():
    print("Phoenix Health Check")
    print("=" * 50)
    print(f"Background processes: {'✅' if check_processes() else '❌'}")
    print(f"Dependencies: {'✅' if check_imports() else '❌'}")

if __name__ == "__main__":
    main()
```

---

**Last Updated:** January 22, 2026  
**Phoenix Version:** Latest with error handling improvements
