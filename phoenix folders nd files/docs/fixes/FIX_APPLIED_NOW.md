# URGENT FIX: Self-Voice Suppression (Enhanced)

## What Changed

I've implemented a **multi-layered defense** against self-listening:

### 🛡️ Layer 1: Set Flag EARLY
- `.speaking` file now created **BEFORE** any audio generation
- File created at the very start of `speak()` method

### 🛡️ Layer 2: Clear Queue Immediately  
- Queue cleared when Phoenix starts speaking
- Removes any pending audio chunks

### 🛡️ Layer 3: Active Queue Draining
- While speaking, processor **continuously drains** the queue
- Removes up to 20 chunks per check
- Prevents audio accumulation

### 🛡️ Layer 4: Longer Buffer
- Increased from 0.5s to **2.5 seconds** total buffer
- 2.0s after speech ends
- Additional 0.5s for microphone audio to clear

## Files Modified

1. **helpers/HelperPHNX.py** - `speak()` method
   - Set speaking flag FIRST
   - Clear queue immediately
   - Increased buffer from 0.5s → 2.5s total

2. **bgprogs/voice_command_processor.py** - `process_audio_chunk()`
   - Added active queue draining while speaking
   - Added debug logging to track chunk skipping
   - Enhanced `is_speaking()` with better logging

## How to Test

```bash
# 1. Launch Phoenix
python launch_phoenix.py

# 2. Test self-voice (say this):
"Phoenix, tell me a joke"

# 3. Expected output:
👤 You [HH:MM:SS]: "Tell me a joke Phoenix"
🔊 Phoenix [HH:MM:SS]: Why did the chicken cross the road?
🎧 Listening...

# Should NOT see Phoenix's joke repeated as "You said"!
```

## Debug Tools

### Monitor .speaking file in real-time:
```bash
# In a separate terminal
python debug_speaking_flag.py
```

This will show when the speaking flag is set/cleared and for how long.

### Check processor logs:
```bash
# After testing, check if chunks were skipped:
findstr /C:"is_speaking" bg_voice_processor.log
findstr /C:"Skipping chunk" bg_voice_processor.log
findstr /C:"Cleared" bg_voice_processor.log
```

You should see:
```
is_speaking() = True (Phoenix is speaking, audio will be skipped)
Skipping chunk - Phoenix is speaking
Cleared 5 chunks from queue during speaking
```

## If It STILL Fails

### Quick Fix: Increase Buffer Time

Edit `helpers/HelperPHNX.py`, in the `speak()` method's finally block:

```python
# Change from:
sleep(2.0)
# To:
sleep(4.0)  # or even 5.0

# And change:
sleep(0.5)
# To:
sleep(1.0)
```

### Hardware Solution (Most Reliable)
**Use headphones!** This eliminates the problem entirely since Phoenix's audio doesn't reach the microphone.

### Why This Should Work Now

**Before**: One defense layer (flag only) - Race condition allowed audio through
**Now**: Four defense layers - Even if one fails, others catch it

**The race condition timeline**:
```
OLD:
T+0:    speak() starts
T+5ms:  Audio → Speakers → Microphone
T+8ms:  Chunk queued ❌
T+10ms: .speaking file created (TOO LATE!)

NEW:
T+0:    .speaking file created ✅
T+1ms:  Queue cleared ✅
T+5ms:  Audio → Speakers → Microphone
T+8ms:  Chunk queued
T+9ms:  Processor sees is_speaking() = True → Skips chunk ✅
T+10ms: Processor drains queue continuously ✅
T+2500ms: .speaking removed (long buffer) ✅
```

## Testing Checklist

- [ ] Run `python launch_phoenix.py`
- [ ] Say: "Phoenix, tell me a joke"
- [ ] Phoenix responds with a joke
- [ ] Verify Phoenix's joke does NOT appear as "👤 You said..."
- [ ] Check `bg_voice_processor.log` for "Skipping chunk" messages
- [ ] Try multiple interactions to ensure consistency

## Performance Note

- **Trade-off**: ~2.5 seconds of "dead time" after Phoenix speaks before accepting new input
- **Benefit**: Reliable self-voice suppression
- **If needed**: Can be reduced to 1.5-2.0s after confirming it works

Good luck! This should fix the self-listening issue. Let me know if Phoenix still hears itself and we'll tune the buffer time. 🎯
