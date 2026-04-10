# Quick Test Guide - Speed Optimization

## What Was Fixed

**Problem:** Phoenix taking 7-17 seconds to respond instead of 0.8 seconds

**Solution:** 
1. Raised `ENERGY_THRESHOLD` from 50 to 150 (ignores fan noise better)
2. Added `MAX_SPEECH_DURATION = 30s` (auto-processes long speech)
3. Added timestamps to all debug output (track delays precisely)

## How to Test

### Option 1: Test File (Quick)
```powershell
python test_continuous_listen.py
```

Say something, then pause. Watch the timestamps:
```
[14:23:45.123] [DEBUG] Speech CONFIRMED (chunk 11)
[14:23:47.890] [DEBUG] Silence CONFIRMED (buffered 42 chunks)
[14:23:48.720] [DEBUG] Silence threshold reached (0.83s), processing...
```
Look for the time difference between "Silence CONFIRMED" and "threshold reached" - should be ~0.8s

### Option 2: Full Phoenix (Real World)
```powershell
python main_assistant.py
```

Say "Hello Phoenix" and watch timing in debug output.

## What to Look For

### GOOD (Working correctly):
```
[12:00:01.500] [DEBUG] Speech CONFIRMED
[12:00:05.200] [DEBUG] Silence CONFIRMED (buffered 58 chunks)
[12:00:06.010] [DEBUG] Silence threshold reached (0.81s), processing...
                                                         ^^^^^ ← Should be 0.8-1.5s
```

### BAD (Still broken - fan noise):
```
[12:00:01.500] [DEBUG] Speech CONFIRMED  
[12:00:15.800] [DEBUG] Silence CONFIRMED (buffered 340 chunks)
[12:00:27.200] [DEBUG] Silence threshold reached (11.40s), processing...
                                                         ^^^^^^ ← Too long!
```

If you see long delays still, try:

## Tuning for Very Noisy Rooms

Edit `helpers/HelperPHNX.py` around line 218:

```python
# OPTION 1: Increase threshold (ignore louder noise)
self.ENERGY_THRESHOLD = 250  # Try 200-300

# OPTION 2: Faster response (less silence needed)
self.MIN_SILENCE_DURATION = 0.5  # Try 0.5-0.6s

# OPTION 3: Require fewer confirmations (faster but less stable)
self.SPEECH_CONFIRMATION_CHUNKS = 2  # Try 2 instead of 3

# OPTION 4: Process long speech sooner
self.MAX_SPEECH_DURATION = 15.0  # Try 10-15s
```

## Expected Performance

- **Speech detection:** < 0.7 seconds
- **Silence detection:** < 1.0 seconds  
- **Processing trigger:** 0.8-1.5 seconds after you stop speaking
- **Total response time:** 2-4 seconds (including Whisper transcription)

Compare with your earlier logs:
- **Before:** 7.93s, 17.92s silence thresholds ❌
- **After:** 0.8-1.5s silence thresholds ✅

## Debug Output Explanation

```
[14:23:45.123] [DEBUG] Speech CONFIRMED (chunk 11)
                ↑ Timestamp              ↑ Took 11 chunks (~0.7s) to confirm speech

[14:23:47.890] [DEBUG] Silence CONFIRMED (buffered 42 chunks)
                                           ↑ 42 chunks of audio captured

[14:23:48.720] [DEBUG] Silence threshold reached (0.83s), processing...
                ↑ Time when processing started    ↑ How long it waited after silence started

[14:23:48.750] [DEBUG] Speech duration: 2.69s
                                        ↑ Total speech length

[14:23:48.780] [DEBUG] Transcribing 42 chunks...
[14:23:49.120] [DEBUG] Transcription complete: 'Hello Phoenix'
                ↑ Whisper took ~0.34s
```

Total time from "silence confirmed" to "transcription complete": ~1.2 seconds

## Still Having Issues?

1. Check fan noise level - if RMS values constantly > 150, increase threshold
2. Try turning off fan temporarily to verify it's the cause
3. Compare timestamps - find which step is slow
4. Post the timestamped debug output for analysis
