# Fix: Fan Noise Causing Infinite Loop

## Problem Identified

From your log:
```
[DEBUG] Silence START (buffered 121 chunks)
[DEBUG] Silence START (buffered 291 chunks)  ← Timer keeps resetting!
[DEBUG] Silence START (buffered 303 chunks)
... 800+ times!
```

**Root Cause:** Your fan noise causes VAD to flip-flop:
- Frame 1: Detects silence → Sets timer
- Frame 2: Fan noise detected as "speech" → Resets timer to None
- Frame 3: Silence again → Sets timer again
- Repeat forever, never reaching 0.8s threshold

## The Fix Applied

**Added "Confirmation Chunks" - Require 3 consecutive detections:**

### Before (Flaky):
```
1 chunk with speech → Speech detected!
1 chunk with silence → Silence detected!
(Flip-flops constantly with background noise)
```

### After (Robust):
```
3 consecutive chunks with speech → Speech CONFIRMED
3 consecutive chunks with silence → Silence CONFIRMED
(Ignores brief noise fluctuations)
```

### New Parameter:
```python
SPEECH_CONFIRMATION_CHUNKS = 3  # Must hear 3 chunks in a row
```

## How It Works Now

```
Fan noise pattern:
Chunk: S S N S S S S S N S S S ...
       ↑   ↑           ↑
     Noise spikes (ignored)

Detection:
Chunk: S S N S S S S S N S S S ...
Count: 1 2 0 1 2 3 ← CONFIRMED at 3!
                 ↑
            Speech starts here
```

The silence timer can ONLY be reset after 3 consecutive speech chunks, not just 1 random fan noise spike.

## Test It Now

Run MainPHNX again with your fan on:

```bash
python MainPHNX.py
```

You should see:
```
[DEBUG] Speech CONFIRMED (chunk X)  ← Not "START", but "CONFIRMED"
[DEBUG] Silence CONFIRMED (buffered Y chunks)  ← Only prints ONCE
[DEBUG] Silence threshold reached (0.8s), processing...
```

No more infinite "Silence START" messages!

## Adjusting Sensitivity

If it's still too sensitive or not sensitive enough:

In `helpers/HelperPHNX.py` around line 221:

```python
# More tolerant (good for noisy environments):
self.SPEECH_CONFIRMATION_CHUNKS = 5  # Need 5 consecutive chunks

# Less tolerant (good for quiet rooms):
self.SPEECH_CONFIRMATION_CHUNKS = 2  # Need only 2 consecutive chunks

# Current (balanced):
self.SPEECH_CONFIRMATION_CHUNKS = 3  # Default
```

The higher the number, the more it ignores brief noise spikes.

## Why This Works

**Physics of audio chunks:**
- Each chunk = ~64ms (1024 samples at 16kHz)
- 3 chunks = ~192ms (~0.2 seconds)
- Fan noise spikes are usually < 100ms
- Real speech lasts much longer

So requiring 3 consecutive chunks filters out brief noise while still catching real speech quickly!
