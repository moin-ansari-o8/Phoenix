# Phoenix Upgrade Status - What Is Left

Date: 2026-04-09
Based on: PHOENIX_COMPREHENSIVE_ANALYSIS.md + SENIOR_REVIEW_PHOENIX_ARCHITECTURE.md + current code verification

---

## 1) What is already done

### Implemented and working in code
- Queue IPC foundation exists:
  - core/queue_server.py
  - helpers/QueueManagerPHNX.py
  - core/continuous_listener.py
  - bgprogs/voice_command_processor.py
- Self-voice suppression exists:
  - Shared speaking flag via QueueManager
  - Listener skips capture while Phoenix is speaking
- Faster-Whisper is integrated:
  - GPU/CPU loading logic exists
  - Transcription pipeline is active in listener/processor flow
- Wake-word + follow-up mode exists:
  - Loop-style conversation flow is implemented
- Edge TTS integration exists with pyttsx3 fallback:
  - HelperPHNX.py supports edge_tts first, then fallback
- Plugin architecture prototype exists:
  - plugin-temp/base.py
  - plugin-temp/normal/* plugins
  - integration example drafted

---

## 2) What is partially done (started, but not connected)

- Reorganization to core/ is partial:
  - core/ has launch_phoenix.py, main_assistant.py, continuous_listener.py, queue_server.py
  - But root launch files are empty and docs still point to old paths
- Plugin system is built as prototype but not wired into runtime path:
  - No production import/usage from main runtime flow
- Edge TTS was added, but Piper decision is unresolved:
  - Piper has tests/scripts but runtime still not switched to Piper
- Queue architecture exists, but entrypoint wiring is inconsistent:
  - core/launch_phoenix.py references core/bgprogs path that does not exist

---

## 3) What is not done yet

### From the upgrade plans (major items still pending)
- No centralized config module:
  - Missing config.py single source of truth
- No unified manager orchestration:
  - Missing bgprogs/manager.py (or equivalent production manager)
- No soul/memory architecture from senior plan:
  - Missing data/core.md
  - Missing core/soul.py
- No SQLite persistence layer from senior plan:
  - Missing data/database.py
  - Missing phoenix.db integration
- No semantic intent matching engine:
  - Still mostly SequenceMatcher pattern matching
  - No sentence-transformers production integration
- UtilitiesPHNX.py is still monolithic:
  - Not fully split into production plugin modules
- No finalized MCP integration:
  - Only planning/example level

---

## 4) Critical blockers to fix first

1. Resolve merge conflict in bgprogs/time_monitor.pyw
   - File currently has unresolved conflict markers

2. Fix broken launcher wiring
   - core/launch_phoenix.py points to base_dir/bgprogs but bgprogs is not inside core/
   - root launch_phoenix.py and root queue_server.py are empty

3. Pick one canonical runtime architecture
   - Current state mixes:
     - core/main_assistant.py monolith path
     - helpers/ProcessorPHNX.py + bgprogs/voice_command_processor.py queue path
   - Need one final source of truth

4. Align docs with real runnable entrypoints
   - README still describes load.py and root main_assistant.py style flow
   - Current code is mixed after partial reorganization

---

## 5) Exact remaining work list

### Phase A - Make project run cleanly (must-do)
- [ ] Fix time_monitor.pyw merge conflicts
- [ ] Repair launch path resolution in core/launch_phoenix.py
- [ ] Create proper root wrappers OR remove empty root launch files
- [ ] Decide one primary run command and make it reliable
- [ ] Update README run instructions to that one command

### Phase B - Connect architecture (must-do)
- [ ] Remove duplicated assistant logic between core/main_assistant.py and helpers/ProcessorPHNX.py
- [ ] Keep one intent engine and one action routing flow
- [ ] Integrate plugin system into real execution path (not example-only)
- [ ] Move remaining direct utility calls to plugin actions (gradually)

### Phase C - Implement planned upgrades (next)
- [ ] Add config.py and move constants/thresholds into it
- [ ] Add data/core.md and core/soul.py
- [ ] Add data/database.py + sqlite3 persistence for memory/history
- [ ] Add semantic matching fallback before no-match path
- [ ] Add tests around intent matching + queue + speech suppression

### Phase D - Optional strategic choices
- [ ] Decide final TTS engine strategy:
  - Option 1: Edge TTS primary + pyttsx3 fallback
  - Option 2: Piper primary (offline-first) + fallback
- [ ] If MCP is required, implement plugins/mcp in production, not temp

---

## 6) Architecture verdict right now

The upgrade plan was started well, but implementation is currently in a hybrid transitional state:
- Some modern pieces are real and good (queue, whisper, speaking suppression, plugin prototype)
- Core orchestration and file connectivity are incomplete
- Documentation and runtime entrypoints are out of sync

Priority is not adding new features now. Priority is finishing integration so all existing pieces are connected and stable.
