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

---

## 2026-08-12 - A boolean cannot express "still"

_Problem:_ Follow-up mode was `self.loop`, set from `result is not False`. But
`PhoenixAssistant.main()` always returns `True`, so after one wake word the flag
latched on and never cleared -- Phoenix answered every utterance in the room
forever. This is the second time the same shape of bug has appeared in this
repo: `speaking_flag` as a bool had to become a `(since, until)` window for
exactly the same reason.

_Solution:_ `WakeGate._awake_until`, a deadline. `is_awake` is
`now() < _awake_until`. Only an arriving utterance can push it forward, so
silence expires it by construction rather than by remembering to clear a flag.

_Lesson:_ When state means "this was true recently", store the time it stops
being true, not a boolean. A flag needs someone to remember to unset it; a
deadline unsets itself. Reach for a timestamp whenever the correct answer
depends on *when* you ask.

_Related Files:_ Utils/limbs/wake_gate.py, Utils/runners/voice_command_processor.py

---

## 2026-08-12 - Raw f-strings ate the word boundaries

_Problem:_ `remove_phoenix_except_folder` guarded its wake-word stripping with
`rf"(?<!\w)({aliases})(?! folder)(?!\w)"`. In a **raw** string `\w` is three
characters -- backslash, backslash, w -- so the regex compiled to a lookbehind
for a literal backslash followed by `w`, which is essentially never present.
Both boundary guards were dead. The pattern had also been hardcoded to the
"phoenix" aliases, so under the `igris` profile the wake word was never stripped
and got routed to the LLM as part of the query.

_Solution:_ Delegated to `WakeGate.strip_wake`, which builds its alternation from
`AppConfig.wake_words` and uses plain `\b`.

_Lesson:_ Escaping in a raw string is already literal -- do not double it. And a
regex that silently matches too much looks identical to one that works until you
test the negative case. Every regex guard needs a test that proves it *rejects*.

_Related Files:_ Utils/limbs/command_processor.py, Utils/limbs/wake_gate.py

---

## 2026-08-12 - A local import made a module-level name unreachable

_Problem:_ Added `from core.config import AppConfig` at module level in
`command_processor.py` and used it in `__init__`. A pre-existing
`from core.config import AppConfig` still sat further down the same `__init__`.
Python decides scope statically: an import anywhere in a function body makes
that name local for the ENTIRE body, so the earlier reference raised
`UnboundLocalError` before the import line was ever reached.
`PhoenixAssistant` never constructed, the voice processor exited, and nothing
drained the audio queue.

_Solution:_ Deleted the redundant function-local imports. Added
`tests/test_startup_smoke.py`, which constructs the real objects and statically
fails any function-local import that shadows a module-level one.

_Lesson:_ Adding a module-level import is not additive - it can break code that
already worked, if any function re-imports the same name. Grep for the name
across the file before adding it at the top.

_Related Files:_ Utils/limbs/command_processor.py, Utils/runners/voice_command_processor.py

---

## 2026-08-12 - A crash that looked like a hang

_Problem:_ When the above crash killed the processor, the TUI showed
"Processing..." indefinitely. The processor's logger is file-only, so the
traceback went to `bg_voice_processor.log` and nothing reached the screen. The
symptom reported was "it's stuck, it was fast before" - which points at
performance, not at a dead subprocess, and cost real debugging time.

_Solution:_ The processor now prints a single-line `[FATAL] <type>: <msg>` to
stdout before exiting. `main.py` and `manager.py` match it BEFORE their
noise filters and show it in red with a "restart Phoenix" status.

_Lesson:_ A supervised subprocess that can die silently will eventually die
silently at the worst time. Any process whose death stops the pipeline must
announce it on the channel the UI actually reads - a log file nobody is tailing
does not count.

_Related Files:_ Utils/runners/voice_command_processor.py, main.py, Utils/runners/manager.py

---

## 2026-08-12 - The dictionary that could not fit

_Problem:_ The plan for Hindi/Gujarati recognition was "put the vocabulary in
Whisper's prompt". Measured against the real library that is impossible:
faster-whisper truncates hotwords at `max_length // 2` = **223 tokens**
(`WhisperModel.get_prompt`), and a romanised song title costs **8.7 tokens** -
against ~1.3 for an English word. The bias layer holds about **twenty titles, no
matter how large the library grows**: 50% coverage at 40 songs, 10% at 200, 4%
at 500. The first implementation silently shipped that ceiling.

_Solution:_ Two layers, split by what each is good at. Prompt bias handles the
top ~20 titles by PLAY COUNT (`Lexicon.ranked_songs`), because the budget is
fixed so the only lever is which twenty. Everything else is handled after
transcription by fuzzy matching over the whole library, which has no size limit.
Ambiguous cases get a second transcription pass biased to just 8 retrieved
candidates - and 8 always fits, whatever the library size.

_Lesson:_ When a fixed-size channel meets a growing dataset, stop trying to fit
the data and split the problem by failure mode instead. Retrieval over the full
set and ranking within it fail differently: measured here, the right title is
first only 92.9% of the time but is in the top 8 **99.6%** of the time. Design
around that gap rather than against the cap.

_Related Files:_ Utils/limbs/lexicon.py, Utils/runners/voice_command_processor.py

---

## 2026-08-12 - A repair layer that broke what already worked

_Problem:_ The transcript repair layer originally fuzzy-matched every word
against the whole lexicon - names, command words and Hinglish. Testing against
ordinary English immediately produced "what is the weather today" ->
"...weather **thoda**" and "remind me to call mom" -> "**reminder** me to
**chalu** mom". Common English words were being rewritten into Hindi ones that
happened to sit close phonetically.

_Solution:_ Scoped repair to `names` only, plus an exact alias map for known
mishearings (`phonix` -> `phoenix`). The STT model is an ENGLISH model, so
English command words are what it already gets right - running a fuzzy rewrite
over them risked the words that worked to fix words that were never broken.
Command and Hinglish vocabulary still feed the prompt BIAS, where the acoustics
still get a vote; editing a finished transcript has no such safety net.

_Lesson:_ Two lessons. A blocklist of "words not to touch" can never be
complete - scope the mechanism instead. And known cases deserve exact handling:
lowering a fuzzy threshold far enough to catch "pheonix" also catches words that
were never wrong.

_Related Files:_ Utils/limbs/lexicon.py, data/lexicon.json, tests/test_lexicon.py

---

## 2026-08-12 - pip installed a package that shadows the standard library

_Problem:_ `pip install resemblyzer` pulled in a transitive dependency literally
named `typing` - the Python 3.4 backport - which shadows the stdlib `typing`
module on 3.11 and breaks imports across unrelated packages.

_Solution:_ `pip uninstall -y typing` immediately, then verified
`typing.__file__` pointed back at the stdlib. Noted in `pyproject.toml` next to
the dependency so the next install does not repeat it.

_Lesson:_ Check what a new dependency dragged in, not just whether the install
succeeded. Backport packages named after stdlib modules are still on PyPI and
still installable on versions that have long since absorbed them.

_Related Files:_ pyproject.toml, Utils/limbs/speaker_id.py

---

## 2026-08-12 - Blocking for confirmation in a process with no microphone

_Problem:_ `play_random_song` asked "do you want to play X?" and then blocked on
`self.take_command()`. In the voice processor `Utility` is built with
`reco=None` - the microphone belongs to another process and audio arrives over a
queue - so the call raised `AttributeError` on a `None`. Even had it worked,
blocking that thread would have stalled the queue the answer needed to arrive
through.

_Solution:_ Removed the confirmation round trip; Phoenix announces what it is
about to play instead. `take_command()` now returns "" rather than raising, so
the other legacy callers degrade instead of killing the processor.

_Lesson:_ Code moved from a single-process design into a multi-process one keeps
compiling and stops making sense. Any call that waits for user input has to be
re-examined when the input arrives somewhere else - and a method that can return
None must never be called with a bare attribute access.

_Related Files:_ Utils/limbs/action_utilities.py


## 2026-08-12 - A logging import killed the entire voice subtree
_Problem:_ `core/launch_phoenix.py` gained `from core.logging_setup import setup_logging`
during the logging unification. That file had never needed a sys.path fix, because
`logging.basicConfig()` imports nothing from the package. Run as a script, `python
core/launch_phoenix.py` puts `core/` on sys.path -- not the repo root -- so the import
raised ModuleNotFoundError at line 16 and the launcher died instantly. No queue server,
no listener, no processor. The TUI starts independently and starts fine, so it sat on
"Listening - say 'phoenix'..." forever with nothing behind it. It looked like the wake
word was broken; nothing was wrong with the wake word.
_Solution:_ Put the repo root on sys.path before the first package import, and added
`tests/test_entrypoints.py`, which imports every launched script in a subprocess with
sys.path[0] set to the script's own directory - the condition that actually holds in
production - plus a static guard on import ordering.
_Lesson:_ Adding an import to a script is not a free change. A file launched by path has
a different sys.path from the same file imported by a test, and EVERY existing test
imported these modules with the repo root already present, so all 147 passed while the
assistant was completely dead. Test entry points the way they are actually started.
A second lesson: the symptom pointed at the most recently changed *feature* (the wake
gate), and the cause was in the *plumbing* of an unrelated refactor. The 0-byte
`logs/phoenix_processor.log` was the real clue - a process that never logs never ran.
_Related Files:_ core/launch_phoenix.py, core/logging_setup.py, tests/test_entrypoints.py

## 2026-08-12 - Phoenix answered its own music
_Problem:_ Phoenix played a song on YouTube; the microphone heard it through the speakers.
The echo gate only covers Phoenix's OWN speech (it knows the window in which TTS is
playing) so music was transcribed as user input, and because the follow-up window was open
every mangled lyric became a command - a four-engine web search ran on "waalakhua, ari
waalakhua". Worse, the processor loop is single-threaded, so it built a backlog: measured
transcription times of 21.0s, 20.2s, 18.9s while it ground through the chorus. Real
questions were answered half a minute late, over the music. To the user this read as
"tools are broken" and "sometimes she speaks, sometimes she doesn't". Neither was true.
_Solution:_ (1) starting media returns the wake gate to dormant, so ambient audio during
playback cannot be a follow-up; (2) audio older than `max_chunk_age_seconds` (12) is
dropped rather than transcribed, killing the backlog; (3) a failed utterance now logs a
warning with the lost text instead of returning False silently.
_Lesson:_ Two separate suspicions were wrong and cost time - the connectivity probe and
barge-in were both blamed before the log was read properly, and both were fine (the
listener had logged zero interrupts). The log said plainly what was happening: every
transcription for three minutes was song lyrics. Read the whole log before theorising.
Second lesson: a feature that emits audio into the room is not a normal action. Anything
that starts uncontrolled sound has to tell the listener, because the echo gate cannot
infer it.
_Related Files:_ Utils/runners/voice_command_processor.py, Utils/limbs/action_registry.py,
Utils/limbs/command_processor.py, Utils/limbs/assistant_io.py, tests/test_backlog.py
