# How to Test Continuous Listening

## Step 1: Install Dependencies

Run this command:

```bash
pip install webrtcvad
```

Wait for it to finish installing.

## Step 2: Test Continuous Listening

Run this command:

```bash
python test_continuous_listen.py
```

### What will happen:
1. Shows if Whisper and VAD are loaded
2. Starts listening continuously
3. Speak as much as you want
4. Pause for 0.8 seconds
5. Shows your transcription

### Expected output:
```
✅ Whisper loaded - OFFLINE mode
✅ VAD enabled - Detects voice automatically

📌 How it works:
   - Always listening (no timeouts)
   - Speak as long as you want
   - Pauses 0.8s → processes speech
   - Ignores non-voice noise

🎤 Start speaking... (0.8s pause to process)
```

## Step 3: Test with MainPHNX

If test works, run the full assistant:

```bash
python main_assistant.py
```

Now Phoenix will use continuous listening instead of 8-second timeout.

## Alternative Tests

### Test helper file directly:
```bash
python helpers\HelperPHNX.py
```

### Quick Whisper check:
```bash
python test_whisper_quick.py
```

## Troubleshooting

### If webrtcvad installation fails:
Try installing from wheel file:
```bash
pip install --user webrtcvad
```

### If it says "module not found":
Make sure you're using the same Python where you installed faster-whisper:
```bash
python -c "import faster_whisper; print('Whisper OK')"
python -c "import webrtcvad; print('VAD OK')"
```

### If both print "OK", you're ready to test!

## What Changed

- **Before**: 8-second timeout, fixed pauses
- **After**: Continuous listening, processes on 0.8s silence
- **Flow**: Exactly the same, just no timeouts

Run the test and let me know what happens!
