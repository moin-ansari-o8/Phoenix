# Performance Optimization - Continuous Listening

## Problem
Phoenix was taking 7-17 seconds to respond after user stopped speaking, instead of the expected 0.8s. The issue was caused by fan noise interfering with the silence detection algorithm.

## Root Cause
The confirmation chunks algorithm required **3 consecutive silence chunks** to confirm silence. With fan noise constantly triggering false speech detections, it took many seconds before getting 3 clean consecutive silence chunks.

Example from logs:
```
Silence CONFIRMED (buffered 338 chunks)  ← Fan kept resetting this for 17 seconds!
Silence threshold reached (17.92s)        ← Should be 0.8s
```

## Changes Made

### 1. Increased Energy Threshold (150 from 50)
**File:** `helpers/HelperPHNX.py` line ~218
```python
self.ENERGY_THRESHOLD = 150  # Raised to ignore fan noise
```
This makes the system less sensitive to background noise like fans.

### 2. Added Maximum Speech Duration (30 seconds)
**File:** `helpers/HelperPHNX.py` line ~222
```python
self.MAX_SPEECH_DURATION = 30.0  # Force processing after 30s
```
If you speak for more than 30 seconds continuously, it will auto-process instead of waiting for silence. This prevents infinite buffering.

### 3. Added Timestamps to All Debug Messages
All debug prints now show exact timing:
```
[14:23:45.123] [DEBUG] Speech CONFIRMED (chunk 11)
[14:23:52.456] [DEBUG] Silence CONFIRMED (buffered 120 chunks)
[14:23:53.280] [DEBUG] Silence threshold reached (0.82s), processing...
```

This lets you track exactly where delays occur.

### 4. Implemented Max Duration Auto-Processing
**File:** `helpers/HelperPHNX.py` line ~376-386
If speech duration exceeds 30 seconds, automatically process without waiting for silence:
```python
speech_duration_so_far = current_time - self.speech_start_time
if speech_duration_so_far >= self.MAX_SPEECH_DURATION:
    log_time(f"[DEBUG] Max speech duration ({self.MAX_SPEECH_DURATION}s) reached, processing...")
    # Process immediately
```

## Expected Behavior Now

1. **Normal operation:** Speak → pause 0.8s → processes immediately
2. **With fan noise:** Higher threshold ignores most fan noise
3. **Long speech:** Auto-processes after 30s without needing silence
4. **Timing visible:** Timestamps show exact delays in real-time

## Testing

Run with fan on:
```powershell
python main_assistant.py
```

Watch the timestamps to verify:
- Speech confirmed quickly (within 1 second)
- Silence confirmed without long delays
- Processing happens within 0.8-1.5 seconds after you stop speaking

## Tuning Parameters

If still having issues, adjust these in `helpers/HelperPHNX.py` (~line 218):

```python
# Make LESS sensitive to noise (higher = louder needed)
self.ENERGY_THRESHOLD = 200  # Try 200-300 for very noisy rooms

# Process faster (lower = quicker response)
self.MIN_SILENCE_DURATION = 0.5  # Try 0.5s for faster response

# Fewer confirmations needed (faster but more false positives)
self.SPEECH_CONFIRMATION_CHUNKS = 2  # Try 2 for faster (but less stable)

# Auto-process sooner
self.MAX_SPEECH_DURATION = 20.0  # Try 15-20s for shorter speeches
```

## Comparison with WriteForMe

WriteForMe processes chunks every 15 seconds regardless of silence, which is why it feels faster but may cut off mid-speech. Phoenix waits for complete silence, which is more accurate but can be delayed by noise.

The current approach is a hybrid: wait for silence (like Phoenix) but timeout after 30s (like WriteForMe).
