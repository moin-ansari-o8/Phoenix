# Phoenix Voice Assistant - Comprehensive Codebase Analysis

> **Document Purpose:** Complete analysis of the Phoenix project for refactoring and modernization.  
> **Generated:** April 2026  
> **Current Version:** 5.9.0  

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Complete File Map](#complete-file-map)
4. [Core Components Deep Dive](#core-components-deep-dive)
5. [IGRS (Igris) Sibling Project](#igrs-igris-sibling-project)
6. [Voice Logic Comparison](#voice-logic-comparison)
7. [Data Flow Diagrams](#data-flow-diagrams)
8. [Code Quality Assessment](#code-quality-assessment)
9. [Refactoring Priorities](#refactoring-priorities)
10. [Modernization Roadmap](#modernization-roadmap)
11. [Offline-First Strategy](#offline-first-strategy)

---

## Executive Summary

### What Phoenix Is
Phoenix is a **Windows desktop voice assistant** built ~3 years ago as a learning project. It listens to voice commands (or typed input), matches them against predefined patterns, and executes corresponding actions like opening apps, controlling volume, setting timers, etc.

### Current State
- **Working:** Core voice recognition, intent matching, 100+ utility functions
- **Architecture:** Multi-process system with queue-based IPC
- **Speech Recognition:** Hybrid (Google API online, Faster-Whisper offline)
- **Text-to-Speech:** pyttsx3 (SAPI5 voices)
- **Intent System:** JSON-based pattern matching with fuzzy matching

### Key Statistics
| Metric | Value |
|--------|-------|
| Total Python Files | ~25 |
| Lines of Code (estimated) | ~8,000+ |
| Dependencies | 50+ packages |
| Intents/Commands | 100+ patterns |
| Utility Functions | 100+ |

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PHOENIX SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │  load.py     │────▶│  Queue       │────▶│  main_assistant.py │    │
│  │  (Launcher)  │     │  Server      │     │  (Main Brain)│    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│         │                    │                     │            │
│         │                    │                     │            │
│         ▼                    ▼                     ▼            │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │ BgBtryPHNX   │     │ ListenerPHNX │     │  helpers/    │    │
│  │ (Battery)    │     │ (Audio In)   │     │  (All Logic) │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│         │                    │                     │            │
│         │                    │                     │            │
│         ▼                    ▼                     ▼            │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │ BgTmPHNX     │     │ BgVoice      │     │ NetMonitor   │    │
│  │ (Time/Alarm) │     │ Processor    │     │ (Network)    │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Relationships

```
Entry Points:
├── load.py ──────────────────▶ Full Launch (spawns all processes)
├── launch_phoenix.py ────────▶ Modern Launch (queue-based system)
├── main_assistant.py ──────────────▶ Direct Voice Mode (standalone)

Core Flow:
├── User speaks ──▶ Microphone ──▶ VoiceRecognition ──▶ Whisper/Google
│                                         │
│                                         ▼
│                               Text Transcription
│                                         │
│                                         ▼
│                         ┌───────────────────────────────┐
│                         │  PhoenixAssistant.main()      │
│                         │  - Pattern Matching (65%+)    │
│                         │  - Intent Extraction          │
│                         │  - Action Mapping             │
│                         └───────────────────────────────┘
│                                         │
│                                         ▼
│                         ┌───────────────────────────────┐
│                         │  UtilitiesPHNX.py             │
│                         │  - 100+ action functions      │
│                         │  - System control             │
│                         │  - App management             │
│                         └───────────────────────────────┘
│                                         │
│                                         ▼
└──────────────────────── SpeechEngine.speak() ◀──────────
```

---

## Complete File Map

### 📁 Root Level Files

| File | Purpose | Priority | Notes |
|------|---------|----------|-------|
| `main_assistant.py` | **CORE** - Main assistant brain | 🔴 Critical | 700 lines, handles all command processing |
| `continuous_listener.py` | Continuous audio capture | 🔴 Critical | VAD-based listening, sends to queue |
| `load.py` | Legacy launcher | 🟡 Medium | Spawns background processes |
| `launch_phoenix.py` | Modern 3-process launcher | 🔴 Critical | Queue server + listener + processor |
| `queue_server.py` | IPC queue server | 🟢 Good | Clean, modern multiprocessing |
| `cmd_gui.py` | GUI command interface | 🟡 Medium | Alternative to voice input |
| `pyproject.toml` | Dependencies | 🔴 Critical | 50+ packages listed |

### 📁 helpers/ Directory (THE CORE LOGIC)

| File | Lines (est.) | Purpose | Priority |
|------|--------------|---------|----------|
| `HelperPHNX.py` | ~600 | Speech Engine, Voice Recognition, GUI | 🔴 Critical |
| `UtilitiesPHNX.py` | ~3300 | **100+ action functions** | 🔴 Critical |
| `ProcessorPHNX.py` | ~300 | PhoenixAssistant class copy for bg processing | 🔴 Critical |
| `QueueManagerPHNX.py` | ~200 | Audio chunk queue management | 🟢 Good |
| `TimeBasedHandlePHNX.py` | ~1400 | Timer, Alarm, Reminder, Schedule handlers | 🟡 Medium |
| `TimeBasedRunPHNX.py` | ~500 | Background time checker loop | 🟡 Medium |
| `PersonalManagerPHNX.py` | ~470 | Project/Goal/Todo tracking | 🟢 Good |
| `OllamaHelperPHNX.py` | ~250 | LLM integration (Ollama/Mistral) | 🟢 Good |

### 📁 bgprogs/ Directory (Background Processes)

| File | Purpose | Notes |
|------|---------|-------|
| `battery_monitor.pyw` | Battery monitoring | Silent .pyw window |
| `time_monitor.pyw` | Time-based triggers | Alarms, reminders |
| `voice_command_processor.py` | Audio transcription | Whisper-based |

### 📁 data/ Directory

| File | Purpose |
|------|---------|
| `intents.json` | **THE BRAIN** - All patterns, tags, responses (~2000 lines) |
| `TimeData.json` | Active timers, alarms, reminders, schedules |
| `PersonalManager.json` | Projects, goals, todos |
| `songs.txt` | User's saved song list |
| `remember.json` | Stored memory/notes |

### 📁 Other Directories

| Directory | Purpose |
|-----------|---------|
| `assets/img/` | GUI indicator images (green.png, red.png) |
| `assets/sound/` | Startup sounds, background music |
| `NetMonitor/` | PyQt5 network speed widget |
| `batch/` | Windows batch launchers |
| `scripts/` | Utility scripts |
| `tests/` | Test files |
| `trials/` | Experimental code (can be cleaned) |

---

## Core Components Deep Dive

### 1. SpeechEngine (HelperPHNX.py)

**Current Implementation:**
```python
class SpeechEngine:
    def __init__(self):
        self.lock = threading.Lock()  # Thread-safe
        self.voice_id = voices[1].id  # Female voice
        self.rate = 174
        
    def speak(self, audio, speed=174):
        # Creates fresh pyttsx3 engine each call (Windows workaround)
        # Replaces "sir" with random honorifics
        engine = pyttsx3.init("sapi5")
        engine.say(audio)
        engine.runAndWait()
```

**Issues:**
- Creates new engine every call (memory overhead)
- Windows SAPI5 specific
- No queue for overlapping speech

### 2. VoiceRecognition (HelperPHNX.py)

**Current Implementation:**
```python
class VoiceRecognition:
    # Uses Faster-Whisper for offline
    # Falls back to Google Speech Recognition
    # VAD (Voice Activity Detection) for continuous listening
    
    self.ENERGY_THRESHOLD = 150  # For fan noise filtering
    self.MIN_SILENCE_DURATION = 0.8  # Seconds to trigger processing
```

**Technologies Used:**
- `faster_whisper` - Offline STT (small model, int8)
- `webrtcvad` - Voice Activity Detection
- `speech_recognition` - Fallback to Google
- `pyaudio` - Audio capture

### 3. Intent Matching (main_assistant.py)

**Algorithm:**
```python
def _get_best_matching_intent(self, sent):
    # Uses SequenceMatcher for fuzzy matching
    # Compares against all patterns in intents.json
    # Returns best match if > 65% similarity
    
    best_tag, highest_probability = max(
        (tag, self._getSentProbability(sent, patterns))
        for tag, patterns in self.tag_to_patterns.items()
    )
    
    if highest_probability > 65:
        return {"tag": best_tag, "response": ...}
```

**Limitations:**
- Simple string similarity, not semantic
- No machine learning
- Fixed threshold

### 4. UtilitiesPHNX.py (THE BIG ONE)

**Categories of Functions:**
```
App Management:
├── open_brave(), open_arc(), open_code(), open_file_explorer()
├── close_tab(), close_all_py(), close_bg_py()
├── OpenAppHandler, CloseAppHandler classes

System Control:
├── shutD(), restarT(), sleeP(), hibernatE()
├── restart_phoenix()

Window Management:
├── minimize_window(), maximize_window(), toggle_fullscreen()
├── pin_wind(), move_window()
├── switch_desk(), desKtoP() (virtual desktops)

Media:
├── play_random_song(), play_pause_action()
├── add_song(), delete_song(), view_songs()

Volume/Brightness:
├── adjust_volume(), mute_speaker(), unmute_speaker()
├── adjust_brightness()

Information:
├── tim(), date_day(), battery_check()
├── weather_check() (uses Open-Meteo API)

Web:
├── search_browser(), search_youtube(), search_instagram()
├── open_google(), open_linkedin(), open_github()

Automation:
├── type_text(), press_key()
├── screenshot()
```

---

## IGRS (Igris) Sibling Project

**Location:** `W:\workplace-1\IGRS`

### What is IGRS?

IGRS is a more modern, AI-powered assistant with:
- **Different architecture** - Uses cloud LLMs (Cohere, Groq)
- **Better voice** - Uses Edge TTS (neural voices)
- **GUI focused** - Has a proper GUI dashboard
- **Decision-making model** - AI classifies intent, not pattern matching

### IGRS Structure

```
IGRS/
├── main_voice.py        # Voice mode entry point
├── main_text.py         # Text mode entry point
├── run_assistant.py     # Launcher with menu
│
├── Backend/
│   ├── Model.py         # Decision-making model (Cohere)
│   ├── ModelManager.py  # Multi-model support
│   ├── TextToSpeech.py  # Edge TTS (neural voices) ← BETTER
│   ├── SpeechToText.py  # Selenium + Chrome WebSpeechAPI
│   ├── Automation.py    # App control, YouTube, system
│   ├── Chatbot.py       # Conversation handling
│   ├── RealtimeSearchEngine.py  # Web search
│   └── ImageGeneration.py
│
├── Frontend/
│   └── Graphics/        # Animation assets
│
├── GUI/
│   ├── MainDashboard/
│   ├── MessageBox/
│   └── ScreenEdgeDock/
│
└── Settings/
```

### IGRS Key Differences

| Feature | Phoenix | IGRS |
|---------|---------|------|
| **Intent Classification** | Pattern matching (65% threshold) | LLM-based (Cohere/Groq) |
| **Text-to-Speech** | pyttsx3 (SAPI5) | Edge TTS (neural voices) |
| **Speech-to-Text** | Whisper/Google | Chrome WebSpeechAPI |
| **Architecture** | Multi-process queue | Single-process async |
| **Offline** | Partial (Whisper) | Requires internet |
| **AI Integration** | Optional Ollama | Required (Cohere API) |

---

## Voice Logic Comparison

### Phoenix Voice (pyttsx3 - SAPI5)

```python
# HelperPHNX.py
engine = pyttsx3.init("sapi5")
engine.setProperty("voice", voices[1].id)  # Female voice
engine.setProperty("rate", 174)
engine.say(audio)
engine.runAndWait()
```

**Pros:** Offline, simple  
**Cons:** Robotic, Windows-only

### IGRS Voice (Edge TTS - Neural)

```python
# Backend/TextToSpeech.py
import edge_tts
import pygame

VOICE = "en-AU-WilliamNeural"  # Neural voice

async def TextToAudioFile(text):
    communicate = edge_tts.Communicate(text, AssistantVoice, 
                                        pitch="+5Hz", rate="+13%")
    await communicate.save("Data/speech.mp3")

def TTS(Text):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
```

**Pros:** Natural-sounding neural voices, customizable pitch/rate  
**Cons:** Requires internet (downloads voice), async complexity

### Recommendation: Use Edge TTS in Phoenix

Edge TTS is a **significant upgrade** - natural voices, multiple accents, pitch/rate control. It requires internet but produces far better output than SAPI5.

---

## Data Flow Diagrams

### Voice Command Processing Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                     VOICE COMMAND FLOW                           │
└──────────────────────────────────────────────────────────────────┘

  User Speaks
       │
       ▼
┌─────────────────┐
│  Microphone     │
│  (PyAudio)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│  VAD Detection  │──NO──│  Ignore Chunk   │
│  (webrtcvad)    │      │  (background)   │
└────────┬────────┘      └─────────────────┘
         │
         YES (speech detected)
         │
         ▼
┌─────────────────┐
│  Audio Buffer   │
│  (collect until │
│   silence)      │
└────────┬────────┘
         │
         ▼ (0.6s silence)
┌─────────────────┐      ┌─────────────────┐
│  Whisper STT    │──OR──│  Google STT     │
│  (offline)      │      │  (online)       │
└────────┬────────┘      └─────────────────┘
         │
         ▼
┌─────────────────┐
│  Text           │
│  Transcription  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│  Wake Word?     │──NO──│  Ignore         │
│  ("phoenix")    │      │  (unless loop)  │
└────────┬────────┘      └─────────────────┘
         │
         YES
         │
         ▼
┌─────────────────┐
│  Remove Wake    │
│  Word & Preproc │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Intent Matching (intents.json)             │
│  SequenceMatcher: best pattern match        │
│  if similarity > 65% → tag found            │
└─────────────────────┬───────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│  MATCHED        │      │  NOT MATCHED    │
│  Execute action │      │  loop = False   │
│  Speak response │      │  Keep listening │
│  loop = True    │      └─────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Action Map     │
│  tag → function │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  UtilitiesPHNX  │
│  Execute func() │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SpeechEngine   │
│  speak(response)│
└─────────────────┘
```

---

## Code Quality Assessment

### ✅ What's Good

1. **Modular Structure** - Helpers separated from main logic
2. **Queue-based IPC** - Modern multiprocessing approach
3. **Offline Support** - Whisper integration
4. **Rich Feature Set** - 100+ commands work
5. **Documentation** - Good README exists

### 🔴 Issues to Fix

| Issue | Location | Severity |
|-------|----------|----------|
| **Hardcoded paths** | load.py, UtilitiesPHNX.py | High |
| **Duplicate code** | main_assistant.py ↔ ProcessorPHNX.py | High |
| **No config file** | Settings scattered everywhere | High |
| **Giant files** | UtilitiesPHNX.py (3300 lines) | Medium |
| **Inconsistent naming** | tim(), sleeP(), shutD() | Medium |
| **No error handling** | Many try/except with pass | Medium |
| **No type hints** | Most functions | Low |
| **No tests** | Minimal test coverage | Medium |

### 🟡 Technical Debt

1. **pyttsx3 engine recreation** - Creates new engine each speak()
2. **Blocking speech** - Can't queue multiple utterances
3. **Pattern matching limits** - Fuzzy match, not semantic
4. **Windows-only** - pywin32, pyvda dependencies
5. **Internet dependency** - Google STT, weather, searches

---

## Refactoring Priorities

### Phase 1: Foundation (Week 1-2)

1. **Create config.py** - Centralize all settings
   ```python
   # config.py
   WAKE_WORDS = ["phoenix", "finish", "buddy"]
   ENERGY_THRESHOLD = 150
   MIN_SILENCE = 0.6
   WHISPER_MODEL = "small"
   VOICE_ENGINE = "edge_tts"  # or "pyttsx3"
   ```

2. **Fix hardcoded paths** - Use `pathlib` and relative paths

3. **Merge ProcessorPHNX.py into main_assistant.py** - Remove duplication

### Phase 2: Voice Upgrade (Week 3-4)

1. **Integrate Edge TTS** from IGRS
   - Natural voices
   - Async playback
   - Voice customization

2. **Improve Whisper pipeline**
   - Pre-load model at startup
   - Smaller model option for speed
   - Better VAD tuning

### Phase 3: Intelligence (Week 5-6)

1. **Add semantic intent matching**
   - Use sentence transformers
   - OR integrate Ollama properly
   - Fall back to pattern matching

2. **Consolidate intent system**
   - Reduce patterns in intents.json
   - Use embeddings for similarity

### Phase 4: Clean Architecture (Week 7-8)

1. **Split UtilitiesPHNX.py**
   ```
   utils/
   ├── app_control.py
   ├── system_control.py
   ├── media_control.py
   ├── window_control.py
   ├── web_control.py
   └── information.py
   ```

2. **Add proper logging**
3. **Add type hints**
4. **Write unit tests**

### Phase 5: Polish (Week 9+)

1. **Cross-platform preparation**
2. **Plugin system**
3. **Better GUI**
4. **Installer/packaging**

---

## Modernization Roadmap

### Architecture Goals

```
CURRENT:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ load.py     │────▶│ Queue       │────▶│ MainPHNX    │
│ (launcher)  │     │ Server      │     │ (monolith)  │
└─────────────┘     └─────────────┘     └─────────────┘

PROPOSED:
┌─────────────────────────────────────────────────────────────────┐
│                      PHOENIX CORE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐                                          │
│  │  config.py       │◀─── Single source of truth               │
│  └──────────────────┘                                          │
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │  Voice Input     │────▶│  Intent Engine   │                 │
│  │  - VAD           │     │  - Semantic      │                 │
│  │  - Whisper       │     │  - Pattern       │                 │
│  │  - Continuous    │     │  - LLM fallback  │                 │
│  └──────────────────┘     └────────┬─────────┘                 │
│                                    │                            │
│                           ┌────────▼─────────┐                 │
│                           │  Action Router   │                 │
│                           │  - Plugin system │                 │
│                           │  - Async exec    │                 │
│                           └────────┬─────────┘                 │
│                                    │                            │
│  ┌──────────────────┐     ┌────────▼─────────┐                 │
│  │  Voice Output    │◀────│  Response Gen    │                 │
│  │  - Edge TTS      │     │  - Templates     │                 │
│  │  - pyttsx3 fallb │     │  - LLM natural   │                 │
│  └──────────────────┘     └──────────────────┘                 │
│                                                                 │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │  Plugins/        │     │  Background/     │                 │
│  │  - Apps          │     │  - Battery       │                 │
│  │  - System        │     │  - Timers        │                 │
│  │  - Media         │     │  - Reminders     │                 │
│  │  - Custom        │     │  - Schedules     │                 │
│  └──────────────────┘     └──────────────────┘                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Offline-First Strategy

### Current Online Dependencies

| Feature | Current | Offline Alternative |
|---------|---------|---------------------|
| Speech-to-Text | Google API | ✅ Whisper (already integrated) |
| Text-to-Speech | pyttsx3 (offline) | ✅ Already offline |
| Weather | Open-Meteo API | ❌ Requires caching/offline data |
| YouTube Play | pywhatkit (online) | ❌ Needs local music library |
| Web Search | Google | ❌ Offline not possible |
| LLM/Chat | Ollama (local) | ✅ Ollama integration exists |

### Offline Enhancements

1. **Pre-cache Edge TTS voices** - Download commonly used phrases
2. **Local music library** - Index local files instead of YouTube
3. **Weather caching** - Cache last known weather, show "stale" indicator
4. **Offline intent matching only** - Don't call LLM unless needed
5. **Graceful degradation** - Announce when features unavailable offline

### Recommended Stack for Offline

```
Speech Input:  faster-whisper (✓ works)
Speech Output: pyttsx3 (offline) OR pre-cached Edge TTS
Intent:        Local pattern matching + optional Ollama
Actions:       All local system control works offline
Data:          SQLite instead of JSON for better querying
```

---

## Files to Delete/Archive

### Safe to Delete (trials/)
```
trials/
├── try1.py through try8.py  ← Experimental, archive
├── shreyu.zip               ← Old archive
├── pdfCon.py                ← Unused
```

### Redundant/Duplicate
```
ProcessorPHNX.py ← Duplicate of PhoenixAssistant from main_assistant.py
Multiple .md guides ← Consolidate into one
```

### Check Before Deleting
```
cmd_gui.py ← Check if used
SortPythonProgram.py ← Utility, may be needed
apply_queue_fix.py ← One-time fix script
```

---

## Quick Reference: Key Entry Points

| What You Want | Run This |
|---------------|----------|
| Full launch (all features) | `python load.py` |
| Modern launch (queue-based) | `python launch_phoenix.py` |
| Voice assistant only | `python main_assistant.py` |
| Test voice recognition | `python test_voice_command.py` |
| Test speaking | `python test_speak.py` |

---

## Next Steps

1. **Read this document thoroughly**
2. **Decide on Phase 1 priorities**
3. **Create config.py first**
4. **Set up proper git branching** (feature branches)
5. **Start refactoring helpers/ one file at a time**

---

*This document will be updated as refactoring progresses.*
