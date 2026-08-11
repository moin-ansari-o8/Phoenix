# Phoenix - Mistakes and Lessons

Append-only record. Read before starting work.

---

## 2026-08-10 - Cross-process shared state that silently did nothing

_Problem:_ Self-voice suppression never worked. `queue_server.py` shared a
`mp.Value("i", 0)` speaking flag through a `BaseManager`, and every process did
`flag.value = 1` / `if flag.value == 1`. The default `AutoProxy` for a
`Synchronized` object exposes only `('acquire', 'get_lock', 'get_obj',
'release')` -- there is no `.value` on the proxy. So the write set an attribute
on the *local proxy object*, never reaching the server, and reads in other
processes raised `AttributeError`, which `QueueManager.is_speaking()` caught and
turned into `return False`. Every "pause while Phoenix is speaking" guard in the
codebase was unreachable dead code for as long as it existed.

_Solution:_ Share a plain `list` behind an explicit `ListProxy` instead. Verified
with two independent connections that a write on one is visible to the other
before building anything on top of it.

_Lesson:_ `BaseManager.register()` without an explicit `proxytype` gives you an
AutoProxy that exposes public *methods* only -- not properties, not dunder
access like `__getitem__`. Never assume shared state works because the code
looks right; prove it with two connections. And never write
`except Exception: return False` around a state read, because that converts a
wiring bug into permanently wrong behaviour that looks like a working feature.

_Related Files:_ core/queue_server.py, Utils/limbs/queue_manager.py

---

## 2026-08-10 - webrtcvad frame size, swallowed by a bare except

_Problem:_ The listener fed webrtcvad 1024-sample (64 ms) frames. webrtcvad
accepts only 10/20/30 ms frames, so every call raised "Error while processing
frame" straight into `except Exception: pass`. VAD was dead, detection silently
degraded to a fixed `RMS > 150` threshold that ordinary room noise clears
permanently, the speech state latched on and never released, and every utterance
ever produced was exactly `MAX_SPEECH_DURATION` (30.08 s) of mostly noise. That
one defect caused all four reported symptoms: slow replies, self-voice being
transcribed, "Thank you." hallucinations, and "is it even listening?".

_Solution:_ Rebuilt capture around Silero VAD (bundled with faster-whisper) on
32 ms frames, with webrtcvad as a fallback given a correct 30 ms slice, an
adaptive noise floor instead of a fixed threshold, and a real endpointer.

_Lesson:_ A bare `except: pass` around a detector turns "this component is
broken" into "this component votes no", which is indistinguishable from working.
Log the exception at minimum. Also: if a signal-processing path has no test, it
has no floor -- a five-line unit test asserting "silence produces no utterance"
would have caught this on day one.

_Related Files:_ core/continuous_listener.py, Utils/limbs/audio_capture.py,
tests/test_listener_pipeline.py

---

## 2026-08-10 - Probing the wrong library for GPU support

_Problem:_ Whisper device selection asked `torch.cuda.is_available()`. The
installed torch is a CPU-only build (`2.11.0+cpu`), so it always answered False
and pinned STT to the CPU. But torch does not run Whisper here -- CTranslate2
does, and `ctranslate2.get_cuda_device_count()` returns 1. The probe measured a
library that was not involved in the decision.

_Secondary trap:_ CTranslate2 reporting a CUDA device is still not proof it
works. The model loads fine on `cuda` and only fails at first encode with
`Library cublas64_12.dll is not found`. A capability probe that does not
exercise the real code path proves nothing.

_Solution:_ Probe CTranslate2, and warm the model up on the real transcribe path
at startup so a broken CUDA install surfaces immediately and falls back to CPU,
rather than failing on the user's first command.

_Lesson:_ Ask the library that actually does the work. Then confirm by doing the
work once, at startup, where a failure is cheap.

_Related Files:_ Utils/runners/voice_command_processor.py

---

## 2026-08-10 - Whisper pads to 30s, so short utterances are not proportionally cheaper

_Problem:_ Planned to fix latency by shortening utterances from 30 s to ~3 s,
assuming STT time would fall proportionally. It does not: Whisper pads every
input to a 30 s mel window, so encoder cost is nearly constant. Measured on this
machine for a 3 s command: `small.en` 2.74 s vs `base.en` 0.74 s. Only the
decoder shrinks with shorter audio. `chunk_length=10/15` does not help either --
CTranslate2 pads internally regardless.

_Solution:_ Default to `base.en`. Shortening utterances is still essential (it
is what stops self-voice and noise reaching the model at all), just not for the
reason assumed.

_Lesson:_ Measure the actual latency curve before choosing a model on
reasoning alone. "Smaller input, proportionally less work" is not true of
fixed-window encoders.

_Related Files:_ core/config.py, core/config.json

---

## 2026-08-10 - "Prefer the quietest microphone" selects a dead one

_Problem:_ `VoiceRecognition._get_working_microphone_index` picks the *quietest*
openable mic, on the theory that a mic already in use by another app carries
that app's audio and reads loud. The opposite is true on Windows: a microphone
held by a call app opens successfully and delivers digital silence. The rule
therefore actively selects the unusable device.

_Second bug found while fixing it:_ the replacement probe measured a device
immediately after opening it and declared all three inputs dead (peak=1).
Windows shared-mode capture returns zero-filled buffers for the first few
hundred ms after a stream opens. Without a warm-up read, every healthy mic looks
broken -- worse than not probing at all, because it moves Phoenix off a good mic.

_Solution:_ Select *against* digital silence (peak below a small threshold after
a 0.4 s warm-up read), prefer a healthy default, and re-probe mid-session if the
active device goes silent for 20 s.

_Lesson:_ "Busy" and "silent" are the same observation on Windows audio, and
a freshly opened capture stream lies for the first fraction of a second. Always
discard the head of a measurement window.

_Related Files:_ Utils/limbs/audio_capture.py, core/continuous_listener.py

---

## 2026-08-10 - Two code paths, one callback

_Problem:_ `CapturePipeline.process_frame` returned a finished utterance but
only `run()` invoked `on_utterance` and incremented stats. Driving frames
directly -- which is how tests and any non-mic caller work -- silently dropped
every utterance while `process_frame` appeared to succeed.

_Solution:_ Moved dispatch and stats into `process_frame` so both paths behave
identically; `run()` is now just a loop.

_Lesson:_ If a method is documented as "broken out so tests can drive it", it
must do everything the live path does. Otherwise the tests validate a different
program than the one that ships.

_Related Files:_ Utils/limbs/audio_capture.py
