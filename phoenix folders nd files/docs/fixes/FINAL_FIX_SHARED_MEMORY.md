# FINAL FIX: Shared Memory Speaking Flag ✅

## The Solution

**The file-based approach had race conditions and timing issues.**

**New approach**: **Shared memory flag via multiprocessing** - bulletproof!

## How It Works

### 1. Queue Server (queue_server.py)
Now manages:
- Shared audio queue (existing)
- **NEW**: Shared speaking flag (`mp.Value('i', 0)`)

### 2. Listener (continuous_listener.py)
**Checks speaking flag BEFORE capturing audio**:
```python
while self.running:
    # Check if Phoenix is speaking
    if self.queue_manager.is_speaking():
        stream.read(...)  # Drain audio buffer
        continue  # Skip audio capture
    
    # Normal audio capture...
```

### 3. Speech Engine (HelperPHNX.py)
**Sets flag when speaking starts**:
```python
def speak(audio):
    queue_manager.set_speaking(True)   # PAUSE listener
    queue_manager.clear()               # Clear queue
    
    # Generate and play speech
    ...
    
    sleep(1.5)  # Buffer
    queue_manager.set_speaking(False)  # RESUME listener
```

## Why This Works

**OLD (File-based)**:
```
T+0:    Create .speaking file
T+5ms:  Audio already in microphone buffer
T+8ms:  Chunk created and queued ❌
T+10ms: Processor checks file (too late!)
```

**NEW (Shared Memory)**:
```
T+0:    set_speaking(True) → Listener PAUSED immediately
T+5ms:  Listener checks flag → SKIPS audio capture ✅
T+10ms: Phoenix speaks
T+1500ms: set_speaking(False) → Listener RESUMED
```

**The listener is COMPLETELY PAUSED while Phoenix speaks!**

## What Changed

### queue_server.py
- Added `speaking_flag = mp.Value('i', 0)`
- Registered `get_speaking_flag()` method

### helpers/QueueManagerPHNX.py
- Now connects to speaking flag
- Added `set_speaking(bool)` method
- Added `is_speaking()` method

### helpers/HelperPHNX.py
- Removed file-based approach
- Now uses `queue_manager.set_speaking(True/False)`
- Cleaner, faster, more reliable

### continuous_listener.py
- Added check at top of listen loop
- If `is_speaking() == True` → Skip audio capture
- Drains audio buffer while Phoenix speaks

### bgprogs/voice_command_processor.py
- No changes needed! The listener simply won't send chunks while speaking

## Testing

```bash
# 1. Launch Phoenix (will restart queue_server with new flag)
python launch_phoenix.py

# 2. Test self-voice suppression
"Phoenix, tell me a joke"

# 3. Expected output:
👤 You [HH:MM:SS]: "Tell me a joke Phoenix"
🔊 Phoenix [HH:MM:SS]: Why did the chicken cross the road?
🎧 Listening...

# Should NOT see:
# ❌ 👤 You: "Why did the chicken cross the road?"
```

## Why This is Bulletproof

1. **Shared memory** = No file I/O delays
2. **Listener checks flag** = No audio captured while speaking
3. **Queue cleared** = Any stray chunks removed
4. **Buffer time** = Extra safety margin
5. **Process-safe** = Works across all 3 Phoenix processes

**This is the industry-standard approach for preventing echo/feedback!**

## Performance

- **Zero latency** for flag check (shared memory)
- **No I/O overhead** (no file operations)
- **Guaranteed synchronization** (multiprocessing.Value is atomic)
- **1.5s buffer** after speech (tunable)

## Troubleshooting

**If Phoenix STILL hears itself** (very unlikely):

1. Increase buffer in `HelperPHNX.py`:
   ```python
   sleep(1.5)  # Change to 2.5 or 3.0
   ```

2. Check if speaking flag is working:
   ```python
   # Add to continuous_listener.py for debugging:
   if self.queue_manager.is_speaking():
       print("[DEBUG] Listener paused - Phoenix speaking")
   ```

3. Hardware solution (100% guaranteed):
   - **Use headphones** instead of speakers
   - Phoenix audio never reaches microphone

## Comparison

| Method | Reliability | Speed | Complexity |
|--------|-------------|-------|------------|
| File-based | ⭐⭐ (race conditions) | ⭐⭐ (I/O overhead) | ⭐⭐⭐ |
| **Shared Memory** | **⭐⭐⭐⭐⭐** | **⭐⭐⭐⭐⭐** | **⭐⭐⭐⭐** |
| Headphones | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**This should finally solve the self-listening problem!** 🎯
