# Phoenix Fixes - Self-Voice Suppression & Accurate Timestamps

## Issues Fixed

### 1. Phoenix Hearing Its Own Voice (Self-Listening)
**Problem**: Phoenix's speech was picked up by the microphone and transcribed as user input, causing it to respond to itself.

**Solution**: Cross-process speaking state management
- **HelperPHNX.py** (`speak()` method): Creates `.speaking` file when Phoenix starts speaking, removes it after speech + 0.5s buffer
- **voice_command_processor.py**: Added `is_speaking()` function that checks for `.speaking` file
- **voice_command_processor.py** (`process_audio_chunk()`): Skips audio processing if `is_speaking()` returns True
- **ConsoleUI.py**: Added speaking state management methods (for future in-process use)

**How it works**:
```
User: "Hello Phoenix"
   ↓
Phoenix speaks: "Hi there!" [.speaking file created]
   ↓
Microphone captures Phoenix's voice
   ↓
Processor checks: is_speaking() = True → Skip chunk
   ↓
Phoenix finishes + 0.5s buffer [.speaking file deleted]
   ↓
Back to normal listening
```

### 2. Inaccurate Timestamps
**Problem**: Both user and Phoenix timestamps showed the same time (transcription completion time), not when actual speech occurred.

**Solution**: Use AudioChunk.timestamp (captured when audio chunk is created)
- **QueueManagerPHNX.py**: AudioChunk already has `timestamp` field set via `time.time()` when created
- **voice_command_processor.py** (`process_audio_chunk()`): Extracts timestamp from AudioChunk
- **voice_command_processor.py** (`transcribe_audio()`): Now accepts optional `timestamp` parameter
- **ConsoleUI.py** (`user_said()`): Now accepts optional `timestamp` parameter

**How it works**:
```
User speaks at 01:52:10
   ↓
Silence detected at 01:52:12 → AudioChunk created with timestamp=1743728530.0
   ↓
Chunk sent to processor
   ↓
Transcription completes at 01:52:15
   ↓
Display: "👤 You [01:52:10]: Hello" ✅ (uses captured timestamp, not current time)
```

### 3. Console Logging Cleanup
**Problem**: Verbose INFO logs appearing in console (e.g., "Chunk sent: 5.89s, energy: 328.1")

**Solution**: Remove all console handlers from loggers
- **continuous_listener.py**: Added explicit code to remove StreamHandlers from both logger and root logger
- All logging now goes only to files:
  - `phoenix_launcher.log` (launch_phoenix.py)
  - `phoenix_listener.log` (continuous_listener.py)
  - `bg_voice_processor.log` (voice_command_processor.py)
  - `phoenix_queue.log` (QueueManagerPHNX.py)

**Console output now shows only**:
- Clean TUI with status line (🎧 Listening... / 🎙️ Voice detected... / 🧠 Processing...)
- Conversation blocks with timestamps
- No technical logs

## Files Modified

### helpers/ConsoleUI.py (NEEDS RENAME)
- Created as `ConsoleUI_new.py` - **needs to replace `ConsoleUI.py`**
- Added speaking state: `_is_speaking`, `_speaking_end_time`, `_speaking_buffer`
- Added methods: `start_speaking()`, `stop_speaking()`, `should_ignore_audio()`, `is_speaking()`
- Updated `user_said()` to accept optional `timestamp` parameter
- Added `STATUS_SPEAKING` state

### helpers/HelperPHNX.py
- `speak()` method updated to create/remove `.speaking` file
- Wraps speech in try/finally to ensure `.speaking` is always cleaned up
- Adds 0.5s buffer after speech before removing flag

### bgprogs/voice_command_processor.py
- Added `is_speaking()` function to check `.speaking` file exists
- `process_audio_chunk()`: Skips processing if `is_speaking()` returns True
- `process_audio_chunk()`: Extracts timestamp from AudioChunk for accurate timing
- `transcribe_audio()`: Accepts optional `timestamp` parameter
- `transcribe_audio()`: Passes timestamp to `user_said()`

### continuous_listener.py
- Added code to explicitly remove StreamHandlers from logger and root logger
- Ensures all logs go only to `phoenix_listener.log`, not console

## How to Test

1. **Rename ConsoleUI file**:
   ```cmd
   cd helpers
   del ConsoleUI.py
   ren ConsoleUI_new.py ConsoleUI.py
   cd ..
   ```

2. **Run verification test**:
   ```cmd
   python test_fixes.py
   ```

3. **Launch Phoenix**:
   ```cmd
   python launch_phoenix.py
   ```

4. **Test self-voice suppression**:
   - Say: "Phoenix, tell me a joke"
   - Phoenix will respond with a joke
   - Verify the console does NOT show Phoenix's response as user input
   - Check `.speaking` file is created and removed (may be too fast to see)

5. **Test accurate timestamps**:
   - Say: "Phoenix, hello there"
   - Note the time you spoke
   - Check the "👤 You [HH:MM:SS]" timestamp matches when you spoke, not when transcription completed

6. **Test console cleanliness**:
   - Verify console only shows:
     - Banner
     - Status line (updates in place at bottom)
     - Conversation blocks (You said / Phoenix said)
   - NO "Chunk sent", "energy", or other technical logs

## Known Limitations

- **Speaking buffer**: 0.5s after speech may not be enough for all systems. If Phoenix still hears itself, increase the buffer:
  - In `HelperPHNX.py` `speak()`: Change `sleep(0.5)` to `sleep(1.0)` or higher
  
- **Timestamp accuracy**: Timestamp is captured when audio chunk is CREATED (after silence detection), not when speech STARTS. This is still more accurate than before, but there's ~0.8s delay.

- **Cross-process file**: Using `.speaking` file for IPC is simple but not the most elegant. A better solution would be to add a "speaking" flag to the queue server.

## Future Improvements

1. **Add speaking flag to queue_server.py** instead of file-based IPC
2. **Capture timestamp at speech START** not at silence detection
3. **Dynamic speaking buffer** based on actual speech duration
4. **Acoustic echo cancellation** (AEC) for more robust self-voice suppression
5. **Voice fingerprinting** to distinguish user vs Phoenix voice patterns
