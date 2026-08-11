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
          │  close on 600 ms hangover, discard if < 400 ms voiced, hard cap 12 s
          ▼
        Utterance → create_audio_chunk() → queue → processor
```

Then in `Utils/runners/voice_command_processor.py`:

```
        faster-whisper (small.en, CPU int8 by default, cpu_threads=4,
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
        wake-word gate → PhoenixAssistant.main(text)
```

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
│   └── plugins/                ⚠ DEAD CODE. ~3,800 lines, imported by nothing.
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
| `audio.*` | `echo_mode`, `vad_threshold`, `hangover_ms`, `min_voiced_ms`, `max_utterance_ms`, `pre_roll_ms`, `noise_multiplier`, `noise_absolute_min`, `barge_in` |
| `stt.*` | `model` (`small.en`), `device` (`auto`→CPU by design, see `_resolve_device` docstring), `beam_size`, `max_no_speech_prob`, `min_avg_logprob` |
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
| `tests/unit/`, `tests/integration/`, `tests/experimental/` | mixed vintage, mostly ad-hoc scripts |

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
9. **Gate self-voice on capture timestamp, never on a live boolean.**
10. **Prompt length, then VRAM fit, are the two latency levers.** In that order for
    prompts, but check `ollama ps` first.

---

## 10. Known state / open work

See **`.github/temp-todo-beast-mode.md`** for the full flaw register and roadmap, and
`.github/temp-todo-listener-rewrite.md` for the listener rewrite (phases 0–4 done,
phase 5 partially done).

Headline items:
- `Utils/plugins/` (~3,800 lines) and `helpers/` are dead code
- `utils/` (lowercase) is a **case-duplicate** of `Utils/` in git history — repo will not
  clone correctly on Linux/macOS
- `core/main_assistant.py` is a superseded duplicate of `command_processor.py`
- ~38 stray scripts and stale fix-notes at repo root
- `tts_engine: "local"` silently means SAPI5, not Piper
- Wake-word matching is naive substring (`"yo" in "you"` → true)
