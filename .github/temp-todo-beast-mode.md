# Task: Phoenix — "local, offline, perfect" hardening plan
Generated: 2026-08-10
Scope: full-repo audit. **No code changed.** This is the flaw register + roadmap.

Read `README.md` first for the architecture map. This file only lists what is *wrong*
and what to do about it.

---

## Verdict up front

The **listening pipeline and the routing brain are genuinely good** — better than most
hobby assistants. `audio_capture.py`, `speech_filters.py`, `intent_router.py` and
`tool_registry.py` are well-reasoned, well-commented, and each defensive check is
traceable to a real observed failure. That work should not be touched except where
listed below.

The problems are in three other places:

1. **The offline claim is not actually true** — several paths silently reach the internet
   or silently degrade to a worse local engine.
2. **The repo is structurally unsafe** — a case-duplicated package tree, ~3,800 lines of
   dead plugin code, two competing `PhoenixAssistant` classes, 38 stray root scripts.
3. **The action layer never got the same rigour as the listening layer** —
   `action_utilities.py` is 3,556 lines / 189 methods with a 100-entry `action_map`
   duplicated across two files.

---

## SECTION A — Correctness bugs (fix these first)

### [todo-A1] Wake-word matching is naive substring → Phoenix wakes on the word "you"
**File:** `Utils/runners/voice_command_processor.py:215-218`
```python
return any(word in text_lower for word in self.WAKE_WORDS)
```
Configured wake words include `"yo"` and `"baby"`. `"yo" in "you"` → **True**.
`"yo" in "your"` → **True**. So *any* sentence containing "you" or "your" — which is
most sentences — passes the wake gate. The `IGNORED_HEARD` branch is close to unreachable.

**Fix:** word-boundary regex over the normalised transcript, built once at init:
`re.compile(r"\b(" + "|".join(map(re.escape, sorted(WAKE_WORDS, key=len, reverse=True))) + r")\b")`.
Additionally: only accept a wake word in the **first N words** of the utterance, and drop
`"yo"` from the profile (2 letters is not a viable wake word for Whisper output).

### [todo-A2] Follow-up mode latches on forever — no idle timeout
**File:** `Utils/runners/voice_command_processor.py:392-420`
```python
self.loop = True if result is not False else False
```
`PhoenixAssistant.main()` **always returns `True`** (`command_processor.py:354`, plus the
early `return True` on open/close). So `result is not False` is always true, `self.loop`
is set once and never cleared except on an exception. After one wake word Phoenix
responds to every utterance in the room, forever.

**Fix:** two changes.
- `main()` must return a meaningful result (`RouteResult`, or at minimum `False` when the
  router produced `source == "error"` or an empty answer).
- Follow-up mode must expire: `self._loop_until = time.time() + FOLLOWUP_WINDOW_S` (20–30 s),
  refreshed on each successful turn. Config key `audio.followup_window_seconds`.

### [todo-A3] `utils/` and `Utils/` are both tracked — repo is broken on case-sensitive filesystems
**Evidence:** `git ls-files | tr A-Z a-z | sort | uniq -d` returns **32 duplicated paths**.
`git status` currently shows `Utils/limbs/assistant_io.py` **and** `utils/limbs/assistant_io.py`
as separately modified. On Windows these are the same file; on Linux/macOS a clone
produces two divergent packages and imports resolve unpredictably.

**Fix:** `git rm -r --cached utils` (lowercase) in a dedicated commit, verify `Utils/`
survives, then `git config core.ignorecase false` locally to stop it recurring.
**Do this before any other commit** — every commit meanwhile doubles the damage.

### [todo-A4] `.gitignore` inline comments disable the rules they annotate
**File:** `.gitignore`
```
*.wav  # Temporary audio outputs
*.mp3  # Temporary audio outputs
test_*_output.*  # Test output files
```
gitignore has **no inline comment syntax**. These patterns literally match a filename
ending in `# Temporary audio outputs`. Result: `*.wav` and `*.mp3` are **not ignored** —
which is why ~20 test `.wav` files and `data/phoenix_speech_*.mp3` are in the tree.

Also: the entire file content is **duplicated verbatim** (lines 1-50 repeat as 51-100).

**Fix:** move comments to their own lines, dedupe the file, then
`git rm --cached` the audio artefacts already committed.

### [todo-A5] `tts_engine: "local"` silently means SAPI5, not Piper
**Files:** `core/config.json:12`, `Utils/limbs/assistant_io.py:93-94`
```python
self.use_edge_tts  = (self.TTS_ENGINE == "edge") and EDGE_TTS_AVAILABLE
self.use_piper_tts = (self.TTS_ENGINE == "piper")
```
`"local"` matches neither, so it falls through to pyttsx3/SAPI5 — the robotic Windows
voice — even though **14 Piper .onnx voices are installed** (10 in `voice/`, 4 in
`models/piper_voices/`) and `piper.exe` is present in `.venv/Scripts/`.

**Fix:** validate the value at load time in `core/config.py` against
`{"piper", "edge", "sapi5"}`, map `"local"` → `"piper"`, and **log a warning** on an
unknown value instead of silently degrading. Also reconcile the two voice directories
(`_piper_models_dir` points at `voice/`; `models/piper_voices/` is orphaned).

### [todo-A6] `SpeechEngine` reads config into **class attributes** at import time
**File:** `Utils/limbs/assistant_io.py:81-87`
```python
class SpeechEngine:
    from core.config import AppConfig      # import inside class body
    EDGE_VOICE  = AppConfig.voice
    PIPER_VOICE = AppConfig.piper_voice
    TTS_ENGINE  = AppConfig.tts_engine
```
These bind once, at first import, and leak `AppConfig` into the class namespace. Any
future profile switch or config reload cannot affect an already-imported process, and
the three processes that each construct a `SpeechEngine` can disagree.

**Fix:** read from `AppConfig` inside `__init__` (instance attributes).

### [todo-A7] `AIDecisionMaker` opens config with a **relative** path
**File:** `Utils/ai_manager.py:88`  → `config_path: str = "core/config.json"`
Correct only when cwd is the repo root. The processor and listener subprocesses are
launched with an inherited cwd that happens to be right today; `_read_config()` swallows
the failure and returns `{}`, which silently falls back to `DEFAULT_ANSWER_MODEL =
"gemma4:e2b"` — a **7.2 GB model that cannot fit in 4 GB of VRAM**. Silent 10× latency
regression.

**Fix:** resolve relative to `__file__` like `memory_manager.py` already does
(`_BASE = os.path.dirname(os.path.dirname(__file__))`). Better: have `AIDecisionMaker`
read `AppConfig` rather than re-parsing the JSON at all — there are currently **two
independent readers** of `config.json`.

### [todo-A8] Dead config keys
- `memory.auto_save` — parsed in `core/config.py:132`, read nowhere.
- `web.enabled` — parsed, but `tool_registry.dispatch("search_web")` never checks it.
  **This matters for the offline goal**: setting `web.enabled: false` does nothing.

**Fix:** enforce `web.enabled` at the top of the `search_web` branch and in
`needs_fresh_data()`'s upgrade path; delete `memory.auto_save` or wire it.

### [todo-A9] Two `PhoenixAssistant` classes, one obsolete
`core/main_assistant.py` (703 lines) and `Utils/limbs/command_processor.py` (382 lines)
both define `PhoenixAssistant` with a ~100-entry `action_map` that is **copy-pasted
between them**. Only `command_processor.py` is live (it has the `IntentRouter`);
`main_assistant.py` still has the old fuzzy `_get_best_matching_intent` and a broken
`intents.json` path (`core/data/intents.json`, which does not exist).

**Fix:** delete `core/main_assistant.py`. Its only unique content is the ASCII-art banner.

---

## SECTION B — The offline story (this is the headline ask)

Right now Phoenix is **"local-first"**, not offline. Four leaks:

| # | Leak | Where |
|---|---|---|
| B1 | `search_web` → DuckDuckGo, Wikipedia, arbitrary page fetch | `Utils/limbs/web_search.py` |
| B2 | Edge TTS → Microsoft's cloud speech endpoint | `assistant_io.py:_generate_and_play_edge_tts` |
| B3 | `weather` action | `action_utilities.py` |
| B4 | Ollama `:cloud` models are one config typo away | `ollama list` shows 5 of them |

### [todo-B1] Add a hard `offline_mode` switch
New top-level config key `offline_mode: true|false`. When true:
- `search_web` returns `_result("direct")` immediately with a spoken "I can't look that
  up while I'm offline" — **never** silently answers from stale training data pretending
  it looked it up
- `needs_fresh_data()` upgrade path is disabled
- `tts_engine: "edge"` is refused at config-load with a warning, forced to `piper`
- `AIDecisionMaker` refuses any model name containing `:cloud`

This is one boolean that makes the offline claim *auditable* instead of aspirational.

### [todo-B2] Make Piper the default and prove it
Piper is fully offline neural TTS and is already installed. Switch `tts_engine` to
`"piper"`, pick a voice, and delete the Edge path from the default config (keep the code
behind `offline_mode: false`).
Measure: Piper generation is a subprocess round-trip per utterance — benchmark it against
SAPI5 and consider the `piper` **Python API** (`piper-tts` package) to avoid the process
spawn on every sentence.

### [todo-B3] Local knowledge fallback instead of a web search
For the offline case, the honest answer to "what is the population of France" is "I don't
know current figures offline". But a large amount of what `search_web` is used for is
*encyclopedic*, not volatile. Options, cheapest first:
- **Kiwix / ZIM Wikipedia dump** (`libzim` Python bindings) — a 10 GB `wikipedia_en_simple`
  ZIM gives offline Wikipedia lookup with the same interface `wiki_summary()` already has.
  Drop-in replacement for the first branch of `gather_context()`.
- A small local embedding index over `data/` + the ZIM for true RAG (heavier; only if B3a
  proves insufficient).

---

## SECTION C — Architecture changes worth making

### [todo-C1] Collapse the 4-process topology to 2
Today: TUI process → spawns `launch_phoenix.py` → spawns queue_server + listener +
processor. That is four Python interpreters, three of which each import
`action_utilities.py` (3,556 lines), and **three separate `SpeechEngine` instances**
(TUI, runtime manager, processor) that can talk over each other — the queue-server
speaking window is the only thing coordinating them.

The IPC hub exists purely to move numpy arrays and 3 floats between listener and
processor. Those two have no reason to be separate processes: the listener is I/O-bound
in a PyAudio callback, and the processor is GIL-releasing C code (CTranslate2) plus
network I/O (Ollama). **One process with two threads and a `queue.Queue` removes the
named pipe, the pickling, the connection handshake, and the entire class of
"queue server died" failures.**

Proposed:
```
main.py  (TUI + supervisor)
  └─ phoenix_engine.py  (one subprocess, restartable)
       ├─ capture thread   (CapturePipeline)
       ├─ worker thread    (STT → filters → router → action)
       └─ speech thread    (the ONE SpeechEngine, serialised)
```
`speaking_since/until` becomes a plain object with a lock. `EchoGate.state_provider`
already takes a callable, so `audio_capture.py` needs **zero changes**.

This is the single biggest structural win available. Keep `queue_manager.py`'s API shape
so the migration is mechanical.

### [todo-C2] One `SpeechEngine`, one speech queue, process-wide
`main.py:GlobalSpeechWorker` already implements exactly the right pattern (a queue + one
worker thread + blocking `speak()`), but only for the TUI process. `manager.py:__init__`
constructs a *second* `SpeechEngine`, and the processor a *third*. Under C1 this collapses
naturally; if C1 is deferred, at minimum make `SpeechEngine` a module-level singleton.

### [todo-C3] Split `action_utilities.py` (3,556 lines, 189 methods)
This is the last unrefactored monolith and the highest-risk file in the repo. It already
has a natural seam: `Utils/plugins/normal/{apps,browser,desktop,input,media,personal,
system,windows}.py` is a **complete, well-structured decomposition of exactly this
functionality that nobody ever wired up**.

Decide one way or the other:
- **(a)** Adopt the plugin tree: make `Utility` a thin facade that delegates to the plugin
  modules. ~3,800 lines of already-written code stops being dead.
- **(b)** Delete `Utils/plugins/` entirely and split `action_utilities.py` by hand.

Do **not** leave both. Recommend (a) — but audit the plugin code first; it uses
`shell=True` liberally (`plugins/base.py:163`, `plugins/normal/apps.py:189,283`), which
`action_utilities.py` has mostly moved away from.

### [todo-C4] The `action_map` should be data, not a 100-line dict duplicated in two files
`command_processor._execute_action` has a 100-entry dict of lambdas, and
`tool_registry.CONTROL_ACTIONS` has a **hand-maintained list of the same tags**, and
`core/intents.md` documents them **again** in a markdown table. Three sources of truth
that drift.

**Fix:** one registry — a decorator (`@action("adjustVolume", takes_query=True)`) on the
`Utility` methods, from which `CONTROL_ACTIONS`, the dispatch table, and the docs table
are all generated. This also kills the `if tag in [...]` argument-arity lists, which are
currently the most bug-prone lines in the file (`"type_text"` appears in that list but the
tag is `"type"` — a dead entry; `"setTimer"` appears **twice**).

### [todo-C5] `AppConfig` is a mutable class-level singleton loaded at import
`core/config.py:155` calls `AppConfig.load()` at module import. Every consumer does
`from core.config import AppConfig` and reads class attributes. Consequences: no hot
reload, no validation, no way to run two profiles, and test isolation is impossible.

**Fix:** a frozen dataclass built by a `load_config() -> Config` function, passed
explicitly. Keep a module-level `CONFIG` for convenience during migration. Add
**validation with warnings** for: unknown `tts_engine`, unknown `router_mode`, a model
name not present in `ollama list`, `stt.model` not a valid whisper size, `echo_mode`
not in `{gate, open}` (this last one is already done — extend the pattern).

### [todo-C6] Structured trace events instead of `print("[TAG] msg")` parsed by regex
The TUI reads subprocess stdout and string-matches `[VOICE_STATE]`, `[HEARD]`,
`[IGNORED_HEARD]`, `"Phoenix ["`, plus a heuristic filter that drops any line containing
`"|"` or `"---"` (`main.py:298-306`). `manager.py:_handle_voice_log` has a *second,
different* copy of the same parser including emoji matching. Any `print()` anywhere in
3,500 lines of `action_utilities` can corrupt the TUI.

**Fix:** emit one JSON object per line on a dedicated fd (or just `stdout` with a
`@@PHX@@` prefix), parse with `json.loads`. Delete the duplicate parser in `manager.py`.

---

## SECTION D — Latency (the "beast" part)

Current per-turn budget, from the code's own measurements and log traces:

| Stage | Now | Achievable | How |
|---|---|---|---|
| endpoint hangover | 600 ms | 400 ms | tune `hangover_ms`; measure false cuts |
| STT (`small.en`, CPU int8) | ~0.3 s @ rtf 0.15 | ~0.15 s | see D1 |
| router LLM | 1.5–3.0 s | **0 s for ~40 % of turns** | see D2 |
| answer LLM | 1–3 s | 0.5–1.5 s | see D3 |
| TTS first audio | ~0.5–1.5 s | ~0.2 s | see D4 |

### [todo-D1] Revisit the CPU-only STT decision
`_resolve_device` defaults to CPU *by design* ("borrowing VRAM for STT would slow the LLM
down by more than it speeds up transcription"). That reasoning was sound when the answer
model was 4.4 GB. With `llama3.2:latest` at 2.0 GB there is now ~1.5 GB of headroom on a
4 GB card. `small.en` in `int8_float16` is ~250 MB. **Measure it** — set
`stt.device: "cuda"`, run a 20-command soak, and compare `ollama ps` CPU/GPU split before
and after. If the LLM stays ≥90 % GPU, keep CUDA.

### [todo-D2] Grow the zero-cost path
`tests/test_routing.py` already reports "Resolved with no LLM call". Every utterance moved
into Stage 0/0b saves **1.5–3 seconds**. Cheap additions:
- alias-table entries for the top-N utterances observed in `data/ChatLog.json`
  (write a script that mines the log and proposes aliases — the data is already there)
- extend `_match_command_grammar` to cover `open`/`close`/`play` with an app-name
  vocabulary (already implicitly there via `OpenAppHandler`, but it runs *before* the
  router with a crude `"open" in query` substring test that also fires on "open source")
- a normalised-utterance → last-decision cache with a small TTL, so repeated commands
  skip the router entirely

### [todo-D3] Stream the answer model into TTS
Today: `compose_answer` waits for the full completion (`stream: False`), *then* TTS runs,
*then* audio plays. Sentence-level streaming — take the first sentence off the token
stream and start Piper on it while the rest generates — cuts perceived latency roughly in
half. `OllamaHelper.chat` already has the shape for it; needs `stream: True` plus a
sentence splitter feeding the speech queue.

### [todo-D4] Cache TTS for canned responses
`data/intents.json` has 144 intents with fixed `responses`, and `_apply_honorifics`
substitutes from a fixed list. Pre-synthesise the common ones to `.wav` at first use and
key a cache on `hash(text + voice)`. "Yes boss", "Done", "Noted." should be instant.

### [todo-D5] Two models are loaded but they are the same model
`router_model` and `answer_model` are both `llama3.2:latest`, yet `ai_manager` keeps two
separate `OllamaHelper` instances and `manager.py:_warm()` warms both. Harmless today
(Ollama dedupes by model name) but it means the *design* intent — a tiny fast router
(`llama3.2:1b`, already pulled, 1.3 GB) plus a better answerer — is unrealised.
**Try `llama3.2:1b` as the router.** `tests/test_routing.py` will tell you within minutes
whether accuracy holds, and it would free ~700 MB of VRAM.

---

## SECTION E — Repo hygiene

### [todo-E1] Root directory has 38 stray files
`ListenerPHNX.py`, `queue_server.py`, `launch_phoenix.py`, `main_assistant`-era scripts,
`dummy.py`, `fix.py`, `scratch_test.py`, `test_init.py`, `test_init2.py`, `test_voice.py`,
`test_voice2.py`, `clean_empty_files.py`, `reorganize_phoenix.py`, `validate_structure.py`,
plus 9 stale `FIX_*.md` / `*_ANALYSIS.md` notes and `[investigate]alright.md` /
`Untitled-2.md`.

Several are **duplicates of files that already live in `core/` or `scripts/utilities/`**
(`queue_server.py`, `launch_phoenix.py`, `download_piper_voices*.py`). A future reader
cannot tell which is live.

**Fix:** delete the duplicates, move the rest to `scripts/archive/` or `docs/history/`,
`git rm --cached` the tracked logs (`bg_voice_processor.log`, `phoenix_*.log` are in the
tree despite `*.log` being ignored — they were committed before the rule).

### [todo-E2] Dead trees to delete
- `Utils/plugins/` — 3,800 lines, imported only by itself (see C3 for the alternative)
- `helpers/` — `ConsoleUI.py`, `ConsoleUI_new.py`, `HelperPHNX.py`, `QueueManagerPHNX.py`,
  all pre-reorganisation copies
- `bgprogs/BgVoiceProcessorPHNX.pyw`
- `trials/` (already gitignored, 400+ lines of old experiments)
- `tests/*.wav` (~20 files), `tests/piper_models/`, `tests/coqui_output/`

### [todo-E3] Two dependency manifests that disagree
`pyproject.toml` (60 deps) and `Requirements.txt` (25 deps) list different things.
`pyproject.toml` includes `cohere`, `groq`, `selenium`, `Flask`, `PyQt5`, `pywhatkit`,
`googlesearch-python`, `mtranslate` — **none of which are imported anywhere in `Utils/`
or `core/`**. `Requirements.txt` includes `torch` (a 2 GB CPU-only wheel used solely by a
`cuda_available` probe that `_resolve_device` no longer relies on).

**Fix:** `pyproject.toml` is the single source of truth. Prune it to what is actually
imported (`grep -rhoP '^\s*(?:import|from)\s+\K[\w.]+'` and diff), delete
`Requirements.txt`. Dropping `torch` alone removes ~2 GB from a fresh install.

### [todo-E4] `.python-version` says 3.14.0
`pyproject.toml` says `requires-python = ">=3.10"`. Python 3.14 is very new for this
dependency set — `pyaudio`, `webrtcvad`, `PyQt5==5.15.11` and `pywin32` are the usual
casualties. Confirm the venv actually resolved on 3.14, and pin a tested floor/ceiling
(`>=3.11,<3.13`) if not.

### [todo-E5] License mismatch
`pyproject.toml` → `MIT`. `LICENSE` file → Apache 2.0. Pick one.

### [todo-E6] Logging is configured three different ways
- `main.py:_configure_logging()` strips root handlers, writes `logs/phoenix.log`
- `continuous_listener.py:33` `basicConfig` → `phoenix_listener.log` (**repo root**, not `logs/`)
- `voice_command_processor.py:23` `basicConfig(level=DEBUG)` → `bg_voice_processor.log` (**repo root**)
- `queue_manager.py:17` its own `FileHandler("phoenix_queue.log")` (**repo root**) with
  `propagate = False`

Four log files, three in the wrong directory, one at DEBUG in production. Under C1 most of
this collapses; short of that, one `setup_logging(name)` helper used everywhere.

---

## SECTION F — Testing gaps

`tests/test_listener_pipeline.py` (4 tests) and `tests/test_routing.py` (44 cases) are the
only real tests, and neither runs under a test runner (`pytest` is declared as a dev dep
but not installed).

### [todo-F1] Make the suite runnable
`uv sync --extra dev`, convert `test_routing.py`'s `main()` into a pytest test marked
`@pytest.mark.slow` (it needs Ollama), and add `pytest.ini` with markers.

### [todo-F2] Missing coverage, in priority order
| Target | Why it matters |
|---|---|
| `RememberStore.add_fact` / `.forget` | every rejection rule in it exists because of a real fabricated memory. Zero tests. |
| `intent_router._match_command_grammar` | the most intricate pure function in the repo — pronoun resolution, reset detection, residual-empty logic. Pure input→output, trivially testable, **zero tests**. |
| `tool_registry.salvage_action` / `_forget_request` / `needs_fresh_data` | pure functions, all validators, all untested |
| `has_wake_word` | would have caught A1 immediately |
| `core/config.py:load` | index-based `modes`/`profiles` parsing with several silent fallbacks |

### [todo-F3] The soak test from the listener plan (`todo-5.5`) was never run
"Silent room for 10 minutes must produce **zero** transcripts; 20 spoken commands must
produce 20 utterances of 1-5 s each." Run it and record the numbers in
`.github/temp-todo-listener-rewrite.md`. Without it, "the listener is fixed" is a claim,
not a measurement.

---

## SECTION G — Security review (the workflow requires 10/10)

Current honest rating: **6/10.** Nothing is remotely exploitable today because everything
runs locally under the user's own account, but the input path is *speech from a room*,
which is not fully trusted, and the action layer executes shell commands.

| # | Issue | Where | Severity |
|---|---|---|---|
| G1 | `subprocess.Popen(details["launch"], shell=True)` with a value from a data file | `action_utilities.py:3239` | med |
| G2 | `subprocess.Popen(app_name)` where `app_name` derives from a transcript | `action_utilities.py:176` | med |
| G3 | `os.system("shutdown /s")`, `taskkill /F /IM python.exe` reachable from a voice command with **no confirmation** | `action_utilities.py:2422`, `plugins/normal/system.py:240` | high (destructive, not exploitable) |
| G4 | `plugins/base.py:163` generic `run_async(command, shell=True)` | dead code, but it is a shell-injection primitive sitting in the tree | med |
| G5 | `launch_phoenix.py:111` builds a PowerShell command via string interpolation and `shell=True` | `_cleanup_stale_processes` | low |
| G6 | `type_text` / `press_key` drive the keyboard from transcribed audio | `action_utilities.py` | med |
| G7 | Named-pipe authkey `b"phoenix_audio_queue"` is a hardcoded constant in two files | `queue_server.py`, `queue_manager.py` | low (local pipe, but any local process can connect and inject audio chunks / force `speaking_until` high to deafen the mic) |

**Fixes:**
- G1/G2/G4: never `shell=True`; pass argv lists. Validate app names against the known
  app registry before spawning.
- G3: a `destructive_actions` confirmation gate — `pcshutdown`, `pcrestart`, `pchibernate`,
  `closeallpy`, `closebgpy` must require an explicit spoken confirmation turn. Config key
  `confirm_destructive: true`.
- G6: gate `type`/`press` behind the same confirmation, or a config toggle defaulting off.
- G7: generate the authkey at launcher startup, pass it to children via env var.

---

## Recommended order of work

**Phase 1 — stop the bleeding (half a day, no architecture risk)**
A3 (case-duplicate git tree — do this first, alone, in its own commit) → A4 → A1 → A2 →
A7 → A5 → A8

**Phase 2 — make "offline" true (one day)**
B1 → B2 → G3 → then measure D1 and D5 with `tests/test_routing.py`

**Phase 3 — hygiene (one day, mostly deletion)**
E1 → E2 → E3 → A9 → E6 → F1/F2

**Phase 4 — architecture (multi-day, do only after Phases 1-3 land and tests exist)**
C1 (4 processes → 2) → C2 → C6 → C4 → C3

**Phase 5 — speed**
D3 (streaming TTS) → D2 (grow zero-cost path) → D4 (TTS cache)

**Phase 6 — offline knowledge**
B3 (Kiwix/ZIM Wikipedia)

---

## Progress Notes
- 2026-08-10: audit complete, nothing implemented. `README.md` rewritten as the
  project map so future sessions do not need to re-read the source.
- Deliberately NOT recommending: real acoustic echo cancellation (see the note at the
  bottom of `temp-todo-listener-rewrite.md`), and a rewrite of the routing brain — that
  layer is the strongest part of the codebase and should be left alone.
