# Phoenix — Local-First Desktop Voice Assistant (Windows)

**Version:** 5.9.0 · **Platform:** Windows 10/11 · **Python:** 3.10+ (venv currently pins 3.14) · **License:** MIT (pyproject) / Apache-2.0 (LICENSE file — *mismatch, needs resolving*)

> **This file is the project map.** It is written so that a new session (human or AI) can
> understand the whole system without re-reading 25k lines of source. If you change
> architecture, update this file in the same commit.

---

## 1. What Phoenix is

A always-on, wake-word-driven desktop assistant that runs on the user's own machine.
It hears you, decides what you meant, and either **does something to the PC** or
**answers you out loud**.

Two things make it different from a toy assistant:

1. **Everything heavy is local** — speech-to-text (faster-whisper), the LLM brain
   (Ollama), and text-to-speech (Piper / SAPI5). The only online path is `search_web`.
2. **Routing is layered, not fuzzy** — deterministic matchers handle the cases they
   can prove, and only genuinely ambiguous input reaches a model. This was a
   deliberate rewrite after a fuzzy string-similarity matcher caused constant
   misfires (e.g. `playsong` firing on "capital of france?").

**User identity:** `kALY` (see `core/config.json` → `user`). Active profile: `phoenix`.

---

## 2. Runtime topology

Phoenix is **not one process**. In voice mode there are four:

```
main.py  (TUI process)
  ├─ AdvancedTUIManager  (extends Utils/runners/manager.py:PhoenixRuntimeManager)
  │    ├─ GlobalSpeechWorker thread  → serialises ALL speech from this process
  │    ├─ battery-monitor-thread     (Utils/runners/battery_monitor.py)
  │    ├─ time-monitor-thread        (Utils/runners/time_monitor.py)
  │    └─ voice-processor-thread     (Utils/runners/voice_processor.py)
  │          └─ subprocess: core/launch_phoenix.py
  │
  └─ core/launch_phoenix.py  (supervisor)
        ├─ subprocess: core/queue_server.py            [IPC hub, hidden]
        ├─ subprocess: Utils/runners/voice_command_processor.py   [STT + brain + TTS]
        └─ subprocess: core/continuous_listener.py     [mic capture]
```

In **text mode** (`current_mode: 1`) the voice subtree is skipped entirely and
`main.py` drives `Utils/limbs/command_processor.py:PhoenixAssistant` directly from
keyboard input via `msvcrt`.

### IPC — `core/queue_server.py`

A `multiprocessing.managers.BaseManager` served over a **Windows named pipe**
(`\\.\pipe\phoenix_audio_queue`). It owns three shared objects:

| Object | Direction | Purpose |
|---|---|---|
| `audio_queue` (`mp.Queue`, maxsize 10) | listener → processor | finished utterances |
| `speech_state` (list of 3 floats, `ListProxy`) | speech engine → listener | `[speaking_since, speaking_until, interrupt_requested]` |
| `tts_history` (list, `ListProxy`) | speech engine → processor | last 5 things Phoenix said |

**Why a `ListProxy` and not `mp.Value`/`mp.Array`:** those get wrapped in an AutoProxy
exposing only `acquire/get_lock/get_obj/release` — no `.value`, no item assignment.
The original `speaking_flag = mp.Value("i", 0)` therefore **never crossed the process
boundary**; self-voice suppression was unreachable dead code. Do not "simplify" this back.

**Why `(since, until)` timestamps and not a boolean:** audio is examined well after
it was captured. A boolean read *now* says nothing about a frame recorded 8 seconds
ago. `until` is heartbeated forward every 200 ms while audio plays, so if the speaking
process dies mid-sentence the mic self-heals instead of wedging shut forever.

---

## 3. The listening pipeline (rewritten Aug 2026)

`Utils/limbs/audio_capture.py` holds all signal logic; `core/continuous_listener.py`
is a thin driver over it. Read the module docstring in `audio_capture.py` — it contains
the full post-mortem of the defects this design fixes.

```
mic ──► MicStream (PyAudio CALLBACK mode, 512-sample / 32 ms frames, bounded deque)
          │  the stream is NEVER paused — pausing is what created the OS-buffer backlog
          ▼
        EchoGate.should_drop(frame.timestamp)
          │  drops frames CAPTURED inside [speaking_since-0.15, speaking_until+0.35]
          │  on the close edge: flush mic buffer + hard-reset endpointer
          ▼
        VoiceDetector  — Silero VAD (bundled with faster-whisper, no extra dep)
          │  evaluated over an 8-frame (256 ms) rolling window, webrtcvad fallback
          │  RULE: VAD decides, adaptive energy floor only VETOES
          ▼
        NoiseFloor — 20th-percentile RMS over 5 s, frozen during an utterance
          │  threshold = max(floor * 3.0, 120.0)
          ▼
        Endpointer — pre-roll 300 ms, open on 3 voiced frames,
          │  close on 800 ms hangover, discard if < 400 ms voiced, hard cap 20 s
          ▼
        Continuation stitching — a closed utterance is PARKED, not sent, for
          │  stitch_window_ms (900 ms). If speech resumes inside that window the
          │  halves are concatenated and the clock restarts.
          ▼
        Utterance → create_audio_chunk() → queue → processor
```

**Pause tolerance is `hangover_ms + stitch_window_ms` = 1.7 s, but only a
sentence that actually continues pays the stitch window.** Dispatch used to be
bound to endpointing, so the only way to tolerate a slow speaker's mid-sentence
pause was to raise `hangover_ms` — which taxes every command equally. Parking
unbinds them: a finished command still goes out after `hangover_ms`.

The stitch deadline is measured in **audio time** (the frame's capture
timestamp), not wall clock — same reasoning as lesson 9 below. If this thread
stalls, wall clock races ahead while the audio the decision is about has not
moved. A parked utterance is dropped, never sent, when the echo gate closes:
otherwise a fragment captured before Phoenix spoke would be glued to the front
of the user's next command, which is the exact defect the listener rewrite
existed to kill.

Then in `Utils/runners/voice_command_processor.py`:

```
        SpeakerVerifier.verify()  (Utils/limbs/speaker_id.py)
          │  BEFORE Whisper: ~16 ms vs ~800 ms, so a stranger never reaches STT
          │  ships in "log" mode — scores printed, nothing suppressed
          ▼
        faster-whisper (base.en, CPU int8 by default, cpu_threads=6,
          │             hotwords=<priority-ordered lexicon>, language="en",
          │             condition_on_previous_text=False, vad_filter=False,
          │             warm-up transcribe at startup)
          ▼
        HallucinationFilter  (Utils/limbs/speech_filters.py)
          │  rejects on no_speech_prob > 0.6, avg_logprob < -1.0,
          │  or short + blacklisted phrase ("thank you", "thanks for watching", ...)
          │  wake words are exempt from the blacklist
          ▼
        SelfEchoFilter  — word-level SequenceMatcher vs queue_manager.recent_tts()
          │  accept / reject (ratio ≥ 0.62 or ≥60 % coverage) / TRIM an echoed block
          ▼
        Lexicon.repair_transcript()  (Utils/limbs/lexicon.py)
          │  names + known mishearings only:  "phonix" → "phoenix"
          ▼
        song rerank — ambiguous song titles get a SECOND STT pass (see §4a)
          ▼
        WakeGate.evaluate()  (Utils/limbs/wake_gate.py)
          │  ignore / acknowledge / respond
          ▼
        PhoenixAssistant.main(query)      ← wake word already stripped
```

### The wake gate — `Utils/limbs/wake_gate.py`

Phoenix boots **dormant**: it transcribes everything but answers nothing. A wake
word anywhere in a sentence wakes it *and answers that same sentence*. It then stays
awake for `audio.followup_window_seconds` (default 30), so follow-ups need no wake
word, and returns to dormant when that expires.

```
            wake word matched (anywhere in the sentence)
 DORMANT ───────────────────────────────────────────────► AWAKE
    ▲       answers THAT sentence, wake word stripped       │
    └───────────────────────────────────────────────────────┘
                 now() >= awake_until   (30 s idle)
```

Wake words come from `core/config.json → profile.<active>.wake_words`. Nothing is
hardcoded, so switching to the `igris` profile switches the wake words with it.

**Why awake is a deadline, not a boolean.** The previous implementation used
`self.loop`, set from `result is not False` — but `PhoenixAssistant.main()` always
returns `True`, so it latched on at the first wake word and never cleared. A deadline
cannot latch: only an arriving utterance can push it forward, so silence expires it
by construction. Same reasoning as the `speaking_since/until` window in §2. Do not
"simplify" this back to a flag.

**Why word boundaries matter.** Matching used to be
`any(w in text.lower() for w in WAKE_WORDS)`. The profile contains `"yo"`, and
`"yo" in "you"` is `True` — so nearly every sentence passed the gate, which is why
Phoenix appeared to answer everything and `[IGNORED_HEARD]` was near-unreachable.

Two behaviours worth knowing:
- Multi-word wake words are sorted longest-first in the alternation. Regex
  alternation is first-match, not longest-match, so without this `"hey phoenix"`
  would match the bare `phoenix` branch and route a dangling `"hey"`.
- `"phoenix folder"` is protected from stripping (`PROTECTED_FOLLOWERS`) — it names
  a directory, and stripping it would route `"open folder"`.

Tested by `tests/test_wake_gate.py` (70 checks, injectable clock — no mic, no sleep).

### Speaker verification — `Utils/limbs/speaker_id.py`

Answers the owner's voice rather than the room. Resemblyzer embeddings (256-d,
~16 ms on this CPU) compared by cosine similarity against an enrolled profile in
`data/speaker_profile.npz`. Enrol with `tests/enroll_voice.py`.

Runs **before** Whisper: 16 ms to reject a stranger instead of 800 ms.

**It is a convenience filter, not a security control.** A recording of the owner
passes it, so does a good impersonation, and accuracy drops with distance and
illness. It exists to stop the TV and other people in the room issuing commands.

**Every uncertainty fails open** — no profile, encoder missing, corrupt profile
file, or an utterance under `min_duration_s` all return `accepted=True`. A voice
assistant that goes deaf because a model file is missing is a worse failure than
one that occasionally answers a guest. `VerificationResult.verifiable` tells a
real acceptance from a fail-open one.

**Ships in `mode: "log"`** — scores every utterance, suppresses nothing. Run it
that way until you have real numbers for yourself and for other people, then set
`threshold` between them and switch to `"gate"`. Picking a cosine threshold by
intuition is how this ends up ignoring its owner.

### <a name="s4a"></a>Vocabulary — `Utils/limbs/lexicon.py` + `data/lexicon.json`

How romanised Hindi/Gujarati words and song titles survive an **English** STT
model. Three layers, because no single one can do it:

| Layer | Where | Size limit | Cost |
|---|---|---|---|
| **Bias** — `hotwords=` on `transcribe()` | before STT | **~20 song titles, hard** | free |
| **Repair** — `repair_transcript()` | after STT | none | ~1 ms |
| **Rerank** — second STT pass | after STT | none | one extra pass |

**The cap is real and is not negotiable.** faster-whisper truncates hotwords at
`max_length // 2` = **223 tokens** (`WhisperModel.get_prompt`). A romanised song
title costs **8.7 tokens** against ~1.3 for an English word, so the bias layer
holds about twenty titles *no matter how large the library grows* — 50 % coverage
at 40 songs, 10 % at 200, 4 % at 500. Do not try to fix this by enlarging the
list; it is silently truncated at the tail.

Since the budget is fixed, the only lever is **which** twenty:
`Lexicon.ranked_songs()` orders by play count (`data/song_stats.json`), so the
bias window follows what is actually listened to.

**The rerank is what makes library size irrelevant.** Retrieval and ranking fail
differently — measured over the real library with synthetic mangling
(`tests/test_lexicon.py::test_candidate_recall`):

| | top-1 correct | correct in top-8 |
|---|---|---|
| light mangling | 92.1 % | **100 %** |
| heavy mangling | 93.3 % | **98.8 %** |

So a full-library fuzzy scan almost always *contains* the answer even when it
ranks it wrong. The second pass exploits that:

```
pass 1    plain transcription
   ▼
retrieve  top 8 candidates from the WHOLE library   (~1 ms, no size limit)
   ▼
pass 2    re-transcribe the same audio, biased to just those 8
```

Eight titles always fit the budget, so the library can grow without bound. It
only runs in the ambiguous band — `score ≥ 88` means pass 1 was right, `< 60`
means it is a new song; neither pays for a second pass.

**`normalize_roman()` folds romanisation variance**, not English spelling:
doubled vowels, aspirates written with a trailing `h`, and the v/w, j/z pairs
that have no settled convention. `sahiba`/`saahibaa`/`sahiwa` collapse to one
key. Double-metaphone and soundex are **wrong** for this corpus — they encode
English orthography, so they split `sahiba` from `saahibaa` while collapsing
`ishq` into `ask`.

**Repair is scoped to `names` only, deliberately.** It once covered command and
Hinglish vocabulary too, and turned "what is the weather today" into
"…weather **thoda**". The STT model is an English model — English command words
are what it already gets right. Those categories still feed the *bias* layer,
where the acoustics still get a vote; rewriting a finished transcript has no
such safety net. Known mishearings (`phonix` → `phoenix`) use the exact
`aliases` map instead, because lowering a fuzzy threshold far enough to catch
`pheonix` also catches words that were never wrong.

> **This is not the fuzzy intent matcher from lesson 1.** Nothing here selects an
> intent, a tool or an action. `repair_transcript` rewrites *words* toward a
> closed lexicon; `resolve_song` matches a *slot value* against a known library
> after the decision to play a song has already been made. Intent selection
> remains exact-alias → grammar → LLM. A change that lets this module decide
> which action runs is reintroducing that bug.

**Two independent self-voice defences** (acoustic gate + text similarity) because
either one alone leaks. There is deliberately **no real AEC** (WebRTC APM / speexdsp);
that needs a WASAPI loopback far-end reference and is a project of its own.

### `audio.echo_mode`

| Value | Meaning |
|---|---|
| `"gate"` (default) | Speakers. Mic gated while Phoenix talks. Barge-in **off** — it would trigger on Phoenix's own voice. |
| `"open"` | Headphones. Gate disabled, true full-duplex, barge-in **on**. |

Barge-in path: listener sets `interrupt_requested` → `SpeechEngine._play_file_interruptible`
polls MCI `status <alias> mode` every 50 ms and issues `stop`. (The old
`play {alias} wait` blocked inside winmm so an interrupt could never be noticed.)

---

## 4. The brain — how a command is routed

Entry point: `Utils/limbs/command_processor.py:PhoenixAssistant.main(sent)`.

```
sent
 ├─ strip wake-word aliases (phoenix|phonix|pheonix|fenix|... except "phoenix folder")
 ├─ "open"/"launch"/"start" → OpenAppHandler.process_query()   [returns immediately]
 ├─ "close"                 → CloseAppHandler.process_query()  [returns immediately]
 └─ IntentRouter.route(query)   ← Utils/limbs/intent_router.py
```

### `IntentRouter.route()` — four stages, cheapest first

| Stage | Cost | What it does |
|---|---|---|
| **0. Exact alias** | 0 ms | `EXACT_ALIASES` dict lookup on normalised text. `DEVICE_ALIASES` (time/date/battery/screenshot/…) + `IDENTITY_ALIASES` (who are you / who am I). A miss is a miss — **no fuzzy fallback by design**. |
| **0a. Continuation** | 0 ms | bare "more"/"again" right after a device change repeats it. Gated on `last_was_device`. |
| **0b. Command grammar** | 0 ms | `_match_command_grammar()` — brightness/volume control. Requires **both** a control verb and a control subject (or a pronoun resolved against `last_device`). Handles increase/decrease/set/reset, `%`, "back to normal", "dim the screen". |
| **1. LLM router** | 1.5–3 s | `AIDecisionMaker.choose_tool()` picks exactly one of five tools. |

Stage 0b tracks state so `"back to normal"` works: `baseline` (absolute hardware level
read before the first change) with `net_delta` as fallback when the hardware level is
unreadable.

### Stage 1 — the five tools (`Utils/limbs/tool_registry.py`)

| Tool | Result kind | Notes |
|---|---|---|
| `get_device_state` | `action` | reads time/date/battery/weather/timers/alarms/reminders/songs. Guarded by `_state_is_plausible()` — a **validator**, it can reject the model's pick but never choose one. |
| `control_device` | `action` | enum of ~40 action tags. `salvage_action()` repairs the common case where a small model returns the verb ("increase") instead of the tag ("adjustBrightness"). |
| `search_web` | `evidence` | `Utils/limbs/web_search.py` → Wikipedia first, then DuckDuckGo (`ddgs`), then a `trafilatura` page fetch only if snippets were thin. |
| `remember` | `memory` | writes to `data/remember.md`. Heavily validated — see §5. |
| `answer_directly` | `direct` | default. Then upgraded to `search_web` if `needs_fresh_data()` sees a volatility marker, or overridden to a device reading if `device_state_for()` matches. |

`lookup_encyclopedia` still exists in `dispatch()` for backward compatibility but is
**deliberately absent from the prompt**: a three-way knowledge split (know-it /
encyclopedia / search) proved too subtle for a 3B router. Two modes only — general vs
realtime — which is what actually works.

**Design rule (important):** the command/question distinction is **not** used for
routing. A question can legitimately need a local tool ("what is the time"). Routing is
decided by *where the answer lives* and *whether it mutates state*.

### The router prompt lives in `core/intents.md`

Only the block between `<!-- PROMPT:BEGIN -->` and `<!-- PROMPT:END -->` is sent to the
model (`load_intent_rules(compact=True)`). Everything below it is reference for humans.

> **Measured on this machine:** a 7,100-char prompt cost **13.1–13.6 s** per decision
> and misrouted "increase brightness by 30%". The ~1,000-char prompt block costs
> **1.5–3.0 s** and routes it correctly. Prompt length is the dominant latency cost.
> Add detail to the reference tables, **not** to the prompt block.

Conversation history is deliberately **excluded** from the router prompt (it made
"my friend moin told me about this" resolve "this" to the previous topic) but **is**
given to the answer model, where follow-ups actually need it.

### Two-model split — `Utils/ai_manager.py`

| Role | Config key | Current | Why |
|---|---|---|---|
| Router | `ai_manager.router_model` | `llama3.2:latest` (2.0 GB) | temperature **0** for determinism, `format: json`, `num_predict: 60` |
| Answer | `ai_manager.answer_model` | `llama3.2:latest` | temperature 0.4, `num_predict: 220` |

`router_mode`:
- `"json"` (current) — rules-driven JSON classification, works with **any** completion model
- `"tools"` — native Ollama function-calling, needs a model reporting the `tools` capability (`gemma3` does **not**)

`keep_alive: "30m"` holds both models resident. `Utils/limbs/ollama_helper.py` wraps
`/api/generate` and `/api/chat` and polls `/api/tags` for readiness on first use.

> **HARDWARE CONSTRAINT — read before blaming prompts.** GTX 1650, **4 GB VRAM**.
> `gemma3:latest` (4.4 GB loaded) runs 45 % on CPU → 8–16 s replies.
> `llama3.2:latest` (2.0 GB) runs ~90 % on GPU → 1–3 s replies.
> If latency is bad, run `ollama ps` and check the CPU/GPU split **first**.
> `gemma4:e2b` (7.2 GB) and `gemma4:latest` (9.6 GB) will not fit.
> Models tagged `:cloud` in `ollama list` are **not offline** — never route to them.

---

## 5. Memory — `Utils/limbs/memory_manager.py`

Three separate stores:

| Store | File | Contents |
|---|---|---|
| `load_soul()` | `core/soul.md` | personality/system prompt. `{assistant_name}`, `{user_name}`, `{user_tags}` substituted from `AppConfig`. |
| `ConversationContext` | `data/ChatLog.json` | rolling window of last `context_turns` (8) turns in RAM; full log persisted up to `max_chatlog_entries` (500). `.search()` does keyword recall across the whole log so "you told me X last week" survives a restart. |
| `RememberStore` | `data/remember.md` | long-term facts under `## People / ## Preferences / ## Facts / ## Projects`. |

`RememberStore.add_fact()` is aggressively defensive because **a fabricated memory
persists and poisons every later answer**. It rejects:

- facts under 3 words, over 200 chars, or opening with a verb/connective (no subject)
- **ungrounded** facts — every content word must appear in the user's original message
  (`_is_grounded`). This exists because the model wrote *"Rohit tells Kaly that he is a
  dragon in the game"* from "my friend rohit told me about this".
- requests misread as facts ("a joke on X", "tell me a story")
- near-duplicates (substring match either direction)

It also auto-refiles anything containing a relationship noun into `## People`.

Deletion: `tool_registry._forget_request()` detects "forget that" / "forget about X" /
"remove what you just remembered" and routes it to `RememberStore.forget()` —
because it was previously routed to `remember` and **added** an entry instead.

`intent_router` never lets the answer model narrate a memory save; it emits a fixed
acknowledgement ("Noted.") because a fixed string cannot lie about what it did.

---

## 6. Directory map

```
Phoenix/
├── main.py                     ENTRY POINT. Rich TUI, text-mode REPL, speech serialiser.
├── core/
│   ├── config.py               AppConfig — class-level singleton, loads config.json at import
│   ├── config.json             THE config file (profiles, models, audio, stt, memory, web)
│   ├── soul.md                 personality prompt
│   ├── intents.md              router rulebook (PROMPT:BEGIN/END block is what ships)
│   ├── launch_phoenix.py       supervisor for the 3 voice subprocesses
│   ├── queue_server.py         IPC hub (named pipe)
│   ├── continuous_listener.py  thin driver over audio_capture
│   └── main_assistant.py       ⚠ LEGACY. Superseded by Utils/limbs/command_processor.py
├── Utils/
│   ├── ai_manager.py           AIDecisionMaker — router + answer models
│   ├── limbs/
│   │   ├── audio_capture.py    MicStream/NoiseFloor/VoiceDetector/Endpointer/EchoGate/CapturePipeline
│   │   ├── speech_filters.py   HallucinationFilter, SelfEchoFilter
│   │   ├── lexicon.py          Hinglish normaliser, song resolver, transcript repair
│   │   ├── speaker_id.py       SpeakerVerifier — owner-voice filter (fails open)
│   │   ├── queue_manager.py    client side of queue_server; AudioChunk dataclass
│   │   ├── assistant_io.py     SpeechEngine (Piper/Edge/pyttsx3), VoiceAssistantGUI, VoiceRecognition(legacy)
│   │   ├── intent_router.py    the 4-stage router
│   │   ├── tool_registry.py    tool schemas + dispatch + validators
│   │   ├── command_processor.py PhoenixAssistant — action_map, the real brain entry
│   │   ├── action_utilities.py ⚠ 3,556 lines / 189 methods. Utility, OpenAppHandler, CloseAppHandler
│   │   ├── time_handlers.py    TimerHandle, AlarmHandle, ReminderHandle, ScheduleHandle (1,280 lines)
│   │   ├── memory_manager.py   soul / ConversationContext / RememberStore
│   │   ├── ollama_helper.py    HTTP wrapper for Ollama
│   │   ├── web_search.py       DuckDuckGo + Wikipedia + trafilatura
│   │   ├── personal_manager.py projects/goals/todos store (data/PersonalManager.json)
│   │   ├── time_runner.py      background alarm/reminder firing
│   │   └── console_ui.py       user_said/phoenix_said/listening print helpers
│   ├── runners/
│   │   ├── manager.py          PhoenixRuntimeManager — thread supervisor, ollama warm-up
│   │   ├── battery_monitor.py  battery threshold announcements
│   │   ├── time_monitor.py     hydration/startup/project reminders
│   │   ├── voice_processor.py  spawns + supervises core/launch_phoenix.py
│   │   └── voice_command_processor.py  STT → filters → brain → TTS  (the busy one)
├── data/
│   ├── intents.json            144 intents / 807 patterns (canned responses + fastpath tags)
│   ├── remember.md             long-term memory  (gitignored)
│   ├── ChatLog.json            conversation log  (gitignored)
│   ├── PersonalManager.json    projects/goals/todos
│   ├── TimeData.json           alarms/timers/reminders/schedules
│   └── songs.txt               song list for playsong/suggestsong
├── voice/                      Piper .onnx voices (gitignored, ~10 voices present)
├── models/piper_voices/        4 more Piper voices (gitignored) — ⚠ duplicate location
├── assets/                     green.png / red.png mic indicator, sound effects
├── tests/                      see §8
├── helpers/                    ⚠ DEAD. Pre-reorg copies of ConsoleUI/QueueManager/Helper.
├── trials/                     ⚠ DEAD. Old experiments (gitignored).
├── bgprogs/                    ⚠ DEAD. BgVoiceProcessorPHNX.pyw.
├── docs/                       analysis/, fixes/, guides/, history/, troubleshooting/
└── .github/                    copilot-instructions.md, AGENT.md, temp-todo-*.md
```

---

## 7. Configuration — `core/config.json`

Loaded once at import time by `core/config.py` into the **class attributes** of
`AppConfig` (not an instance — `AppConfig.name`, `AppConfig.audio[...]`, etc.).
There is **no hot reload**; changing config requires a restart.

| Key | Meaning |
|---|---|
| `active_profile` | index into `profiles` — `0` = phoenix, `1` = igris. Sets name, TTS voice, wake words. |
| `current_mode` | index into `modes` — `0` = voice, `1` = text |
| `tts_engine` | `"piper"` (offline neural) \| `"edge"` (**online**, Microsoft) \| anything else → pyttsx3/SAPI5. **Currently `"local"`, which falls through to SAPI5.** |
| `show_routing` | print `-> tool arg` trace lines in the TUI |
| `ai_manager.router_mode` | `"json"` \| `"tools"` |
| `audio.*` | `echo_mode`, `vad_threshold`, `hangover_ms` (800), `stitch_window_ms` (900 — pause tolerance is the sum of the two), `min_voiced_ms`, `max_utterance_ms` (20 000; must stay well above hangover + stitch or long sentences truncate mid-word), `pre_roll_ms`, `noise_multiplier`, `noise_absolute_min`, `barge_in`, `followup_window_seconds` |
| `stt.*` | `model` (`base.en`), `device` (`auto`→CPU by design, see `_resolve_device` docstring), `beam_size`, `max_no_speech_prob`, `min_avg_logprob` |
| `security.speaker_verification.*` | `enabled`, `mode` (`log` \| `gate` — **stays `log` until calibrated**), `threshold`, `min_duration_s` |
| `memory.*` | `context_turns`, `max_remember_entries`, `persist_chatlog`, `max_chatlog_entries`, `announce_saves` |
| `web.*` | `enabled`, `max_results`, `fetch_timeout_seconds`, `max_context_chars` |
| `bg_progs.*` | toggles for battery/time/todo/hydration background threads (**all currently `false`**) |

**Known config keys that are read but never consumed:** `memory.auto_save`,
`web.enabled`. See `.github/temp-todo-beast-mode.md`.

---

## 8. Running it

```powershell
W:\workplace-1\Phoenix\.venv\Scripts\python.exe W:\workplace-1\Phoenix\main.py
```

Always use **absolute paths** for both the interpreter and the script — relative paths
break `Utils.*` imports depending on cwd.

**Prerequisites:**
- Ollama running with `llama3.2:latest` pulled (`manager.py` tries to `ollama serve` on startup)
- `.venv` with the deps from `pyproject.toml`
- A working microphone (PyAudio)
- `piper.exe` on `.venv/Scripts/` if `tts_engine: "piper"`

**Tests** (no pytest in this venv — run the files directly):

| File | What it covers |
|---|---|
| `tests/test_listener_pipeline.py` | endpointer, echo gate, hallucination filter, self-echo. **These are the regression tests for the 30-second-chunk disaster.** |
| `tests/test_routing.py` | 44-case routing accuracy harness. Needs Ollama up. Reports LLM accuracy, zero-cost resolutions, and effective end-to-end. |
| `tests/test_lexicon.py` | 102 checks — normaliser, song resolution, candidate recall, play-count ranking, and the **negative set proving repair leaves English alone** |
| `tests/test_honesty.py` | 35 checks — `UNKNOWN` sentinel and hedge detection. The "confident answers survive" set is the important half; over-deflection is the failure mode. |
| `tests/test_speaker_id.py` | 32 checks — mostly fail-open paths (missing/corrupt profile, short audio, log mode never suppressing) |
| `tests/enroll_voice.py` | not a test — records ~20 phrases and writes `data/speaker_profile.npz` |
| `tests/unit/`, `tests/integration/`, `tests/experimental/` | mixed vintage, mostly ad-hoc scripts |

All six suites above are offline and run in seconds:

```powershell
W:\workplace-1\Phoenix\.venv\Scripts\python.exe W:\workplace-1\Phoenix\tests\test_lexicon.py
```

---

## 9. Hard-won lessons (do not undo these)

1. **Never fuzzy-match intents.** The old `SequenceMatcher` matcher fired `playsong`
   on a 0.462 tie for "capital of france?". Exact alias table + explicit grammar, or the LLM.
2. **Never fall back to fuzzy matching when the model fails.** A wrong action is worse
   than no action. `route()` returns an error message instead.
3. **The clock/date/battery are authoritative.** `tool_registry.device_state_for()`
   overrides `answer_directly` for these, because the model once answered "August 9th,
   National Women's Day and Islamic New Year" — partly invented.
4. **Never let the answer model narrate a side effect.** Asked to acknowledge "i prefer
   dark mode" it replied *"Dark mode is set, I've adjusted the display"* — it had done
   no such thing.
5. **A question is never a fact to store.** "who is my friend" matched the `my friend`
   trigger and tried to SAVE instead of answering.
6. **Never look up a person the user calls their own.** "my friend rohit" returned the
   cricketer Rohit Sharma.
7. **`temperature=0` for classification.** Ollama defaults to 0.8; the same query routed
   differently between runs.
8. **The mic stream is never paused.** Pausing let the OS capture buffer accumulate
   Phoenix's own TTS and replay it seconds later as user speech.
9. **Gate self-voice on capture timestamp, never on a live boolean.** The same
   applies to the stitch window: it is measured in audio time, not wall clock.
10. **Prompt length, then VRAM fit, are the two latency levers.** In that order for
    prompts, but check `ollama ps` first.
11. **Fuzzy matching is allowed on slot values and words, never on intents.** The
    distinction lesson 1 turns on is *what the match decides*. Matching a word
    against a closed lexicon, or "which of my 40 songs is this", is bounded and
    correctable. Choosing an action is not. See §4a.
12. **Never fuzzy-repair a word the model already gets right.** Scoping repair to
    English command vocabulary turned "the weather today" into "the weather
    thoda". Scope the mechanism; a blocklist of exceptions can never be complete.
13. **Give the answer model a way to decline, and make it a fixed token.**
    "Say you don't know" produces a different sentence every time and half of
    them are a guess wearing a hedge. `UNKNOWN` is detectable, so the router can
    escalate to a web search instead of speaking a shrug. Same reasoning as the
    fixed "Noted." in lesson 4 — a constant string cannot lie.
14. **A fixed-size channel meeting a growing dataset is a design split, not a
    tuning problem.** The hotword budget holds ~20 song titles forever. The fix
    was not a bigger list but noticing that retrieval (99.6 % recall@8) and
    ranking (92.9 % top-1) fail differently, and putting a second pass in the
    gap.
15. **Verification failures must fail open.** Speaker ID sits in front of
    everything; every uncertain branch returns "accepted". Going deaf because a
    model file is missing is worse than answering a guest.

---

## 10. Known state / open work

See **`.github/temp-todo-beast-mode.md`** for the full flaw register and roadmap, and
`.github/temp-todo-listener-rewrite.md` for the listener rewrite (phases 0–4 done,
phase 5 partially done).

Headline items:
- ~~`Utils/plugins/` and `helpers/` are dead code~~ — **resolved 2026-08-11**, both deleted
- ~~`utils/` (lowercase) is a case-duplicate of `Utils/`~~ — **resolved 2026-08-11**, the 32
  stale lowercase paths are out of the git index; the repo clones correctly on Linux/macOS
- ~~~38 stray scripts and stale fix-notes at repo root~~ — **resolved 2026-08-11**
- ~~Wake-word matching is naive substring (`"yo" in "you"` → true)~~ and
  ~~follow-up mode latches on forever~~ — **resolved 2026-08-12**, replaced by
  `Utils/limbs/wake_gate.py` (see §3)
- ~~Phoenix cuts off a slow speaker mid-sentence~~ — **resolved 2026-08-12**,
  continuation stitching (see §3)
- ~~Hindi/Gujarati words and song titles are unrecognisable~~ — **resolved
  2026-08-12**, three-layer lexicon (see §4a)
- ~~The answer model invents rather than admitting ignorance~~ — **resolved
  2026-08-12**, `UNKNOWN` sentinel + hedge detection + web escalation
- ~~Anyone in the room can command Phoenix~~ — **partly resolved 2026-08-12**,
  speaker verification is wired and tested but **ships in `log` mode and nobody
  has enrolled yet**. It does nothing until `tests/enroll_voice.py` is run and
  `mode` is switched to `"gate"`.
- `core/main_assistant.py` is a superseded duplicate of `command_processor.py`
- `tts_engine: "local"` matches no branch and falls through to SAPI5. Per the
  2026-08-12 review that engine is the *wanted* one — but it must be chosen, validated
  and voice-selected by name, not reached by fallthrough. Piper is being dropped.

**Not yet measured, and worth doing before further tuning:**
- Whether biasing toward 8 retrieved candidates actually flips a wrong
  transcription often enough to justify the second pass. The retrieval half is
  measured (99.6 % recall@8); the *effect on Whisper's output* is not.
- Whether `stt.model` should move to multilingual `base`. Same size, same speed,
  slightly worse on English, but it removes the root cause instead of
  compensating for it. Decide from `tests/stt_bench.py` numbers, not argument.
  Note `base.en` is **not** incapable of romanised Hindi — its tokenizer is
  byte-level, so it can spell `sahiba`; it simply has no Hindi acoustics to work
  from and guesses worse.
