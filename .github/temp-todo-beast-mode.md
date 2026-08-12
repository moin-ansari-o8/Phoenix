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

## LOCKED DECISIONS — 2026-08-12 (user review of this plan)

These override anything written below them. Where a todo contradicts this block, this
block wins.

### D-1. TTS: SAPI5 (Zira) is the engine. **Piper is dropped.**
Piper was evaluated on the real machine and rejected: per-utterance `.wav` generation via
subprocess round-trip is too slow, and output was intermittently glitchy. SAPI5 `Zira` is
fast, always resident, and judged good enough. Consequences:
- `tts_engine: "local"` stops being a silent fallback and becomes the **documented,
  validated, default** value meaning SAPI5. See revised [todo-A5].
- ~~[todo-B2] "make Piper the default and prove it"~~ — **CANCELLED.** Inverted into
  "delete the Piper path".
- `voice/*.onnx` (~121 MB) and `piper_voice` config keys become dead weight — remove.
- The **latency argument for Piper is gone, but the streaming argument is not** — see D-4.

### D-2. Wake word: dormant-by-default with a config-driven wake gate
Exact behaviour the user asked for:
- Phoenix boots **dormant**. It transcribes continuously but **does not respond**.
- If a wake word appears **anywhere in a sentence**, it wakes **and answers that same
  sentence** (wake word stripped, remainder routed). Not "wake, then wait for a command".
- After answering it stays **awake** — no wake word needed for follow-ups.
- **30 s of silence → back to dormant.** Timer refreshes on every answered turn.
- Wake words are read from `core/config.json → profile.<active>.wake_words`.
  **Nothing hardcoded**, so switching to the `igris` profile switches the wake words.

### D-3. Offline mode is **auto-detected**, not just a manual switch
`offline_mode: "auto" | true | false`. In `"auto"` Phoenix probes reachability at startup
and on each web-tool attempt, and transparently behaves as fully offline when there is no
connection — rather than hanging on a DNS timeout. See revised [todo-B1].

### D-4. Streaming answer → speech: **keep, retargeted to SAPI5**
[todo-D3] survives the Piper cancellation. Speaking sentence 1 while sentence 3 is still
generating is engine-independent; it feeds `GlobalSpeechWorker`'s queue instead of Piper.
This is the single biggest perceived-latency win left.

### D-5. TUI: one restrained palette, light + dark, toggled from config
New task [todo-C7]. Design brief in the user's words: *futuristic, modern, yet peaceful —
not attention-grabbing, but beautiful and well contrasted.* **No rainbow colours.**
Consistency matters more than variety. Light/dark selectable from `core/config.json`.

### D-6. Confirmed as-is
- [todo-D5] try `llama3.2:1b` as the router — wanted, "2× faster possibly".
- [todo-B3] offline Wikipedia via ZIM — wanted ("loved phase 6").
- [todo-A3] case-duplicate `utils/` — **DONE**, `git ls-files` duplicates now 0.

---

## SECTION A — Correctness bugs (fix these first)

### ~~[todo-A1]~~ Wake-word matching is naive substring — **DONE 2026-08-12**
Implemented in `Utils/limbs/wake_gate.py` together with A2 (they are one state machine).
70 checks in `tests/test_wake_gate.py`, all passing. Notes below kept for the rationale.
**File:** `Utils/runners/voice_command_processor.py:215-218`
```python
return any(word in text_lower for word in self.WAKE_WORDS)
```
Configured wake words include `"yo"` and `"baby"`. `"yo" in "you"` → **True**.
`"yo" in "your"` → **True**. So *any* sentence containing "you" or "your" — which is
most sentences — passes the wake gate. The `IGNORED_HEARD` branch is close to unreachable.

**Fix (revised per D-2):** word-boundary regex over the normalised transcript, compiled
once at init from `AppConfig.wake_words` — longest-first so `"hey phoenix"` wins over
`"phoenix"`:
```python
self._wake_re = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in
                      sorted(self.WAKE_WORDS, key=len, reverse=True)) + r")\b"
)
```
Word-boundary matching alone kills the reported bug: `\byo\b` no longer matches "you" or
"your". So `"yo"`/`"yoi"` may stay in the profile — but they remain the weakest entries
(Whisper renders a lot of filler as "yo"), and dropping them costs nothing.

**Do NOT restrict the wake word to the first N words** — the original note suggested that,
but D-2 explicitly wants "when I say that word *in a sentence*". Match anywhere; strip the
matched span; route the remainder.

**Edge case that must be handled:** if the remainder after stripping is empty (the user
said just "phoenix"), do **not** route an empty query — acknowledge and go awake, so the
next sentence is answered without a wake word.

### ~~[todo-A2]~~ Follow-up mode latches on forever — **DONE 2026-08-12**
Shipped with A1 in `Utils/limbs/wake_gate.py`. `self.loop` is gone from the processor;
`_awake_until` is a deadline. Config key `audio.followup_window_seconds: 30` added to
both `core/config.py` and `core/config.json`.

**Also fixed while in there (not in the original register):**
`command_processor.remove_phoenix_except_folder` was broken twice — its alias list was
hardcoded to "phoenix" (so under the `igris` profile the wake word was never stripped and
got routed as part of the query), and its word-boundary guards were written `(?<!\\w)`
inside a **raw** f-string, which compiles to a lookbehind for a literal backslash followed
by `w` — a condition that is essentially always true, so no boundary was ever enforced.
It now delegates to `WakeGate.strip_wake`.

**File:** `Utils/runners/voice_command_processor.py:392-420`
```python
self.loop = True if result is not False else False
```
`PhoenixAssistant.main()` **always returns `True`** (`command_processor.py:354`, plus the
early `return True` on open/close). So `result is not False` is always true, `self.loop`
is set once and never cleared except on an exception. After one wake word Phoenix
responds to every utterance in the room, forever.

**Fix (revised per D-2):** A1 and A2 are one feature — a two-state machine. Implement them
together.

```
            wake word matched (anywhere in sentence)
   DORMANT ─────────────────────────────────────────► AWAKE
      ▲     answers THAT sentence (wake word stripped)   │
      │                                                  │
      └──────────────────────────────────────────────────┘
              awake_until < now()   (30 s idle)
```

- `AWAKE` is a **deadline, not a boolean**: `self._awake_until: float`.
  `is_awake` is a property → `time.time() < self._awake_until`. A boolean is exactly what
  latched forever; a deadline cannot latch. (Same reasoning as `speaking_since/until` in
  `queue_server.py` — see README §2.)
- Refresh `self._awake_until = time.time() + AppConfig.followup_window_seconds` on **every
  answered turn**, whether it was wake-word-triggered or a follow-up.
- New config key `audio.followup_window_seconds: 30` (D-2 specifies 30).
- `main()` must still return a meaningful result so an errored turn does not refresh the
  window — return `False` when the router produced `source == "error"` or an empty answer.
- **In DORMANT, transcription still runs** (it must, to detect the wake word) but nothing
  is routed, nothing is spoken, and the TUI shows it as `[IGNORED_HEARD]` — which finally
  makes that existing branch reachable.
- Log the transition both ways so the user can see state in the TUI: `[VOICE_STATE] awake`
  / `[VOICE_STATE] dormant`.

### [todo-A3] `utils/` and `Utils/` are both tracked — repo is broken on case-sensitive filesystems
**Evidence:** `git ls-files | tr A-Z a-z | sort | uniq -d` returns **32 duplicated paths**.
`git status` currently shows `Utils/limbs/assistant_io.py` **and** `utils/limbs/assistant_io.py`
as separately modified. On Windows these are the same file; on Linux/macOS a clone
produces two divergent packages and imports resolve unpredictably.

**Fix:** `git rm -r --cached utils` (lowercase) in a dedicated commit, verify `Utils/`
survives, then `git config core.ignorecase false` locally to stop it recurring.
**Do this before any other commit** — every commit meanwhile doubles the damage.

### ~~[todo-A4]~~ `.gitignore` inline comments — **DONE 2026-08-12**
File rewritten (comments on their own lines, de-duplicated) and the 4 remaining
tracked-but-ignored files (`voice/*.onnx`, 121 MB) untracked with `git rm --cached`.
`git ls-files -i -c --exclude-standard` now returns 0. Files remain on disk.
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

### [todo-A5] `tts_engine: "local"` matches nothing and falls through — right engine, by accident
**Files:** `core/config.json:12`, `Utils/limbs/assistant_io.py:93-94`
```python
self.use_edge_tts  = (self.TTS_ENGINE == "edge") and EDGE_TTS_AVAILABLE
self.use_piper_tts = (self.TTS_ENGINE == "piper")
```
`"local"` matches neither branch, so it falls through to pyttsx3/SAPI5. The bug is not
*which* engine you end up on — per D-1 that turned out to be the desired one — it is that
the config value is **unvalidated and undocumented**, so the engine in use is an accident
of control flow rather than a choice. Any typo in `tts_engine` produces the same silent
fallthrough with no warning.

**Fix (revised per D-1 — the conclusion inverts, the bug does not):**
The user tested both and **chose SAPI5/Zira**. So `"local"` is the *right* engine — it was
just arriving there by accident, through a fallthrough, which is why nobody knew which
voice they were getting or could change it deliberately.

Make it explicit:
1. Validate `tts_engine` at load time in `core/config.py` against `{"sapi5", "edge"}`,
   accepting `"local"` as an alias for `"sapi5"`. **Warn** on an unknown value instead of
   silently degrading.
2. **Select the voice by name, not index.** `fallback_voice_index: 1` is machine-dependent
   — SAPI voice ordering is a registry enumeration and differs per install, so this silently
   picks a different voice on any other PC. Add `sapi_voice: "Zira"` to the profile and
   match case-insensitively against `voice.name`, falling back to the index only if no
   name matches.
3. `_speak_pyttsx3` calls `pyttsx3.init("sapi5")` **on every utterance**
   (`assistant_io.py:504`) — a COM init per sentence. Build the engine once. This is
   probably a meaningful chunk of the "TTS first audio" budget in the Section D table.

**Delete the Piper path** (D-1):
- remove `use_piper_tts`, `_piper_models_dir`, the `.onnx` lookup and the subprocess call
- remove `piper_voice` from both profiles in `core/config.json`
- delete `voice/` (~121 MB, already gitignored — and already excluded from history by the
  pending filter-repo run)
- drop `piper-tts` / `piper-phonemize` from `pyproject.toml` (folds into [todo-E3])

Keep the **Edge TTS** path — it is the only thing `offline_mode: false` would buy back, and
it is already gated. It just must never be the default.

### ~~[todo-A6]~~ `SpeechEngine` class-attribute config — **DONE 2026-08-12** (with A5)
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

### ~~[todo-A7]~~ `AIDecisionMaker` relative config path — **DONE 2026-08-12**
Resolved against `__file__` via `_BASE`. Verified by constructing it from `C:/`.
`DEFAULT_ANSWER_MODEL` also changed `gemma4:e2b` (7.2 GB, cannot fit) ->
`llama3.2:latest`, and a missing config now warns on stdout instead of silently
swapping the brain.
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

### ~~[todo-A8]~~ Dead config keys — **DONE 2026-08-12**
`web.enabled` enforced at all three network call sites (`search_web`,
`lookup_encyclopedia`, and the `answer_directly -> search_web` upgrade) via
`tool_registry.web_allowed()`. `memory.auto_save` deleted - `persist_chatlog`
already governed that behaviour. Covered by `tests/test_web_gate.py` (11 checks,
which monkeypatch the network helpers to raise if touched).
- `memory.auto_save` — parsed in `core/config.py:132`, read nowhere.
- `web.enabled` — parsed, but `tool_registry.dispatch("search_web")` never checks it.
  **This matters for the offline goal**: setting `web.enabled: false` does nothing.

**Fix:** enforce `web.enabled` at the top of the `search_web` branch and in
`needs_fresh_data()`'s upgrade path; delete `memory.auto_save` or wire it.

### ~~[todo-A9]~~ Two `PhoenixAssistant` classes — **DONE 2026-08-12**
`core/main_assistant.py` deleted. Verified first that `main_assistant` appears nowhere as
an import - only as a window-title string in `get_window("main_assistant.py")` calls,
which were already stale since the entry point became `main.py`.
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

### ~~[todo-B1]~~ `offline_mode` with auto-detection — **DONE 2026-08-12**
`Utils/limbs/connectivity.py`. 1 s TCP connect to 1.1.1.1:53 / 8.8.8.8:53, cached 30 s
when up and 5 s when down. Measured 0.06 s on this machine. `:cloud` model names now warn
at config load. Covered by `tests/test_offline_mode.py`. Original spec kept below.
New top-level config key `offline_mode: "auto" | true | false`, default `"auto"`.

**Resolution:**
- `true`  → always offline, never probe
- `false` → always allow network (today's behaviour)
- `"auto"` → a `ConnectivityMonitor` decides. Probe = a **1-second TCP connect to
  `1.1.1.1:53`**, not an HTTP GET — no DNS dependency, no payload, fails fast. Result
  cached ~30 s so a turn never pays for it twice. Re-probed on demand before any web tool
  runs, so unplugging the cable takes effect on the next command, not the next restart.

**When resolved-offline:**
- `search_web` returns `_result("direct")` immediately with a spoken "I can't look that up
  while I'm offline" — it must **never** silently answer from stale training data while
  pretending it searched. This is the whole point of the switch.
- `needs_fresh_data()` upgrade path is disabled
- `tts_engine: "edge"` falls back to `sapi5` with a warning (per D-1, `sapi5` is already
  the default, so this is only a guard)
- `AIDecisionMaker` refuses any model name containing `:cloud` — `ollama list` currently
  shows 5 of them, one config typo away from a silent network dependency
- the TUI shows an **offline indicator** (ties into [todo-C7])

**Why auto beats a manual boolean here:** the failure the user actually hits is not
"I forgot to flip the flag", it is *Phoenix hanging for 8 seconds on a socket timeout when
the wifi is down.* `fetch_timeout_seconds: 8` plus DuckDuckGo plus Wikipedia is a
potential ~20 s stall on a single question. Auto-detect turns that into an instant,
honest answer.

### ~~[todo-B2] Make Piper the default~~ — **CANCELLED 2026-08-12 (D-1)**
Inverted. Piper is being **deleted**, not promoted; SAPI5/Zira is the chosen engine after
real-machine testing (too slow, occasionally glitchy). The removal work now lives in the
revised [todo-A5]. Nothing else in this plan depends on Piper except [todo-D3], which was
retargeted rather than cancelled (D-4).

### ~~[todo-B3]~~ Offline encyclopedia — **DONE 2026-08-12**

`Utils/limbs/offline_wiki.py`, reading a Kiwix ZIM from `data/zim/`. Title lookup first
(faster and far more accurate than relevance ranking), full-text search as fallback,
redirects followed, markup and `[1]`/`[edit]` markers stripped - what comes back is prose
meant to be spoken, so nothing may reach the speech engine as HTML.

Wired into `tool_registry` in two places:
- before refusing a blocked lookup, so being offline stops being a dead end for settled facts
- before the web for `lookup_encyclopedia` (`prefer_offline_encyclopedia`, default true),
  since a disk read beats a network round trip and a missing article falls straight
  through - worst case is exactly the old behaviour

Archive chosen: **`wikipedia_en_simple_all_mini`, ~450 MB**. It holds lead paragraphs, and
a voice assistant speaks one or two sentences - downloading 3.2 GB of full text and images
to read out thirty words of it is mostly wasted disk. Swap in `_nopic` (940 MB, full text)
by dropping it in the same directory; the largest archive present wins.

A missing or corrupt archive is never an error - it just means no local lookup.

**Verified against the real 468.6 MB archive (394,552 articles), and it found four bugs
that every unit test had passed straight through:**

1. **Phoenix would have read a CSS stylesheet aloud.** The first thing the archive
   returned for "Mahatma Gandhi" was `.mw-parser-output .infobox-subbox{padding:0;
   border:none...}`. Stripping tags leaves the *contents* of `<style>` as text, and
   Wikipedia ships per-article CSS inline - so this was the normal case, not an edge one.
2. **Infoboxes read as a list of disconnected nouns** - "India" began "Flag State Emblem
   Motto: ... Anthem:", the Moon began "Apparent magnitude -2.5 to -12.9".
3. **Short articles ran into the Creative Commons footer** and would have spoken it.
4. **Hatnotes** - "This article is about Earth's moon. For moons in general, see..."

Fixed by extracting the first real `<p>` rather than flattening the page and slicing, with
an `_is_prose` check that rejects hatnotes, boilerplate, and infobox residue (a table has
almost no function words, so the connective-word ratio separates it from a sentence).
A first attempt at de-duplicating the repeated title also ate Ada Lovelace's name, which
the paragraph approach fixes for free. Each is now a regression test.

Measured end-to-end with `web.enabled: false`: **2-21 ms** per lookup.

**The archive is used while ONLINE too, and the line is drawn by volatility.** As first
written it was only consulted from `_refuse_web`, so with working wifi the 468 MB sat
unused - and `prefer_offline_encyclopedia` guarded the `lookup_encyclopedia` branch, which
the router never selects (that tool is deliberately not exposed to it; see the NOTE above
the schemas). The live path is `search_web`, which now splits on `needs_fresh_data()`:

```
LOCAL   62.7 ms  who was mahatma gandhi
LOCAL    2.0 ms  what is photosynthesis
LOCAL    1.0 ms  ada lovelace
WEB              who is the current prime minister of india
WEB              what is the price of bitcoin
WEB              latest python version
```

Only those three reached the network. The volatility check is the right line and it
already existed: the ZIM is a dated snapshot, so answering "who is the current prime
minister" from it would be confident and wrong - the exact failure `needs_fresh_data`
was written to prevent. A settled fact the archive lacks falls through to the web, so the
worst case is the old behaviour.

### (original note) [todo-B3]
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

### ~~[todo-C2]~~ One `SpeechEngine` per process — **DONE 2026-08-12**
`SpeechEngine.shared()`, a locked lazy singleton. `PhoenixRuntimeManager.__init__` built
one that `AdvancedTUIManager` then replaced with a proxy, so the TUI process paid a COM
init plus a SAPI voice enumeration - measured **306 ms** - for an engine it never spoke
through. Safe to share across threads because the SAPI handle itself is already
per-thread (see `_get_sapi_engine`); only the configuration is shared. The two remaining
bare constructions are in `__main__` demo blocks, not live paths.

### (original note) [todo-C2] One `SpeechEngine`, one speech queue, process-wide
`main.py:GlobalSpeechWorker` already implements exactly the right pattern (a queue + one
worker thread + blocking `speak()`), but only for the TUI process. `manager.py:__init__`
constructs a *second* `SpeechEngine`, and the processor a *third*. Under C1 this collapses
naturally; if C1 is deferred, at minimum make `SpeechEngine` a module-level singleton.

### [todo-C3] Split `action_utilities.py` (3,556 lines, 190 methods)
This is the last unrefactored monolith and the highest-risk file in the repo.

**DECIDED 2026-08-11: option (b). `Utils/plugins/` has been deleted** (commit removing
14 files / 3,917 lines). Do not plan around adopting it — the code no longer exists.

The original note recommended (a), adopting the plugin tree as a ready-made
decomposition, on the grounds that it was "complete, well-structured ... that nobody
ever wired up". That recommendation was audited before deleting and no longer held:

| | `action_utilities.py` | `Utils/plugins/` (deleted) |
|---|---|---|
| methods | 190 | 187 |
| last real change | 2026-08-11 | 2026-04-20 |
| `shell=True` sites | 1 | 4 |
| ever executed | yes, in production | no, imported by nothing |

Since the plugin tree was last touched, `action_utilities.py` took 3 commits and
+306/−11 lines, including `set_echo_mode` (which the listener's echo-mode switching
depends on) with no plugin equivalent. Its only commit since April was a mechanical
`Utils` capitalisation pass. So (a) was not "wire up 3,800 finished lines" — it was
port 4 months of drift, remove 4 `shell=True` call sites, and re-test 187 methods that
had never run once, to arrive where the live code already was. The gap would only widen
with each further change to `action_utilities.py`.

**The split itself still stands as a task** — a 3,556-line file with 190 methods is
worth decomposing. Do it by hand from the live code, keeping the same seam the plugin
tree used (apps / browser / desktop / information / input / media / personal / system /
windows). Recover the deleted tree from git history if it is useful as a layout
reference, but treat it as a sketch, not a source.

### ~~[todo-C4]~~ Action dispatch as data — **DONE 2026-08-12**

`Utils/limbs/action_registry.py`. Arity now comes from `inspect.signature` on the callable
about to be invoked, so it cannot disagree with itself. The four hand-written tag lists in
`_execute_action` are gone.

**Those lists had been hiding four completely broken actions.** The audit spotted
`"type_text"` (not a tag - the real one is `"type"`) and a duplicated `"setTimer"`;
introspecting every entry found the true damage:

| tag | needs | dispatch sent |
|---|---|---|
| `type` | query | nothing |
| `press` | query | nothing |
| `addsong` | query | nothing |
| `play-game` | query | nothing |

Each raised `TypeError` on **every** invocation, which the handler caught and reported as
"Sorry, I encountered an error performing that action." Nothing crashed and nothing was
logged as a defect, so "type hello world" had simply never worked. `"open"`, `"select"`,
`"forward"` and `"backward"` also had dispatch arms for tags that are not in `action_map`
at all - dead branches.

`tests/test_action_registry.py` builds the real `action_map` and asserts every entry can
be called with what dispatch would send, plus a guard that fails if a hand-written arity
list ever reappears.

**Deliberately NOT done:** generating `CONTROL_ACTIONS` from `action_map`. That list is
the enum the router sees, and widening it from 41 to 64 tags would change routing accuracy
- a behaviour change that needs a live test session, not a refactor.

### (original note) [todo-C4]
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

### ~~[todo-C6]~~ Structured trace events — **DONE 2026-08-12**
`core/trace.py`. Events are now `@@PHX@@{"event": "heard", "text": "..."}` - a line either
carries the sentinel and is an event, or it is ordinary output. No guessing, so a stray
`print()` in 3,500 lines of action code can no longer be mistaken for a UI event, and the
"drop any line containing | or ---" heuristic is no longer load-bearing.

Both parsers now share one dispatch shape, and `tests/test_trace.py` asserts that every
event the processor emits is handled by **both** UIs. **That test immediately found three
unhandled events** - `speaker`, `repaired` and `song_rerank`, from the parallel
voice-upgrade work - which neither UI rendered at all. Exactly the drift C6 exists to
prevent: `manager.py` had already been matching emoji prefixes that no longer existed.

Most of the test file asserts the negative property, since that is the one that failed
before: tracebacks, table rows, old-style `[TAG]` lines, bare JSON and a transcript
containing the literal text `[VOICE_STATE]` must all parse as None.

### (original note) [todo-C6] Structured trace events
The TUI reads subprocess stdout and string-matches `[VOICE_STATE]`, `[HEARD]`,
`[IGNORED_HEARD]`, `"Phoenix ["`, plus a heuristic filter that drops any line containing
`"|"` or `"---"` (`main.py:298-306`). `manager.py:_handle_voice_log` has a *second,
different* copy of the same parser including emoji matching. Any `print()` anywhere in
3,500 lines of `action_utilities` can corrupt the TUI.

**Fix:** emit one JSON object per line on a dedicated fd (or just `stdout` with a
`@@PHX@@` prefix), parse with `json.loads`. Delete the duplicate parser in `manager.py`.

### ~~[todo-C7]~~ TUI redesign — **DONE 2026-08-12**

`core/theme.py`. One accent hue (blue) plus a grey ramp, light + dark, selected by
`ui.theme` in config.json (`"auto"` reads the Windows apps-light-theme registry value).

**Measured, not eyeballed.** Every text colour is >= WCAG AA (4.5:1) against its
background in both themes; `tests/test_theme.py` computes the ratios. The natural next
step down the dark ramp (`#6e7681`) came out at 4.12:1, so the ramp bends there - that
colour carries timestamps and ignored speech, which are quiet but not optional.

**What actually changed on screen:**
- the header: name in the accent, then user and `stt / llm / tts`, then one hairline
  rule. The old two heavy bold-magenta bars were the loudest thing on screen and carried
  no information; what replaced them carries which engines are actually loaded.
- ignored speech moved from **yellow to the same quiet grey as other secondary text**.
  Yellow made every cough and passing conversation look like a warning.
- every inline style in `main.py` is gone; all six hardcoded hues are now semantic names.
- emoji removed from `manager.py` and `console_ui.py` per the project's own no-emoji rule.

**Two guards keep it from drifting back**, because the rainbow was never a decision -
it grew one defensible inline colour at a time:
- `test_no_inline_colours` fails if a colour literal reappears in `main.py`
- `test_every_used_style_is_defined` fails if a style name is used but never named
- and ANSI colour names are banned outright: every terminal remaps `bright_blue`, so a
  palette built on them cannot be verified across machines

**Bug found while testing:** `U+2500` and `U+00B7` raise `UnicodeEncodeError` on a
cp1252 console, which kills the printing thread rather than showing a wrong glyph. Fixed
two ways - `main.py` reconfigures stdout to UTF-8 at startup, and `theme.safe_chars()`
degrades to ASCII if it still cannot encode. **This also affected the parallel
voice-upgrade work**: every Hindi/Gujarati word the lexicon repairs would have hit the
same crash.

**Also closed A7's second half:** `AIDecisionMaker` now reads `AppConfig.ai_manager`
instead of re-parsing `config.json`, so there is one reader of that file, not two.

Original brief below.

### (original brief) [todo-C7] TUI redesign — one restrained palette, light + dark (NEW, per D-5)

**Brief (user's words):** *futuristic, modern, yet peaceful — not attention-grabbing, but
beautiful and well contrasted. Consistency in colour matters. No rainbow colours.*

**Current state.** `main.py:118` defines a 3-entry `rich.Theme`
(`phoenix: bold bright_blue`, `user: bold red`, `time: dim bright_black`) — but the rest of
the file bypasses it and hardcodes styles inline: `dim cyan` (line 176), `yellow` twice
(189-190), `white` (194), `bright_white` (197), `bold magenta` (247), plus a 51-character
`━` rule. So there are **six** colours in play with no relationship to each other, and
`manager.py` has its own separate emoji-bearing formatter. That is the rainbow.

**Design rules to hold to:**
- **One accent hue, two neutrals.** Everything is the accent, or a step on a grey ramp.
  Semantic colour (warn/error) is the *only* exception and must be rare enough to mean
  something. Blue-cyan reads "calm technical" and is already the Phoenix identity colour —
  keep it; drop red/magenta/yellow as decoration.
- **Hierarchy comes from weight and dimming, not from hue.** `dim` / normal / `bold` on
  one colour separates timestamp, speaker and body better than three different colours do,
  and stays legible in both themes.
- **Contrast is a requirement, not a preference.** Target WCAG AA (4.5:1) for body text
  against the terminal background in *both* themes. `bright_black` on a light background
  is the classic failure — it is unreadable, and it is in the theme today.
- Truecolor hex, not the 16 ANSI names. ANSI names are remapped by the user's terminal
  profile, so "bright_blue" is a different colour in every terminal and neither theme can
  be verified. `rich` supports `#rrggbb` directly.

**Implementation:**
- `core/theme.py` — two `dict[str, str]` palettes (`LIGHT`, `DARK`) → one `build_theme()`
  returning a `rich.Theme`. Every style used anywhere gets a **semantic name**
  (`phoenix`, `user`, `time`, `muted`, `accent`, `warn`, `error`, `rule`, `status`).
- New config key `ui.theme: "dark" | "light" | "auto"`. `"auto"` can read the Windows
  apps-light-theme registry value (`HKCU:\...\Themes\Personalize\AppsUseLightTheme`).
- **Delete every inline style string in `main.py`** — a style name that is not in the theme
  should not exist. That is what makes the palette enforceable rather than aspirational.
- Fold `manager.py:_handle_voice_log`'s separate formatter into the same theme (it
  overlaps with [todo-C6]; do C6 and C7 together — C6 gives structured events, C7 gives
  them one consistent rendering).
- Add the dormant/awake state indicator from [todo-A2] and the offline indicator from
  [todo-B1] to the status line, styled as `muted` — visible when looked for, not
  attention-grabbing.

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

### ~~[todo-D1]~~ CPU-only STT — **MEASURED 2026-08-12, keeping CPU**
```
cpu/int8       load 1.15s | median 0.973s for 7.42s audio | rtf 0.131
cuda/int8_f16  RuntimeError: Library cublas64_12.dll is not found or cannot be loaded
```
**CUDA is not merely unwise here, it is unavailable** - the CUDA 12 runtime is not
installed, so `_resolve_device`'s existing GPU warm-up correctly falls back. Installing
`nvidia-cublas-cu12` + `nvidia-cudnn-cu12` (~500 MB) would change that, but the numbers
say do not bother: at rtf 0.131 a typical 3 s command costs ~0.4 s of STT against a
1.8 s router call and a 1-3 s answer call. STT is ~10% of the turn. **The bottleneck is
the LLM, not Whisper.** Note the docstring in `_resolve_device` gives VRAM contention as
the reason for the CPU default; the real current reason is the missing runtime.
Superseded rationale below.
`_resolve_device` defaults to CPU *by design* ("borrowing VRAM for STT would slow the LLM
down by more than it speeds up transcription"). That reasoning was sound when the answer
model was 4.4 GB. With `llama3.2:latest` at 2.0 GB there is now ~1.5 GB of headroom on a
4 GB card. `small.en` in `int8_float16` is ~250 MB. **Measure it** — set
`stt.device: "cuda"`, run a 20-command soak, and compare `ollama ps` CPU/GPU split before
and after. If the LLM stays ≥90 % GPU, keep CUDA.

### ~~[todo-D2]~~ Grow the zero-cost path — **DONE 2026-08-12**

Built `scripts/utilities/mine_aliases.py`, which replays `data/ChatLog.json` through the
same two deterministic stages the live router uses and reports what still reaches the
model. It proposes; it never edits - an alias is a permanent claim that a phrase always
means one thing.

**The result contradicted the plan's own assumption.** `tests/test_routing.py` suggested
~40% of utterances resolve without a model call; against the real log it was **3%**. The
test file is device-command heavy while actual use is mostly conversational - greetings,
acknowledgements, farewells - each costing a ~1.7 s model call to produce a canned reply
the model added nothing to.

Added `CONVERSATION_ALIASES` (48 entries) plus one new `youarewelcome` intent, since
"thank you" had no correct target - the nearest existing tag replied *"Thank you, sir"*.

```
real chat log   zero-cost 3%  -> 19%
test_routing    zero-cost 15/42 -> 17/42,  accuracy still 100% end-to-end
```

Kept narrow on purpose. `"it's amazing"` repeats in the log and is deliberately NOT
aliased: it is a comment about something specific and deserves a real answer.

Three regression tests now guard the table - every alias target must exist, must have a
non-blank response, and must survive `normalize()` (a key that normalises differently is
unreachable and would fail silently).

### (original note) [todo-D2] Grow the zero-cost path
`tests/test_routing.py` already reports "Resolved with no LLM call". Every utterance moved
into Stage 0/0b saves **1.5–3 seconds**. Cheap additions:
- alias-table entries for the top-N utterances observed in `data/ChatLog.json`
  (write a script that mines the log and proposes aliases — the data is already there)
- extend `_match_command_grammar` to cover `open`/`close`/`play` with an app-name
  vocabulary (already implicitly there via `OpenAppHandler`, but it runs *before* the
  router with a crude `"open" in query` substring test that also fires on "open source")
- a normalised-utterance → last-decision cache with a small TTL, so repeated commands
  skip the router entirely

### ~~[todo-D3]~~ Stream the answer model into TTS — **DONE 2026-08-12**

Measured, first word out loud:

| query | blocking | streaming | saved |
|---|---|---|---|
| Who was Mahatma Gandhi? | 11.55 s | 0.93 s | 10.62 s |
| Explain a transformer network | 2.23 s | 0.95 s | 1.28 s |
| How far is the moon? | 0.77 s | 0.62 s | 0.14 s |
| **mean** | **4.85 s** | **0.83 s** | **4.01 s** |

`OllamaHelper.chat_stream` + `Utils/limbs/sentence_stream.py` +
`AIDecisionMaker.compose_answer_streaming`, wired through `IntentRouter._answer`.
Toggle with `stream_answers` in config.json.

**The hard part was not splitting, it was not splitting in the wrong place.** A bad cut
makes TTS stop dead with falling intonation mid-phrase, which sounds like a fault. The
splitter holds back on abbreviations ("Dr.", "5 p.m."), decimals ("3.14", "Python 3.11"),
and fragments too short to be worth their own round trip, and force-flushes on a word
boundary if a model forgets punctuation entirely. 15 tests in
`tests/test_sentence_stream.py`, most of them asserting that something does NOT split.

**Streaming commits us**, and that needed a decision: `_handle_unknown` escalates a
declined answer to a web search, but once sentence one has been spoken there is no taking
it back. So escalation is only available while still silent - `emit` refuses to voice a
sentinel or a hedge, so a declining model produces no speech, and the old escalation path
runs untouched. A late hedge after two good sentences is simply not spoken, which is far
better than answering twice.

### (original note) [todo-D3] Stream the answer model into TTS
Today: `compose_answer` waits for the full completion (`stream: False`), *then* TTS runs,
*then* audio plays. Sentence-level streaming — take the first sentence off the token stream
and **start speaking it while the rest is still generating** — cuts perceived latency
roughly in half.

**This survives the Piper cancellation.** The win is engine-independent: it is about
overlapping generation with speech, not about which synthesiser runs. If anything SAPI5
suits it *better* — a resident COM engine has no per-sentence process spawn, so the
pipeline is `token → sentence → speak` with no startup cost between sentences.

**Shape:**
- `OllamaHelper.chat` gains `stream: True` (it already has the request shape for it)
- a sentence splitter accumulates tokens and emits on `[.!?]` + whitespace, with a
  ~120-char forced flush so a model that forgets punctuation cannot stall the audio
- each sentence is pushed to `GlobalSpeechWorker`'s existing queue — which already
  serialises speech and is already the right abstraction ([todo-C2])
- **barge-in must drain the queue, not just stop the current sentence** — otherwise
  interrupting Phoenix mid-answer leaves 3 queued sentences that still play. This is a new
  failure mode that streaming introduces; handle it in the same change.
- first-sentence latency becomes `time-to-first-sentence` (~300-500 ms) instead of
  `time-to-full-completion` (1-3 s).

### ~~[todo-D4]~~ Cache TTS for canned responses — **MEASURED 2026-08-12, REJECTED**

```
phrase                                   synth    audio produced
Yes boss.                                0.133s   1.40s
The battery is at eighty percent, sir.   0.159s   2.88s
I have opened Chrome for you, boss.      0.147s   2.67s
```

SAPI5 synthesis is a flat **~0.15 s regardless of phrase length**, and MCI
open/play/close adds ~0.09 s back. Net saving from a cache: **~0.05 s.**

**The premise died with Piper.** D4 was written when TTS meant spawning
`piper.exe` per utterance to write a .wav - genuinely expensive, and worth
caching. SAPI5 is a local concatenative engine that is already resident, so
there is essentially nothing to cache away.

There is also a real hazard: calling `say()` and then `save_to_file()` on the
same pyttsx3 engine **hangs the process** (hit while measuring this; the run had
to be killed). A cache would need a second engine on its own thread, plus
invalidation on voice/rate change and a growing directory of .wav files - real
complexity and a deadlock risk, for 50 ms.

Not building it. `data/intents.json`'s 435 canned responses stay live-synthesised.

### (original note) [todo-D4] Cache TTS for canned responses
`data/intents.json` has 144 intents with fixed `responses`, and `_apply_honorifics`
substitutes from a fixed list. Pre-synthesise the common ones to `.wav` at first use and
key a cache on `hash(text + voice)`. "Yes boss", "Done", "Noted." should be instant.

### Model bake-off — **MEASURED 2026-08-12** (asked: "gemma3 seems faster")

Three candidates, same harness, same box (GTX 1650, 4 GB VRAM).

**As router** (27 routed cases):

| model | on-GPU | accuracy | median | mean | worst |
|---|---|---|---|---|---|
| `llama3.2:latest` 3.1 GB | 90% | 25/27 (92%) | **1.82 s** | **1.66 s** | 2.84 s |
| `gemma3:latest` 4.4 GB | **55%** | 25/27 (92%) | 2.00 s | 2.86 s | 23.80 s |
| `llama3.2:1b` 1.7 GB | 100% | 16/27 (59%) | 3.57 s | 5.65 s | 50.58 s |

**As answer model** (5 prompts, `num_predict=220`):

| model | median | mean | worst | throughput |
|---|---|---|---|---|
| `llama3.2:latest` | **3.00 s** | **2.90 s** | 5.67 s | ~170 char/s |
| `gemma3:latest` | 11.47 s | 7.92 s | 11.71 s | ~32 char/s |

**Root cause is VRAM, and it is physical, not tunable.** `ollama ps`:
```
llama3.2:latest   3.1 GB   10%/90% CPU/GPU
gemma3:latest     4.4 GB   45%/55% CPU/GPU     <- does not fit in 4 GB
```
gemma3 runs 45% of its layers on the CPU, so it is ~5x slower per token. No prompt or
config change fixes that; only more VRAM would.

**Why gemma3 can feel faster:** its first two answers in the bake-off were genuinely
quick (2.06 s, 2.85 s) before settling at ~11.5 s once the GPU cache filled. A two-question
spot check lands entirely inside the fast window. The steady state is 4x slower.

**Decision: `llama3.2:latest` for both roles.** The real perceived-latency win is
[todo-D3] (stream the first sentence into TTS), not a different model.

### ~~[todo-D5]~~ Try `llama3.2:1b` as the router — **MEASURED 2026-08-12, REJECTED**
Same 27 routed cases, same harness, model swapped in-process:

| router | accuracy | median | mean | slowest |
|---|---|---|---|---|
| `llama3.2:latest` (3.1 GB) | **25/27 (92%)** | **1.82 s** | **1.66 s** | 2.84 s |
| `llama3.2:1b` (1.7 GB) | 16/27 (59%) | 3.57 s | 5.65 s | 50.58 s |

The 1b is worse on **both** axes, which was not the expected outcome. It is not VRAM:
`ollama ps` shows the 1b resident at **100% GPU** while the 3B sits at 90%. The cause is
token count - the 1b does not follow the JSON contract, rambles, and runs into
`num_predict=60` on nearly every call, where the 3B emits short valid JSON and stops
early. Latency here is dominated by tokens generated, not by parameter count.

**Decision: keep `llama3.2:latest` for both roles.** The 'tiny fast router' idea is
refuted for this model family on this box. Original note below.
`router_model` and `answer_model` are both `llama3.2:latest`, yet `ai_manager` keeps two
separate `OllamaHelper` instances and `manager.py:_warm()` warms both. Harmless today
(Ollama dedupes by model name) but it means the *design* intent — a tiny fast router
(`llama3.2:1b`, already pulled, 1.3 GB) plus a better answerer — is unrealised.
**Try `llama3.2:1b` as the router.** `tests/test_routing.py` will tell you within minutes
whether accuracy holds, and it would free ~700 MB of VRAM.

---

## SECTION E — Repo hygiene

### ~~[todo-E1]~~ Stray root files — **DONE 2026-08-12**
Root is now `README.md` + `main.py` only. `ok.py` (a learning scratch file) and
`core/main_assistant.py` (703 lines, superseded, closes A9) deleted; `clean_empty_files.py`
and `validate_structure.py` moved to `scripts/utilities/`. Also removed 893 lines of dead
utilities there: both `download_piper_voices*.py` (Piper dropped), `apply_queue_fix.py`
(a one-off migration already applied) and `load.py` (the pre-`main.py` launcher).
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
- ~~`Utils/plugins/`~~ — **DONE 2026-08-11**, 14 files / 3,917 lines deleted (see C3)
- ~~`helpers/`~~ — **DONE**, removed in the repo-clean commit (`ConsoleUI.py`,
  `ConsoleUI_new.py`, `HelperPHNX.py`, `QueueManagerPHNX.py`)
- ~~`bgprogs/BgVoiceProcessorPHNX.pyw`~~ — **DONE**, removed in the repo-clean commit
- `trials/` (already gitignored, 400+ lines of old experiments)
- `tests/*.wav` (~20 files), `tests/piper_models/`, `tests/coqui_output/`

### ~~[todo-E3]~~ Dependency manifests — **DONE 2026-08-12**
Audited by AST-walking every import in `Utils/`, `core/`, `tests/`, `scripts/`, `main.py`
and diffing against the declared list. **60 deps -> 29.** Removed 25 never-imported
packages (Flask, PyQt5, cohere, groq, selenium, webdriver-manager, pywhatkit, mtranslate,
googlesearch-python, appopener, websockets, aiohttp, ...). Left transitive deps to the
packages that require them (tokenizers/huggingface-hub -> faster-whisper, Pygments/
markdown-it-py -> rich, lxml -> trafilatura).

**Found a real install-breaking bug:** `pytube` and `pygetwindow` are imported at MODULE
level in `action_utilities.py` - which every process imports - but were never declared, so
a fresh `uv sync` produced a repo that crashed on import. Added, with `comtypes` and
`pycaw`. `scipy`/`sounddevice` moved to the dev extra. `torch` deliberately NOT declared:
its only use is a `try/except ImportError` CUDA probe in the unused `VoiceRecognition`
GPU path, and CUDA is unavailable anyway (see D1) - dropping it saves ~2 GB per install.

`Requirements.txt` deleted (it was also a case-duplicate with `requirements.txt`).
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

### ~~[todo-E6]~~ Logging configured five different ways — **DONE 2026-08-12**
New `core/logging_setup.py`; every process calls `setup_logging(name)`. All output now
goes to `logs/phoenix_<name>.log`, rotating at 2 MB x 3, level from `PHOENIX_LOG_LEVEL`
(default INFO).

Three things this fixes beyond tidiness:
- **the processor ran at DEBUG in production**, which is why `bg_voice_processor.log`
  reached 2.2 MB of comtypes COM refcount chatter with the real traceback buried in it
- paths were **relative**, so files landed wherever a process was started from
- `basicConfig` is a **no-op when the root logger already has handlers**, so whichever
  module imported first silently won and the rest were ignored

`queue_manager.py` no longer owns a log file - it is a library imported into three
processes, so it logs to whichever file the host configured. Its `propagate = False` is
removed: that existed because the root logger might carry a console handler and print
into the chat, and `setup_logging` now guarantees a file-only root.
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

### ~~[todo-F1]~~ Make the suite runnable — **DONE 2026-08-12**
pytest installed (it was declared as a dev dep but never actually present). Config added
to `pyproject.toml` with a `slow` marker for the Ollama-dependent suite.

```
.venv/Scripts/python.exe -m pytest tests -q      # 47 tests
.venv/Scripts/python.exe -m pytest tests -m slow # routing, needs Ollama
```

`tests/test_suites.py` drives the standalone suites **as subprocesses**, deliberately:
several mutate `AppConfig` and one replaces functions in `web_search` with tripwires, so
sharing an interpreter would leak state between suites and make failures depend on
collection order.
`uv sync --extra dev`, convert `test_routing.py`'s `main()` into a pytest test marked
`@pytest.mark.slow` (it needs Ollama), and add `pytest.ini` with markers.

### ~~[todo-F2]~~ Missing coverage — **DONE 2026-08-12**
`tests/test_units.py`, 39 pytest-native tests over the three most intricate untested pure
functions: `_match_command_grammar`, `RememberStore._is_grounded`/`add_fact`, and
`tool_registry.needs_fresh_data`/`_forget_request`.

Two of my first-draft assertions failed and **the code was right both times** - worth
recording, since both are contracts rather than accidents:
- `"turn it up"` resolves to volume with no antecedent. It is not an ambiguous pronoun;
  in English it carries its own subject. The genuinely ambiguous case is `"decrease it"`,
  which correctly returns None.
- `_is_grounded("", src)` returns True. Empty/short/subjectless facts are `add_fact`'s
  responsibility; `_is_grounded` answers exactly one question - did every content word
  come from the user. Asserting more there tests the wrong layer.

Original priority table below.
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
| G3 | `os.system("shutdown /s")`, `taskkill /F /IM python.exe` reachable from a voice command with **no confirmation** | `action_utilities.py:2422` | high (destructive, not exploitable) |
| ~~G4~~ | ~~`plugins/base.py:163` generic `run_async(command, shell=True)`~~ | **RESOLVED 2026-08-11** — `Utils/plugins/` deleted, taking all 4 of its `shell=True` sites with it | — |
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

**Phase 1 — stop the bleeding** — ✅ **COMPLETE 2026-08-12**
A3, A1+A2, A4, A7, A5, A6, A8 all done. 163 checks passing across 4 suites.

**Phase 2 — make "offline" true (one day)**
B1 (with auto-detect, D-3) → G3 → then measure D1 and D5 with `tests/test_routing.py`
*(B2 cancelled — see D-1.)*

**Phase 3 — hygiene** — ✅ **COMPLETE 2026-08-12**
E1, E2, E3, A9, E6, F1, F2 all done.

**Phase 4 — architecture (multi-day, do only after Phases 1-3 land and tests exist)**
C1 (4 processes → 2) → C2 → **C6 + C7 together** (structured events + the themed renderer
that consumes them — doing C7 before C6 means restyling a stdout regex parser you are
about to delete) → C4 → C3

**Phase 5 — speed** — ✅ **COMPLETE 2026-08-12**
D3 done, D2 done, D4 measured and rejected (SAPI5 synthesis is ~0.15 s; nothing to cache).

**Phase 6 — offline knowledge** — ✅ **COMPLETE 2026-08-12**

**Sequencing note:** A1+A2 has no dependencies and is the change the user will feel most
(today Phoenix answers every sentence in the room). It is a good first commit. C7 is
tempting to do early because it is visible, but it should wait for C6 — see above.

---

## Progress Notes
- 2026-08-10: audit complete, nothing implemented. `README.md` rewritten as the
  project map so future sessions do not need to re-read the source.
- 2026-08-11: A3 done (32 case-duplicate paths untracked). E2/G4 resolved by deleting
  `Utils/plugins/`. C3 decided: delete rather than adopt.
- 2026-08-12: user reviewed the plan. Decisions recorded in **LOCKED DECISIONS** at the
  top — Piper dropped for SAPI5/Zira, wake-gate behaviour specified exactly, offline mode
  becomes auto-detecting, TUI theming added as C7, D3/D5/B3 confirmed wanted.
- Deliberately NOT recommending: real acoustic echo cancellation (see the note at the
  bottom of `temp-todo-listener-rewrite.md`), and a rewrite of the routing brain — that
  layer is the strongest part of the codebase and should be left alone.
