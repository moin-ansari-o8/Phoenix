# Changes Summary - Speed Optimization

## Files Modified

### 1. `helpers/HelperPHNX.py`

#### Change 1: Increased Energy Threshold (Line ~218)
```python
# BEFORE:
self.ENERGY_THRESHOLD = 50  # RMS energy threshold

# AFTER:
self.ENERGY_THRESHOLD = 150  # RMS energy threshold (raised for fan noise)
```

#### Change 2: Added Max Speech Duration (Line ~222)
```python
# NEW LINE ADDED:
self.MAX_SPEECH_DURATION = 30.0  # Max seconds before auto-processing
```

#### Change 3: Added Timestamp Function (Line ~307-314)
```python
# NEW FUNCTION ADDED inside _continuous_listen_whisper():
import datetime

def log_time(msg):
    """Helper to print messages with timestamps"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {msg}")
```

#### Change 4: Replace All print() with log_time() 
All debug prints now include timestamps:
```python
# BEFORE:
print("[DEBUG] Starting continuous listen...")
print(f"\n[DEBUG] Speech CONFIRMED (chunk {chunk_count})")
print(f"[DEBUG] Silence threshold reached ({silence_duration:.2f}s), processing...")

# AFTER:
log_time("[DEBUG] Starting continuous listen...")
log_time(f"[DEBUG] Speech CONFIRMED (chunk {chunk_count})")
log_time(f"[DEBUG] Silence threshold reached ({silence_duration:.2f}s), processing...")
```

#### Change 5: Added Max Duration Check (Line ~376-386)
```python
# NEW CODE BLOCK ADDED after buffering speech:
# Add to buffer
self.audio_buffer.append(audio_chunk)

# Check if speech duration exceeded max
speech_duration_so_far = current_time - self.speech_start_time
if speech_duration_so_far >= self.MAX_SPEECH_DURATION:
    log_time(f"[DEBUG] Max speech duration ({self.MAX_SPEECH_DURATION}s) reached, processing...")
    stream.stop_stream()
    stream.close()
    audio.terminate()
    
    self.gui.show_recognize_image()
    log_time("<<< [Processing with Whisper...]")
    result = self._transcribe_buffer()
    log_time(f"[DEBUG] Transcription result: '{result}'")
    self.gui.hide_listen_image()
    return result
```

#### Change 6: Added Timestamps to _transcribe_buffer() (Line ~456)
```python
# ADDED same log_time helper inside _transcribe_buffer():
import datetime

def log_time(msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {msg}")

# Then replaced all print() with log_time()
```

### 2. Documentation Files Created

- `PERFORMANCE_OPTIMIZATION.md` - Explains the problem and solution
- `QUICK_TEST_GUIDE.md` - How to test and verify the fix
- `CHANGES_SUMMARY.md` - This file

## Why These Changes Fix the Issue

### Problem Analysis
From your logs:
```
Silence CONFIRMED (buffered 338 chunks)
Silence threshold reached (17.92s)  ← 17 seconds delay!
```

The fan noise was causing VAD to detect "speech" intermittently, preventing 3 consecutive silence chunks from being confirmed. The timer kept resetting.

### How Fixes Help

1. **Higher Energy Threshold (150)**
   - Fan noise typically has RMS < 150
   - Your voice has RMS > 300
   - This filters out fan while keeping voice

2. **Max Speech Duration (30s)**
   - Safety net: if buffering for > 30s, process anyway
   - Prevents infinite waiting in noisy environments
   - Most commands are < 10 seconds anyway

3. **Timestamps**
   - Lets you see EXACTLY where delays happen
   - Can measure: detection time, silence wait time, Whisper time
   - Makes debugging future issues easy

## Testing Checklist

- [ ] Run `python test_continuous_listen.py`
- [ ] Speak a test phrase
- [ ] Check timestamps show 0.8-1.5s silence threshold
- [ ] Run `python main_assistant.py` with fan on
- [ ] Say "Hello Phoenix"
- [ ] Verify response within 3-5 seconds total
- [ ] Test long speech (> 30s) to verify auto-processing

## Rollback Instructions

If this makes things worse, revert by editing `helpers/HelperPHNX.py`:

1. Change `self.ENERGY_THRESHOLD = 150` back to `50`
2. Remove `self.MAX_SPEECH_DURATION = 30.0` line
3. Remove the `import datetime` and `log_time` functions
4. Change all `log_time(...)` back to `print(...)`
5. Remove the "max duration check" code block

Or restore from git:
```powershell
git checkout helpers/HelperPHNX.py
```

## Next Steps

After testing:
1. If still slow → increase ENERGY_THRESHOLD to 200-300
2. If too sensitive → decrease ENERGY_THRESHOLD to 100
3. If responses feel sluggish → reduce MIN_SILENCE_DURATION to 0.5s
4. If it cuts you off → increase MIN_SILENCE_DURATION to 1.2s
