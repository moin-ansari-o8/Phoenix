# Debug Guide for Continuous Listening

## Run MainPHNX with Debug Output

```bash
python main_assistant.py
```

## What to Look For

### 1. On Startup:
```
[VoiceRecognition] Loading Faster-Whisper (small model)...
[VoiceRecognition] Faster-Whisper loaded - Offline mode enabled!
```
✅ Whisper loaded successfully

### 2. When take_command() is called:
```
[DEBUG] Starting continuous listen...
[DEBUG] Initializing PyAudio...
[DEBUG] PyAudio stream opened
>>> [Listening continuously - speak and pause 0.8s]
```
✅ Audio stream started

### 3. When you speak:
```
[DEBUG] Speech detected! Energy=True (RMS=XXX), VAD=True
[DEBUG] Speech START (chunk XX)
```
✅ Voice detected

### 4. When you stop speaking:
```
[DEBUG] Silence START (buffered XX chunks)
[DEBUG] Silence threshold reached (0.8s), processing...
[DEBUG] Speech duration: X.XXs
<<< [Processing with Whisper...]
```
✅ Started processing

### 5. During transcription:
```
[DEBUG] Transcribing XX chunks...
[DEBUG] Audio array shape: (XXXXX,), dtype: int16
[DEBUG] Normalized audio, calling Whisper...
[DEBUG] Whisper completed, collecting segments...
[DEBUG] Transcription complete: 'your text here'
```
✅ Transcription successful

### 6. Final result:
```
[DEBUG] Transcription result: 'your text here'
```

## Common Issues

### Issue: Stuck at "Initializing PyAudio"
**Cause:** Microphone access blocked or no microphone
**Fix:** Check microphone permissions

### Issue: No "[DEBUG] Speech detected"
**Cause:** Energy threshold too high or VAD too strict
**Fix:** Lower ENERGY_THRESHOLD in HelperPHNX.py (line ~221)

### Issue: Stuck at "Processing with Whisper"
**Cause:** Audio buffer too large or Whisper taking long
**Fix:** Speak shorter sentences or reduce beam_size

### Issue: Returns empty string ""
**Possible causes:**
- Speech too short (< 0.3s)
- Whisper failed to transcribe
- Check for [ERROR] messages

## Adjust Settings

In `helpers/HelperPHNX.py`, around line 215-221:

```python
# Make detection more sensitive:
self.ENERGY_THRESHOLD = 30  # Lower = more sensitive (default 50)

# Wait longer before processing:
self.MIN_SILENCE_DURATION = 1.2  # Longer pause (default 0.8)

# Accept shorter speech:
self.MIN_SPEECH_DURATION = 0.2  # Shorter minimum (default 0.3)
```

## Test Sequence

1. Run `python main_assistant.py`
2. Wait for "Listening continuously" message
3. Say "Phoenix what time is it"
4. Wait 1 second (silence)
5. Watch debug output

If it gets stuck, copy all debug output and share it!
