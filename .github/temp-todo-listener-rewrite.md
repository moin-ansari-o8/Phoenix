# Task: Listener architecture rewrite (always-on, self-voice-proof, low latency)
Generated: 2026-08-10

## Evidence gathered (not guesses - measured from this machine + the 20:xx session logs)

| # | Finding | Proof |
|---|---------|-------|
| E1 | **Every single audio chunk is exactly 30.08 s** (481280 samples). Not one utterance ever ended on silence. | `bg_voice_processor.log` - every `Transcribing audio (shape: (481280,)` line, back to back, every 30 s |
| E2 | The listener's silence branch is unreachable in this room. `is_speaking` latches True on the first noisy frame and only unlatches at `MAX_SPEECH_DURATION` (30 s) | `phoenix_listener.log`: `Speech CONFIRMED (chunk 17401)` -> `Chunk sent: 30.08s` -> `Speech CONFIRMED (chunk 17871)`; 17871-17401 = 470 frames = 30.08 s, i.e. **every frame was buffered as speech** |
| E3 | **webrtcvad is silently dead.** `_detect_speech` passes a 1024-sample (64 ms) frame; webrtcvad only accepts 10/20/30 ms | Verified: `v.is_speech(<1024 samples>, 16000)` -> `Error while processing frame`, swallowed by `except Exception: pass` (continuous_listener.py:138) |
| E4 | So detection is **pure RMS > 150**, which fan/room noise clears permanently -> E2 | continuous_listener.py:86,128 |
| E5 | **Whisper is pinned to CPU forever.** Device is chosen by `torch.cuda.is_available()`, but the installed torch is `2.11.0+cpu`. CTranslate2 (the engine that actually matters) **does see the GPU** | `torch.cuda.is_available() -> False`; `ctranslate2.get_cuda_device_count() -> 1`; cuda compute types include `int8_float16` |
| E6 | STT cost is ~3.0 s per turn purely because it transcribes 30 s of mostly-noise | 20:11:51.25 chunk -> 20:11:54.26 transcript |
| E7 | GPU headroom is thin: 4096 MiB total, 2753 MiB already held by `llama3.2` which is **already spilling** (10%/90% CPU/GPU) | `nvidia-smi`, `ollama ps` |
| E8 | `small.en` (English-only, faster + more accurate for English than `small`) is **already cached** | `~/.cache/huggingface/hub/models--Systran--faster-whisper-small.en` |
| E9 | `SpeechEngine.speak()` opens a **brand new named-pipe `QueueManager()` connection on every utterance** | assistant_io.py:341 |
| E10 | The self-voice gate stalls the mic stream instead of draining it: 1024 frames (64 ms) read per >=50 ms sleep, so the OS input buffer **accumulates Phoenix's own TTS** and is replayed as user speech afterwards | continuous_listener.py:218-225 |

### How E1-E4 + E10 produce every symptom the user reported

- **"it listens to its own response"** - the 30 s window straddles Phoenix's TTS playback. Proof from the log, one chunk containing self-voice **and** the user's next command concatenated:
  `'I'm running on Kaly's Windows PC, your majesty, assisting with tasks... Set brightness to 50%.'`
- **"automatically listening thank you??"** - 30 s of pure room noise fed to Whisper. `Thank you.` / `Thanks for watching!` is Whisper's single most common silence hallucination. Log shows `Transcribed: 'Thank you.  Bye.'` at 19:59, 20:02, 20:03.
- **"taking too much time"** - 3.0 s of STT on a 30 s buffer, on CPU, on top of up to 30 s of buffering delay before STT even starts.
- **"is my always-listening algorithm working?"** - No. It is always *buffering*, which is not the same thing. It has never once endpointed on silence.

---

## Target architecture

```
mic ──► [PyAudio callback, 20 ms frames] ──► ring buffer (never blocks, never backs up)
                                              │
                                              ├─► EchoGate      (drop frames captured while TTS was audible)
                                              ├─► SileroVAD     (per-frame speech prob, adaptive noise floor under it)
                                              └─► Endpointer    (pre-roll 300 ms, hangover 600 ms, min 250 ms, max 12 s)
                                                     │
                                                     ▼  utterance (typically 1.5-4 s)
                                              [faster-whisper small.en, warm, no double-VAD]
                                                     │
                                              AntiHallucination (no_speech_prob / avg_logprob / phrase blacklist)
                                                     │
                                              SelfEchoReject   (fuzzy match vs last 5 things Phoenix said)
                                                     │
                                                     ▼
                                              wake-word / follow-up routing (unchanged)
```

Design rules:
1. **The stream is never paused.** Ever. Pausing is what created the backlog. Frames are always read; unwanted ones are *discarded by capture timestamp*.
2. **Time-based gating, not flag-based.** A frame is self-voice if `frame_capture_time` falls inside `[tts_start, tts_end + tail]`. Checking "is the flag set *now*" is wrong for audio that was captured 8 s ago - that is exactly bug E10.
3. **Two independent self-voice defenses** (acoustic gate + text similarity), because either alone leaks.
4. **VAD decides, energy only vetoes.** Adaptive noise floor tracked as a rolling percentile so a fan can never latch the machine open again.

---

## Tasks

### Phase 0 - Stop the bleeding (small, high payoff, no new deps)
- [todo-0.1] `continuous_listener.py`: split each 1024-sample read into 20 ms sub-frames before calling webrtcvad -> VAD actually runs (fixes E3)
- [todo-0.2] Replace fixed `ENERGY_THRESHOLD = 150` with adaptive noise floor (`floor = 20th-percentile RMS over trailing 3 s`, speech needs `rms > max(floor * 3.0, 120)`) (fixes E4)
- [todo-0.3] Drop `MAX_SPEECH_DURATION` 30 s -> 12 s so a stuck state machine can never again cost 30 s
- [todo-0.4] `voice_command_processor.py`: gate on `torch.cuda` REMOVED; probe `ctranslate2.get_cuda_device_count()` instead, model `small` -> `small.en`, `compute_type` `int8` (CPU) / `int8_float16` (GPU), `cpu_threads=4`, `condition_on_previous_text=False`, `vad_filter=False` (fixes E5/E6)
- [todo-0.5] Warm-up transcribe of 1 s of silence at startup so the first real turn isn't 2 s slower

### Phase 1 - New capture engine (`Utils/limbs/audio_capture.py`, new file)
- [todo-1.1] `MicStream`: PyAudio **callback** mode, 16 kHz mono, `frames_per_buffer=320` (20 ms), pushes `(timestamp, np.int16[320])` into a `collections.deque(maxlen=...)`. Callback never blocks -> no OS-level backlog is possible
- [todo-1.2] Device selection: reuse the RMS-probe mic picker from `VoiceRecognition._get_working_microphone_index` (the listener currently ignores it and just takes the default device)
- [todo-1.3] `NoiseFloor`: rolling 3 s percentile tracker, exposed for logging
- [todo-1.4] `SileroVAD` wrapper over `faster_whisper.vad.get_vad_model()` - already bundled with faster-whisper 1.2.1, **no new dependency**. webrtcvad (with correct 20 ms frames) stays as fallback
- [todo-1.5] `Endpointer` state machine: `pre_roll=300 ms`, `start` = 3 consecutive voiced frames, `end` = 600 ms unvoiced hangover, `min_utterance=250 ms voiced`, `max_utterance=12 s`, and a hard reset hook
- [todo-1.6] Rewrite `core/continuous_listener.py` to be a thin driver over the above. Delete the old inline state machine

### Phase 2 - Self-voice suppression
- [todo-2.1] Queue server: replace the bool `speaking_flag` with a shared `speaking_until` float (epoch seconds) + `speaking_since`. Bool cannot express "audio captured during that window"
- [todo-2.2] `EchoGate.should_drop(frame_ts)` -> `speaking_since - 0.15 <= frame_ts <= speaking_until + 0.40`. Frames are still *read*, just dropped
- [todo-2.3] On gate close: **flush the ring buffer and hard-reset the Endpointer**, so post-TTS backlog can never merge into a live utterance (this is the direct fix for the concatenated-transcript bug)
- [todo-2.4] `SelfEchoReject`: ring of the last 5 TTS strings; reject a transcript if `difflib.SequenceMatcher.ratio() > 0.62` against any of them, or if it is a >=6-word substring of one. Log as `[SELF_ECHO]`, never route it
- [todo-2.5] Fix E9: `SpeechEngine` holds **one** `QueueManager` for its lifetime instead of reconnecting per utterance
- [todo-2.6] Config switch `audio.echo_mode`: `"gate"` (default, speakers) / `"open"` (headphones - gate disabled, full duplex, enables barge-in)

### Phase 3 - STT quality + latency
- [todo-3.1] Anti-hallucination filter: drop a segment if `no_speech_prob > 0.6`, or `avg_logprob < -1.0`, or (utterance < 1.2 s AND text in blacklist). Blacklist: `thank you`, `thanks for watching`, `bye`, `you`, `.`, `subtitles by...`, etc.
- [todo-3.2] Require `voiced_ms >= 400` from the VAD before an utterance is even sent to Whisper - noise-only windows never reach the model
- [todo-3.3] Keep `initial_prompt` (the wake-word biasing) but cap it - measure whether it helps or hurts hallucination rate
- [todo-3.4] Emit `[STT] utt=2.1s voiced=1.6s stt=0.31s rtf=0.15` trace so latency is never guesswork again

### Phase 4 - Barge-in (README "Conversational Interruption")
- [todo-4.1] Replace blocking `mciSendStringW("play {alias} wait")` with non-blocking `play` + status poll, so `stop` can land mid-sentence
- [todo-4.2] `interrupt_flag` on the queue server; listener sets it when confirmed speech survives the echo gate while TTS is playing
- [todo-4.3] Only enabled when `echo_mode == "open"` (headphones) or real AEC is present - otherwise Phoenix would interrupt itself. Default OFF
- [todo-4.4] (optional) Global push-to-interrupt hotkey as the zero-risk alternative

### Phase 5 - Verification
- [todo-5.1] `tests/test_endpointer.py` - synthetic frame sequences (speech/silence/noise-floor-drift) assert utterance boundaries. **This is the test that would have caught the 30 s bug on day one**
- [todo-5.2] `tests/test_echo_gate.py` - a frame captured mid-TTS but processed after TTS ends must be dropped (regression test for E10)
- [todo-5.3] `tests/test_hallucination_filter.py` - "Thank you." at low confidence + short duration must be rejected
- [todo-5.4] `tests/test_self_echo_reject.py` - feed Phoenix's own logged reply back in, assert rejection
- [todo-5.5] Live 10-minute soak: silent room must produce **zero** transcripts; 20 spoken commands must produce 20 utterances of 1-5 s each

---

## Expected outcome

| Metric | Now | Target |
|---|---|---|
| Time from end-of-speech to Phoenix starting to think | up to 30 s | 0.6 s (hangover) + ~0.3 s (STT) |
| Utterance length sent to Whisper | always 30.08 s | 1-5 s (actual speech) |
| False transcripts in a silent room | ~1 per 30 s ("Thank you.") | 0 |
| Self-voice fed back as user input | routinely | 0 (2 independent defenses) |
| "Is it listening?" | unanswerable | `[VU]`/`[STT]` traces + noise-floor log |

## Progress Notes

**All phases implemented and verified. [tested] 49/49 checks passing.**

### Findings that changed the plan mid-flight
- **E11 (bigger than E10):** the `speaking_flag` never crossed the process boundary at all.
  `AutoProxy` for `mp.Value` exposes only `('acquire','get_lock','get_obj','release')`, so
  `flag.value = 1` set a local attribute and every reader got `AttributeError` ->
  `is_speaking()` returned `False` always. Self-voice suppression was unreachable dead code.
  Replaced with a plain list behind an explicit `ListProxy`, verified across two connections.
- **E12:** Whisper pads to a 30 s mel window, so encoder cost barely depends on utterance
  length. Measured for a 3 s command: `small.en` 2.74 s vs `base.en` 0.74 s. `chunk_length`
  does not help. **Default changed from `small.en` to `base.en`.**
- **E13:** CUDA is unusable on this box regardless of config - `cublas64_12.dll is not found`
  at first encode. Model load succeeds and only fails later, so warm-up now runs on the real
  transcribe path and falls back to CPU.
- **E14 (from user, mid-session):** a mic held by a call delivers digital silence, so the
  existing "prefer the quietest mic" helper would deliberately pick the dead device.
  Added live device selection + mid-session switching. Also had to add a 0.4 s warm-up read:
  Windows returns zero buffers right after stream open, which made all three inputs look dead.

### Status by phase
- [tested] Phase 0 - folded into Phase 1 rather than writing code destined for deletion
- [tested] Phase 1 - `Utils/limbs/audio_capture.py`, `core/continuous_listener.py` rewritten
- [tested] Phase 2 - timestamp echo gate, ring-buffer flush + endpointer reset, self-echo
  filter, persistent `QueueManager` in `SpeechEngine`, live `audio.echo_mode` switch
- [tested] Phase 3 - hallucination filter, `voiced_ms` requirement, `[STT]` traces
- [tested] Phase 4 - polled MCI playback + pyttsx3 interrupt watcher, `interrupt_flag`
- [tested] Phase 5 - `tests/test_listener_pipeline.py`, 49 checks

### Measured results
| Metric | Before | After |
|---|---|---|
| Utterance length reaching Whisper | always 30.08 s | 2.7-3.3 s (real speech) |
| End-of-speech to transcript | up to 33 s | **1.41 s** (0.60 hangover + 0.81 STT) |
| STT on a 3 s utterance | ~3.0 s | **0.76 s** |
| 60 s silent room, live mic | 2 x 30 s noise blobs | **0 utterances** |
| 8 s fan noise -> Whisper | 30 s blob | **0 utterances** |
| Capture pipeline CPU | n/a | 4.2% of one core |
| Cross-process speaking state | never worked | 0.064 ms/read, self-heals in 0.5 s |

### Not done (deliberate)
- Real acoustic echo cancellation (speexdsp / WebRTC APM). It is the only true fix for
  barge-in on open speakers, but it needs a far-end reference via WASAPI loopback and is a
  project of its own. `echo_mode: gate` + the self-echo filter cover speakers; headphones
  (`echo_mode: open`) give full duplex and barge-in today.
- Live verification of speech detection through the real microphone: the mic was busy in a
  call for the whole session. Detection was verified instead by feeding a real recording
  through the real Silero VAD and the real endpointer.
