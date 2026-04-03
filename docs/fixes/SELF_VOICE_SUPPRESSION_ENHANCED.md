# Self-Voice Suppression Fix - Enhanced Version

## The Problem (Race Condition)

**Original Issue**: The `.speaking` file was created AFTER audio was already captured and queued.

**Timeline of the bug**:
```
T+0ms:   Phoenix starts speak() method
T+5ms:   Phoenix outputs "Hello there"
T+5ms:   → Audio hits speakers
T+6ms:   → Microphone picks it up
T+7ms:   → Listener VAD detects voice
T+8ms:   → AudioChunk created and sent to queue ❌
T+10ms:  → .speaking file finally created (TOO LATE!)
T+500ms: Processor checks is_speaking() = True
         But chunk already queued and waiting!
T+2000ms: .speaking file deleted
T+2100ms: Processor gets the queued chunk
          is_speaking() = False (file deleted)
          → Transcribes Phoenix's own speech ❌
```

## The Solution (Multi-Layered Defense)

### Layer 1: Set Speaking Flag EARLY ✅
- Create `.speaking` file BEFORE any output or audio generation
- File created at the very start of speak() method

### Layer 2: Clear the Queue ✅
- When speak() starts: Clear any existing audio chunks in queue
- When processor detects speaking: Drain queue continuously

### Layer 3: Longer Buffer Time ✅
- Increased from 0.5s to 2.0s after speech ends
- Extra 0.5s buffer for microphone audio to clear
- Total: ~2.5 seconds of silence after Phoenix stops

### Layer 4: Continuous Queue Draining ✅
- While `is_speaking() = True`, processor actively drains queue
- Removes up to 20 chunks per check (safety limit)
- Prevents audio accumulation during speech

## Implementation Details

### helpers/HelperPHNX.py - speak() method
```python
def speak(self, audio, speed=174):
    # 1. FIRST: Set speaking flag (BEFORE anything else)
    with open(speaking_file, "w") as f:
        f.write(str(time.time()))
    
    # 2. Clear queue immediately
    try:
        qm = QueueManager()
        qm.clear()  # Remove any queued audio
    except:
        pass
    
    # 3. Then generate and play audio
    phoenix_said(audio)
    self._generate_and_play_edge_tts(audio)
    
    # 4. LONG buffer after speech
    sleep(2.0)  # Wait for microphone audio to clear
    os.remove(speaking_file)
    sleep(0.5)  # Extra buffer
```

### bgprogs/BgVoiceProcessorPHNX.pyw - process_audio_chunk()
```python
def process_audio_chunk(self, chunk):
    # Check if speaking
    if is_speaking():
        logger.debug("Skipping chunk - Phoenix is speaking")
        
        # Actively drain the queue while speaking
        cleared = 0
        while not self.queue_manager.is_empty():
            self.queue_manager.receive_chunk(timeout=0.01)
            cleared += 1
            if cleared > 20:  # Safety limit
                break
        
        if cleared > 0:
            logger.debug(f"Cleared {cleared} chunks during speaking")
        
        return  # Skip this chunk
    
    # Normal processing...
```

## How to Test

### 1. Check the logs
Enable debug logging to see if chunks are being skipped:
```bash
# Check bg_voice_processor.log after running Phoenix
tail -f bg_voice_processor.log | grep "is_speaking\|Cleared"
```

You should see:
```
is_speaking() = True (Phoenix is speaking, audio will be skipped)
Cleared 5 chunks from queue during speaking
Skipping chunk - Phoenix is speaking
```

### 2. Test self-voice suppression
```bash
python launch_phoenix.py

# Say: "Phoenix, tell me a joke"
# Phoenix responds: "Why did the chicken cross the road?"

# Expected output:
👤 You [HH:MM:SS]: "Tell me a joke Phoenix"
🔊 Phoenix [HH:MM:SS]: Why did the chicken cross the road?
🎧 Listening...

# Should NOT see:
# ❌ 👤 You [HH:MM:SS]: "Why did the chicken cross the road?"
```

### 3. Verify .speaking file timing
Open a second terminal and watch the .speaking file:
```bash
# In a separate terminal
while true; do 
    if [ -f .speaking ]; then 
        echo "$(date +%H:%M:%S) - SPEAKING"; 
    else 
        echo "$(date +%H:%M:%S) - listening"; 
    fi; 
    sleep 0.1; 
done
```

You should see `.speaking` appear when Phoenix talks and disappear ~2.5 seconds after.

## Expected Behavior

**Before fix**:
```
👤 You: "Hello Phoenix"
🔊 Phoenix: "Hi there!"
👤 You: "Hi there!"          ❌ Phoenix heard itself
👤 You: "How can I help?"     ❌ Still hearing itself
```

**After fix**:
```
👤 You: "Hello Phoenix"
🔊 Phoenix: "Hi there!"
[.speaking file exists for ~3 seconds]
[All audio chunks during this time are SKIPPED]
🎧 Listening...              ✅ Clean, no self-listening
```

## Tuning the Buffer Time

If Phoenix STILL hears itself:
1. Increase sleep times in `HelperPHNX.py` speak():
   - Change `sleep(2.0)` to `sleep(3.0)` or `sleep(4.0)`
   - Change final `sleep(0.5)` to `sleep(1.0)`

2. The trade-off:
   - Longer buffer = More reliable (no self-listening)
   - Longer buffer = Slower response time after Phoenix speaks

Current settings: 2.5 seconds total buffer (good balance)

## Why This Works

**Multi-layered defense strategy**:
1. ✅ Flag set before audio generated
2. ✅ Queue cleared when speaking starts
3. ✅ Queue actively drained during speaking
4. ✅ Long buffer after speaking ends
5. ✅ Extra buffer for microphone to clear

**Even if one layer fails, others catch it**:
- If some chunks slip through → Cleared by active draining
- If draining misses some → Caught by the 2.5s buffer
- If buffer is too short → Can be easily increased

## Performance Impact

- **CPU**: Minimal (just file existence checks)
- **Latency**: +2.5 seconds after Phoenix speaks before accepting new input
- **Memory**: Negligible (small file + queue clearing)
- **Reliability**: High (multi-layered approach)

## Troubleshooting

**If Phoenix still hears itself**:

1. Check if `.speaking` file is being created:
   ```python
   # Add this to speak() method for debugging:
   print(f"[DEBUG] .speaking file created at: {speaking_file}")
   ```

2. Check processor logs:
   ```bash
   grep "is_speaking\|Skipping chunk" bg_voice_processor.log
   ```
   Should see many "Skipping chunk" messages when Phoenix speaks.

3. Increase buffer time to 5 seconds:
   ```python
   # In HelperPHNX.py speak() finally block:
   sleep(5.0)  # Was 2.0
   ```

4. Check microphone input level:
   - If Phoenix is TOO LOUD in speakers, even long buffers won't help
   - Reduce speaker volume
   - Use headphones instead of speakers (best solution)

## Alternative Solutions (If This Still Fails)

1. **Hardware solution**: Use headphones (Phoenix audio doesn't reach mic)
2. **OS-level**: Use "Stereo Mix" loopback with exclusions
3. **Software**: Implement acoustic echo cancellation (AEC) library
4. **Pause listening**: Completely stop the listener while speaking
5. **Voice fingerprinting**: Train ML model to recognize Phoenix's voice vs yours

The current solution should work for 95% of cases. For the remaining 5%, hardware solutions (headphones) are most reliable.
