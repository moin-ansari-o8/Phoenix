# Task: Voice upgrade - Hinglish lexicon, honest answers, slower endpointing, speaker lock
Generated: 2026-08-12
Status: **IMPLEMENTED 2026-08-12.** All four workstreams landed. 333 checks pass
across six offline suites. See "What actually shipped" at the bottom for the
places the plan was wrong.

Four requests, four workstreams:

| WS | Request | Core problem |
|----|---------|--------------|
| A | Hindi/Gujarati words heard correctly; play Hindi songs by name | STT model is English-only; no lexicon layer; song slot is never matched against `data/songs.txt` |
| B | Say "I don't know" instead of inventing | No unknown escape hatch anywhere in the answer path |
| C | Stop cutting me off when I pause | `hangover_ms: 600` closes the utterance after 0.6 s of silence |
| D | Respond only to my voice | No speaker identity exists anywhere in the pipeline |

**Recommended execution order: C -> A -> B -> D.**
C is a config change with immediate daily payoff. A depends on an STT model decision
that C's latency budget influences. B is prompt + one deterministic gate. D is the
largest and the only one needing a new model download.

---

## Evidence gathered (read from source, not assumed)

| # | Finding | Location |
|---|---------|----------|
| E1 | `stt.model = "base.en"`. The `.en` checkpoints are trained on English audio only, so they have no Hindi/Gujarati **acoustic** grounding. They are not, however, incapable of *emitting* those words: the tokenizer is byte-level BPE, so `sahiba` is representable, and prompt conditioning can pull it out. Expect degraded-but-phonetically-related output (`sahiwa`, `sa hiba`), not garbage. **How degraded is an open empirical question - A0 answers it before any model swap is considered.** | `core/config.json:91` |
| E2 | A dictionary layer already exists but is half-built: `_build_dynamic_prompt()` scrapes every word longer than 4 chars out of all 807 intent patterns, `sorted()` them, and truncates at 80. Alphabetical truncation means the surviving 80 are whatever sorts first - not whatever matters. Songs are never included. | `Utils/runners/voice_command_processor.py:239-289` |
| E3 | faster-whisper 1.2.1 **is installed and does support `hotwords`**. Two independent bias channels exist: `initial_prompt` (goes in as previous-context tokens) and `hotwords` (goes in behind `sot_prev`). Both are capped at `max_length // 2` = **223 tokens**. Roughly 120-150 words total, hard ceiling. A 500-song library will never fit. | `.venv/.../faster_whisper/transcribe.py:1542-1550` |
| E4 | `beam_size: 1`. Prompt bias **does** work at beam 1 - it shifts the logits at every decoding step, so the greedy argmax changes too. Beam search only helps *additionally*: it can recover when the first token of a foreign word still comes out wrong, where greedy is locked in. So beam 3 is an accuracy upgrade, not a prerequisite. | `core/config.json:94` |
| E5 | `data/songs.txt` is 58 lines and dirty: 40+ entries end in the literal word `original`, there are exact duplicates (`haan tu hai original` x3, `perfect original` x3), and junk rows (`no original`, `music original`, `some music settings original`). It is a write-log, not a library - `play_random_song()` appends `song + " original"` on every confirmation. | `data/songs.txt`, `action_utilities.py:2153` |
| E6 | `play_random_song()` extracts the song with `re.search(r"play (.+?) (song|music)", query)` and **never consults `load_songs()` for matching**. Say "play sahiba" and the regex misses (no trailing "song"), so it plays a random track instead. The library is only ever used as a random pool. | `action_utilities.py:2127-2161` |
| E7 | `play_song()` calls `Search(song)` (pytube) and opens `results[0]`. No verification, no fallback if pytube's scraper breaks. | `action_utilities.py:2163-2169` |
| E8 | `compose_answer()` has exactly one honesty rule, and only for evidence mode ("If they lack the answer, say so") plus a personal-details guard. In the no-evidence branch the model is told "Answer from your own knowledge" with no way to decline. | `Utils/ai_manager.py:291-304` |
| E9 | `hangover_ms: 600` = 19 consecutive silent 32 ms frames closes the utterance. `max_utterance_ms: 12000` hard-caps it. A slow speaker pausing 0.8 s mid-sentence gets split into two utterances, and the first half is dispatched as a command. | `core/config.json:80,82`, `audio_capture.py:646` |
| E10 | `VoiceProcessor.MIN_SILENCE_DURATION = 0.6` is set and never read. Dead. | `voice_command_processor.py:108` |
| E11 | Wake-word matching is `any(word in text_lower ...)` over `["phoenix","babe","baby","yo","yoi",...]`. `"yo"` matches inside "you", "your", "yoga", "beyond". Anyone in the room saying "your" wakes it. Relevant to WS-D: speaker lock cannot fix a gate this leaky on its own. | `voice_command_processor.py:230-233` |
| E12 | Available and already installed: `torch 2.11.0`, `torchaudio 2.11.0`, `librosa`, `onnxruntime 1.24.4`, `webrtcvad`, `numpy`. Speaker embedding needs **no new heavy dependency** - only a model file or a thin wrapper package. | `.venv/Lib/site-packages/` |
| E13 | Not installed, needed: `rapidfuzz` (WS-A phonetic repair, ~1 MB C++ wheel), and one of `speechbrain` / `resemblyzer` (WS-D) unless the ONNX route is taken. | - |

### Reference: a working implementation of this exact technique

The user supplied a report from another app that does Hinglish/Gujarati-in-English
correctly. Its recipe: (1) flatten the dictionary into a word list, (2) pass it as
`initial_prompt` behind a grounding sentence, (3) hard-pin `language="en"` so the
model treats the foreign word as a loanword instead of switching languages,
(4) regex-replace recognised triggers afterwards. **This validates the design
below** - A3 is its steps 1-3, A4 is a stronger version of its step 4.

Two things that report leaves out, both of which decide whether it works here:

- **It only works on a multilingual checkpoint.** Its own argument ("Whisper is a
  multilingual model... force it to stay English") is true of `base`/`small`/`large`
  and false of `base.en`, which has no Gujarati phonetics to bias toward. That app
  is running a multilingual model. Phoenix is not (E1). This is the whole of A1.
- **It has no size limit.** Fine for a handful of terms; it silently truncates once
  the list passes 223 tokens (E3), and a growing song library passes that fast.

Its step 4 is exact-string replacement, which only fires when Whisper spelled the
word *perfectly*. A4 replaces that with fuzzy phonetic matching, which also catches
"close but wrong" (`sahiwa` -> `sahiba`). Superset, same idea.

### The single most important consequence

E1 + E3 together mean **the "dictionary" the user is asking for cannot be only a
Whisper setting.** The bias channel holds ~150 words. A song library, an intents
vocabulary and a set of Hinglish words will not fit inside it.

The design therefore uses **two layers**:

1. **Bias layer (in Whisper)** - a small, curated, priority-ordered hotword set
   (wake words, user name, ~40 high-frequency command words, ~30 highest-value
   Hinglish tokens). Bounded at ~150 tokens. Cheap, imperfect.
2. **Repair layer (after Whisper)** - a phonetic normaliser + fuzzy resolver that
   maps whatever Whisper produced onto the real lexicon. Unbounded in size, zero
   STT cost, and it is where the song library and the full Hinglish vocabulary live.

The repair layer does the heavy lifting. This is also the only layer that can grow
to hundreds of songs.

---

## Workstream C - Endpointing for a slow speaker

*(Do this first. Config-only for phase C1.)*

### C1 - Widen the window

- [todo-C1.1] `core/config.json` -> `audio.hangover_ms`: `600` -> **`1200`**
- [todo-C1.2] `core/config.json` -> `audio.max_utterance_ms`: `12000` -> **`20000`**
  (mandatory - a 1.2 s hangover with a 12 s cap means long sentences hit the cap
  and get truncated mid-word, which is worse than the current behaviour)
- [todo-C1.3] `core/config.json` -> `audio.min_voiced_ms`: keep `400`. Raising it
  would start dropping short valid commands ("mute", "stop", "yes").
- [todo-C1.4] Verify `continuous_listener.py` actually reads all three from
  `AppConfig.audio` into `EndpointerConfig` (grep for `hangover_ms` there before
  editing config - a config key nobody reads is a silent no-op).
- [todo-C1.5] Delete the dead `MIN_SILENCE_DURATION` (E10).

**Cost of C1:** every command now waits an extra 600 ms of silence before Phoenix
starts thinking. That is a real, unavoidable trade at this layer - it is the same
knob, turned the other way.

### C2 - Continuation stitching (removes most of that cost)

The trade only exists because dispatch is bound to endpoint. Decouple them:

- [todo-C2.1] Keep `hangover_ms` at a **moderate** 800 ms in `EndpointerConfig`.
- [todo-C2.2] Add `audio.stitch_window_ms` (default 900). In `CapturePipeline`,
  when the endpointer closes an utterance, do not push it to the queue - park it in
  a `pending` slot and **start STT-side work is NOT started yet** (STT lives in the
  other process, so parking is free here).
- [todo-C2.3] If a new utterance opens within `stitch_window_ms` of the parked
  one's `end_timestamp`, concatenate `parked.audio + silence_gap + new.audio`
  into a single utterance and keep parking. Cap the merged length at
  `max_utterance_ms`.
- [todo-C2.4] If the window expires, push the parked utterance to the queue.
- [todo-C2.5] The echo gate's close-edge reset (`consume_close_edge()`) must also
  **drop the parked slot** - otherwise a fragment captured before Phoenix spoke
  gets stitched onto the user's next command, which is exactly the defect the
  listener rewrite fixed in August. This is the one dangerous interaction in C2.

Effective silence tolerance becomes 800 + 900 = 1.7 s, while a *finished* command
still only pays 800 ms + the pending-window timer. If C2 proves fiddly, C1 alone
is a complete, shippable answer to the request.

### C3 - Tests

- [todo-C3.1] `tests/test_listener_pipeline.py`: add cases - 1.0 s mid-sentence
  pause must NOT close; 2.0 s pause must close; stitched utterance carries the
  summed `voiced_ms`; parked utterance is dropped on echo close-edge.
- [todo-C3.2] Live check with `tests/mic_check.py` speaking deliberately slowly.

---

## Workstream A - Hinglish lexicon and song resolution

### A0 - Scope lock: songs only, and try it WITHOUT swapping the model first

**User has confirmed the target is song names, not Hinglish commands.** That makes the
model swap a *maybe*, not a prerequisite. Song titles are the easy case for the repair
layer: the slot is multi-word, matched against a closed ~35-entry library, and a wrong
match is cheap and obvious. `base.en` output that is merely phonetically close is
enough for `token_set_ratio` to land it.

Ordering follows from that: **A2 -> A3 -> A4 -> A5 on the current `base.en`, measure,
and only then decide A1.** Zero latency risk, zero model download, and it answers the
model question with data instead of argument.

- [todo-A0.1] After A4/A5 land, run the A6.2 song table on `base.en`. Record the hit
  rate on the ~35 real titles.
- [todo-A0.2] Decision gate: hit rate **>= 85% -> stop, keep `base.en`**, the request
  is satisfied and nothing got slower. **< 85% -> proceed to A1** and re-measure on
  `base` multilingual.
- [todo-A0.3] Whichever way it goes, write the measured numbers into
  `.github/mistakes.md`. The next session will otherwise re-litigate `.en` vs
  multilingual from first principles, as this one did.

### A1 - Decide the STT model (ONLY if A0.2 fails the gate)

Options, if the repair layer alone proves insufficient:

| Option | Hinglish | Speed | English accuracy | Notes |
|---|---|---|---|---|
| `base.en` (current) | weak but prompt-steerable | baseline | best at this size | 74M params |
| `base` (multilingual) | good | **same as `base.en`** | slightly worse | identical 74M params / architecture - the swap is not a speed decision |
| `small` (multilingual) | best | ~2.5-3x slower | better | likely blows the latency budget on CPU |
| `small.en` | weak | ~2.5x slower | best | pointless here |

**Note on the speed fear:** `base` and `base.en` are the same model size with the same
compute cost. Swapping does not slow transcription down. The real cost of the swap is a
small regression in *English* accuracy, which is why A0 tries to avoid needing it at
all. `beam_size` is the parameter that actually costs latency, and it is independent.

- [todo-A1.1] Write `tests/stt_bench.py`: transcribe a fixed set of ~15 recorded
  WAVs (mixed English commands + Hinglish song names) through `base.en`, `base`,
  `small`, at `beam_size` 1 and 5, printing per-file text plus wall-clock and RTF.
  Record the recordings under `data/stt_samples/` (gitignored).
- [todo-A1.2] Pick the model on measured numbers. **Recommendation before
  measuring: `base` multilingual with `beam_size: 3`.** Same file size as today, but
  with a vocabulary that can represent the sounds. Beam 3 buys extra accuracy on
  foreign words (E4); if it costs too much latency, beam 1 still works.
- [todo-A1.3] `language`: keep **`"en"`**, do not switch to auto-detect. With a
  multilingual model and `language="en"`, Whisper transliterates Hindi/Gujarati
  speech into roman script (`sahiba`, `vhalam aavo ne`) which is exactly what the
  lexicon and `songs.txt` are written in. Auto-detect flips to Devanagari output
  mid-session and would break every downstream string match.
- [todo-A1.4] Update `core/config.json` `stt.model` / `stt.beam_size`, and the
  README §3 and §7 tables.

### A2 - Build the lexicon files

- [todo-A2.1] Clean `data/songs.txt` (E5): strip the trailing `original` token,
  de-duplicate case-insensitively, drop junk rows (`no`, `music`, `original`,
  `some music settings`). Expect ~35 real titles to survive from 58 lines.
- [todo-A2.2] Fix the writer that created the mess: `play_random_song()` must stop
  appending `" original"` (`action_utilities.py:2153`).
- [todo-A2.3] Create `data/lexicon.json` - the single source of truth for the
  repair layer:
  ```json
  {
    "wake":     ["phoenix", "igris", ...],
    "hinglish": ["kholo", "bandh karo", "gaana", "bajao", "thoda", "zyada", ...],
    "commands": ["brightness", "volume", "screenshot", "reminder", ...],
    "names":    ["kaly", "moin", "rohit", ...]
  }
  ```
  Songs are **not** duplicated here - they are read live from `songs.txt` so adding
  a song needs no second edit.
- [todo-A2.4] Seed `hinglish` from the words the user actually says. Bootstrap it
  from `bg_voice_processor.log` transcripts plus a manual list; do not invent a
  generic Hindi word list - only words that appear in real commands earn a slot.

### A3 - Bias layer: rewrite `_build_dynamic_prompt()`

- [todo-A3.1] Replace the alphabetical-truncation logic (E2) with a
  **priority-ordered** builder: wake words -> user name -> `lexicon.names` ->
  `lexicon.commands` -> `lexicon.hinglish` -> most-recently-played song titles.
- [todo-A3.2] Budget it against the real limit: tokenise with the loaded model's
  tokenizer and stop at **200 tokens**, not at 80 words (E3). Log the final token
  count once at startup.
- [todo-A3.3] Pass the curated list via **`hotwords=`**, not `initial_prompt=`.
  `hotwords` is the channel designed for this and survives
  `condition_on_previous_text=False` cleanly. Keep `initial_prompt` for a single
  short style-anchor sentence, or drop it entirely.
- [todo-A3.4] Build once at startup, cache, and rebuild only when `songs.txt`
  mtime changes.

### A4 - Repair layer: `Utils/limbs/lexicon.py` (new)

This is the part that makes Hinglish reliable, and it costs no STT time.

- [todo-A4.1] `normalize_roman(text)` - a Hinglish-aware normaliser. Double-vowel
  collapse (`aa`->`a`, `ee`->`i`, `oo`->`u`), aspirate folding (`kh`->`k`,
  `bh`->`b`, `dh`->`d` for matching only), `w`<->`v`, `z`<->`j`, drop trailing
  `a`/`h`. `sahiba`/`saahiba`/`sahiwa` all collapse to the same key. Plain
  double-metaphone is **not** suitable - it is tuned for English orthography and
  mangles romanised Indic words.
- [todo-A4.2] `Lexicon.resolve(token, category, min_score)` using
  `rapidfuzz.process.extractOne` over normalised keys. Returns the canonical form
  or `None`. Threshold starts at 82, tuned by A6.
- [todo-A4.3] `Lexicon.repair_transcript(text)` - token-wise repair for the
  `wake`/`commands`/`names` categories only. Conservative: never rewrite a token
  that is already a valid English dictionary word unless the score is >= 92.
- [todo-A4.4] Wire into `voice_command_processor.process_audio_chunk()` **after**
  the hallucination and self-echo filters, before `user_said()`. Trace repairs as
  `[REPAIRED] heard -> canonical` so mis-repairs are visible in the TUI.

**Guard rail:** this must not become the fuzzy intent matcher that README §9.1 and
`intent_router.py:6` were written to kill. The distinction to hold: the repair layer
fuzzy-matches **words against a closed lexicon**, and the song resolver fuzzy-matches
a **slot value against a known library**. Neither ever selects an intent or a tool.
Intent selection stays exact-alias / grammar / LLM. Write this rule as a module
docstring so the next session does not undo it or over-extend it.

### A5 - Song resolution

- [todo-A5.1] Rewrite `play_random_song()` (E6). New order:
  1. `random` in query -> random from library (existing behaviour)
  2. extract the slot: strip leading `play`/`bajao`/`chalao`/`lagao` and trailing
     `song`/`music`/`gaana`; whatever remains is the requested title
  3. `Lexicon.resolve(slot, category="songs", min_score=75)` against the cleaned
     `songs.txt` -> on a hit, play the **canonical library title**, no confirmation
     prompt (the library match *is* the confirmation)
  4. on a miss, keep the current confirm-then-play-then-add flow, which is how new
     songs enter the library
- [todo-A5.2] Song matching gets a **lower** threshold (75) than word repair (82):
  the slot is multi-word, `token_set_ratio` is robust there, and a wrong song is a
  cheap, obvious, user-correctable error - unlike a wrong intent.
- [todo-A5.3] The confirmation loop calls `self.take_command()`, which belongs to
  the legacy `VoiceRecognition` path and is `None` in the voice processor
  (`Utility(spk=..., reco=None)`). **Verify this does not already crash today**
  before building on it; if it does, that is a separate bug to file.
- [todo-A5.4] Two-pass STT (optional, only if A3+A4 prove insufficient): when the
  transcript starts with a play verb, re-transcribe the same audio with the full
  song list as hotwords and prefer that result for the slot. Costs one extra STT
  (~0.3-0.6 s) on song commands only. Do not build this until A4 is measured.
- [todo-A5.5] `play_song()` has no failure path (E7) - wrap `Search()` and fall
  back to a YouTube search URL if pytube's scraper breaks.

### A6 - Tests

- [todo-A6.1] `tests/test_lexicon.py`: normaliser table (30+ pairs), resolver
  accepts/rejects, a **negative set** of ordinary English commands that must be
  returned unchanged ("play the news", "what is the time", "open brave").
- [todo-A6.2] Song resolution table: `play sahiba` -> `sahiba`;
  `play saahibaa song` -> `sahiba`; `play vhalam avo ne` -> `vhalam aavo ne`;
  `play something random` -> random path; `play despacito` (absent) -> miss path.
- [todo-A6.3] Re-run `tests/test_routing.py` after the STT model change - routing
  accuracy must not regress.

---

## Workstream B - Honest "I don't know"

### B1 - The escape hatch

Prompt-level instructions alone will not hold on a 3B model. Use the pattern that
already works in this codebase for memory saves: **a fixed sentinel the model can
emit, handled deterministically** (a fixed string cannot lie - README §5).

- [todo-B1.1] `ai_manager.compose_answer()`, no-evidence branch: add
  *"If you are not confident of the answer, reply with exactly UNKNOWN and nothing
  else. A wrong answer is worse than no answer."*
- [todo-B1.2] Detect a bare/leading `UNKNOWN` in the reply and convert it - never
  speak the sentinel.
- [todo-B1.3] On UNKNOWN, escalate rather than give up: if `web.enabled`, run the
  `search_web` path automatically and answer from evidence; announce it
  ("I don't know that one - let me look it up."). If the search returns nothing
  usable, say plainly "I don't know."

### B2 - Hedge detection (catches the case where the model answers anyway)

- [todo-B2.1] A small regex set over the composed answer: `as of my (last )?update`,
  `I don't have (access|real-?time)`, `I'm not sure but`, `I (may|might) be wrong`,
  `I cannot browse`. These are the tells that precede a fabricated answer.
- [todo-B2.2] On a hit, treat it as UNKNOWN (B1.3). Do not try to salvage the
  sentence - a hedged answer is a wrong answer wearing a hat.

### B3 - Evidence-mode tightening

- [todo-B3.1] Strengthen the existing evidence instruction from "If they lack the
  answer, say so" to name the sentinel too, so both branches share one contract.
- [todo-B3.2] Keep the personal-details guard exactly as it is (`ai_manager.py:300`)
  - it fixed a real, documented fabrication.

### B4 - Soul alignment

- [todo-B4.1] `core/soul.md` currently sets a confident persona. Add one line
  granting permission to not know, so the persona and the instruction do not fight.
  Keep it short - `soul.md` is on the latency path for every answer.

### B5 - Tests

- [todo-B5.1] `tests/test_honesty.py` (needs Ollama): a set of questions with no
  knowable answer ("what did I eat last Tuesday", "who is Rahul Mehta from Surat",
  "what is my neighbour's phone number") must produce an "I don't know" or a search,
  never an invented detail.
- [todo-B5.2] A control set of ordinary questions ("capital of france", "what is
  python") that must still be answered directly - the failure mode of B is
  over-deflection, and that would be a regression worse than the bug.

---

## Workstream D - Speaker verification (respond only to my voice)

**Set expectations honestly up front:** speaker verification on a laptop mic gives
roughly 2-5% equal error rate in a quiet room and degrades with distance, illness,
and background noise. It is a **convenience filter, not a security control** - a
recording of the user's voice passes it, and it is not the right tool for anything
that must not be spoofed. Ship it as a filter, describe it as a filter.

### D1 - Model choice

| Option | Quality | Cost | Verdict |
|---|---|---|---|
| SpeechBrain ECAPA-TDNN (192-d) | best (~1% EER) | new dep `speechbrain` + `hyperpyyaml`, ~80 MB HF download, torch already present | **recommended** |
| Resemblyzer (GE2E, 256-d) | good (~4% EER) | small dep, torch already present | acceptable fallback |
| ECAPA/TitaNet as ONNX | best | zero new deps (`onnxruntime` is installed), but the model file must be sourced and pinned | best if the download is acceptable to manage manually |

- [todo-D1.1] Try SpeechBrain first; time one embedding of 2 s of audio on this
  CPU. Budget: **under 150 ms**, since it runs on every utterance. If it exceeds
  that, drop to Resemblyzer.

### D2 - `Utils/limbs/speaker_id.py` (new)

- [todo-D2.1] `SpeakerVerifier.embed(audio_int16) -> np.ndarray` (L2-normalised).
- [todo-D2.2] `verify(audio) -> VerificationResult(accepted, score, reason)`.
  Cosine similarity against the enrolled centroid, plus max-similarity against the
  individual enrolled embeddings; accept on `max(centroid_sim, best_sim) >= threshold`.
- [todo-D2.3] **Fail-open on every uncertainty**: audio shorter than 0.8 s, model
  failed to load, or no enrolment profile present -> `accepted=True,
  reason="unverifiable"`. A voice assistant that goes deaf because a model file is
  missing is a worse failure than one that answers a guest.
- [todo-D2.4] Lazy-load the model; never block process startup on it.

### D3 - Enrolment

- [todo-D3.1] `tests/enroll_voice.py` - CLI: prompts 20 varied phrases (commands,
  questions, one long sentence), records via the existing `MicStream`, rejects
  takes under 1.5 s or with low voiced ratio, saves embeddings + centroid to
  `data/speaker_profile.npz`.
- [todo-D3.2] Gitignore `data/speaker_profile.npz` - it is biometric-derived data
  and belongs to this machine only.
- [todo-D3.3] Print the intra-profile similarity spread at the end. A tight spread
  (>0.85 between own samples) means a good enrolment; a wide one means re-record.

### D4 - Wiring

- [todo-D4.1] New config block:
  ```json
  "security": {
    "speaker_verification": {
      "enabled": true,
      "mode": "log",
      "threshold": 0.72,
      "min_duration_s": 0.8,
      "adapt": false
    }
  }
  ```
- [todo-D4.2] Call `verify()` at the **top of `process_audio_chunk()`, before
  Whisper**. A rejected utterance then costs ~100 ms instead of ~800 ms, and other
  people in the room never reach STT at all.
- [todo-D4.3] `mode: "log"` - always process, but print
  `[SPEAKER] score=0.68 (would reject)`. `mode: "gate"` - reject below threshold
  with a `[SPEAKER_REJECT]` trace. **Ship in `log` mode**, collect a few days of
  real scores, then flip to `gate` with a threshold picked from data. Choosing a
  cosine threshold by intuition is how this feature ends up ignoring its owner.
- [todo-D4.4] Optional `adapt: true` - update the centroid with accepted utterances
  scoring above 0.85, capped to a rolling window. Guards against mic/room drift.
  Off by default; it can also slowly drift the profile onto a frequent guest.

### D5 - Fix the wake gate too (E11)

Speaker lock does not fix `"yo" in "you"`. Both filters are needed, and this one is
five lines:

- [todo-D5.1] Replace substring matching with word-boundary regex over the wake
  word list, built once.
- [todo-D5.2] Keep the existing `"phoenix folder"` exclusion behaviour.
- [todo-D5.3] Consider dropping `yo`/`yoi` from the profile - two-character wake
  words are false-positive machines even with word boundaries.

### D6 - Calibration and tests

- [todo-D6.1] `tests/speaker_calibrate.py` - score a folder of owner clips and a
  folder of other-speaker clips, print the FAR/FRR curve and the equal-error
  threshold. Needs a few recordings of other household voices to be meaningful.
- [todo-D6.2] `tests/test_speaker_id.py` - unit level: identical audio scores ~1.0;
  short audio fails open; missing profile fails open; a corrupt profile file does
  not crash the processor.

---

## Cross-cutting

- [todo-X1] Every new config key must be **read** by code before it lands. The repo
  already carries `memory.auto_save` and `web.enabled` as dead keys (README §7);
  do not add a third.
- [todo-X2] README updates in the same commit: §3 pipeline diagram (stitching,
  speaker gate, repair layer), §7 config table (`stitch_window_ms`, `security.*`,
  new `stt.model`/`beam_size`), §9 lessons (add the "fuzzy on slot values, never on
  intents" rule from A4), §10 open work.
- [todo-X3] `.github/mistakes.md` entries for anything that bites during
  implementation - particularly the `.en`-model dead end (E1), which is a trap the
  next session will otherwise walk straight back into.
- [todo-X4] New dependencies into `pyproject.toml`: `rapidfuzz`, plus the WS-D
  choice. `Requirements.txt` too if it is still maintained.
- [todo-X5] Latency budget check after A and D land together: speaker embed (~120 ms)
  + `base` multilingual at beam 3 (~1.3x current STT) + repair (~5 ms) must not push
  the perceived response time past the current ~2-4 s. Measure with the `[STT]`
  trace line that already exists.

## Open questions for the user

1. ~~**WS-A scope:** Hinglish for commands, or only song names?~~ **ANSWERED
   2026-08-12: song names particularly.** Scope locked in A0 - repair layer on the
   current `base.en` first, model swap only if measurement demands it.
2. **WS-D:** does the assistant need to *respond* to guests at all (e.g. answer
   questions but refuse device control), or ignore them completely?
3. **WS-D:** are other household voices available for calibration recordings? Without
   them the threshold is a guess, and D6.1 is the difference between a working filter
   and one that locks the user out.

---

# What actually shipped (2026-08-12)

All four workstreams are in. Where the plan was wrong, it was wrong in ways worth
recording.

## Where the plan was wrong

| Plan said | Reality | Consequence |
|---|---|---|
| `base.en` **cannot** produce Hindi/Gujarati words (E1) | Overstated. The tokenizer is byte-level, so it can spell `sahiba`; it just has no Hindi acoustics and guesses worse. | The model swap became optional. A0 gate added; still on `base.en`. |
| Hotwords are near-useless at `beam_size=1` (E4) | Wrong. Prompt bias shifts logits at every step, so greedy decoding is affected too. Beam search only adds recovery from a bad first token. | `beam_size` stayed at 1. No latency cost paid. |
| Bias layer holds ~150 words | Measured 8.7 tokens per romanised title -> **~20 titles, permanently**. 4% coverage at 500 songs. | Forced the whole A+B redesign below. |
| Repair layer covers names, commands and Hinglish | Broke English: "weather today" -> "weather thoda". | Scoped to `names` + an exact alias map. |
| Confirm-before-playing an unknown song | `take_command()` raises in the voice processor - the mic is in another process. | Confirmation removed; Phoenix announces instead. |

## The design change that mattered

The user pushed back on the song library being static. They were right: the
hotword budget is fixed at ~20 titles no matter how much the library grows, so
biasing the first pass can never be the answer on its own.

Resolved with **A+B**: play-count-weighted bias window, plus two-pass
retrieval-then-rerank. The measurement that makes it work
(`tests/test_lexicon.py::test_candidate_recall`):

| mangling | top-1 correct | correct in top-8 |
|---|---|---|
| light | 92.1% | **100%** |
| heavy | 93.3% | **98.8%** |

Retrieval over the full library is nearly perfect; only ranking is unreliable.
So the second pass biases toward 8 retrieved candidates - which always fits the
budget, at any library size.

## Files

**New:** `Utils/limbs/lexicon.py`, `Utils/limbs/speaker_id.py`,
`data/lexicon.json`, `tests/test_lexicon.py`, `tests/test_honesty.py`,
`tests/test_speaker_id.py`, `tests/enroll_voice.py`

**Changed:** `audio_capture.py` (stitching), `continuous_listener.py`,
`voice_command_processor.py` (speaker gate, hotwords, rerank, repair),
`action_utilities.py` (song resolution, `take_command` safety, `play_song`
fallback, module logger), `ai_manager.py` (`UNKNOWN` + hedges),
`intent_router.py` (escalation), `core/config.py`, `core/config.json`,
`core/soul.md`, `data/songs.txt` (58 dirty lines -> 40 clean titles),
`pyproject.toml`, `.gitignore`, `README.md`, `.github/mistakes.md`

**Deps:** `rapidfuzz`. `resemblyzer` - and note it drags in a `typing` backport
that shadows the stdlib; uninstall it after.

## Still open

- [todo-A0.1] **Measure the song hit rate on real speech.** Everything so far is
  synthetic mangling and unit tests. Speak the 40 titles, count what resolves.
- [todo-A0.2] Decide `base.en` vs multilingual `base` from those numbers. >= 85%
  hit rate means stay put.
- [todo-A5.4b] **Measure whether the second pass actually helps.** Retrieval is
  proven; that biasing Whisper toward 8 candidates flips a wrong transcription
  often enough to be worth ~0.5 s is NOT. If it does not, delete the rerank -
  the retrieval layer stands on its own.
- [todo-C3.2] Live check of the 1.7 s pause tolerance with real slow speech.
- [todo-D3] **Nobody has enrolled.** Speaker verification is inert until
  `tests/enroll_voice.py` runs. It is wired, tested, and doing nothing.
- [todo-D6.1] Calibrate the threshold from real scores before switching
  `mode` to `"gate"`. Needs recordings of other household voices.
- [todo-B5.1] Live honesty check against Ollama - the offline tests cover the
  detector, not the model's willingness to emit the sentinel.
