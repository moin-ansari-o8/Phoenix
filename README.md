# Phoenix - Desktop Voice Assistant

**Version:** 5.9.0 | **Platform:** Windows | **License:** Apache 2.0

Phoenix is a voice-controlled desktop assistant for Windows. It listens to your voice commands (or typed commands) and performs tasks like opening/closing apps, adjusting volume and brightness, setting alarms/timers/reminders, playing music, checking weather, managing virtual desktops, and more.

Think of it like Siri or Google Assistant, but built specifically for a Windows desktop and fully customizable because you own the source code.

---

## Table of Contents

- [How Phoenix Works (The Big Picture)](#how-phoenix-works-the-big-picture)
- [Flow of the Program](#flow-of-the-program)
- [Project Structure](#project-structure)
- [Core Files Explained](#core-files-explained)
- [Features](#features)
- [How Voice Commands Work](#how-voice-commands-work)
- [Data Files](#data-files)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [How to Run](#how-to-run)
- [Voice vs Chat Mode](#voice-vs-chat-mode)
- [Example Commands](#example-commands)
- [Network Monitor Widget](#network-monitor-widget)
- [Future Enhancements](#future-enhancements)
- [Contributing](#contributing)
- [License](#license)

---

## How Phoenix Works (The Big Picture)

At its core, Phoenix does three things in a loop:

1. **Listens** to your voice through the microphone (using Google Speech Recognition).
2. **Understands** what you said by matching your words against a set of known patterns stored in a JSON file.
3. **Acts** on the matched intent - whether that's opening an app, telling you the time, or setting a timer.

Phoenix is not a single script. It is a collection of programs that work together:

- A **main listener** that processes your voice/text commands.
- **Background processes** that independently monitor battery status and handle time-based triggers (alarms, reminders, schedule announcements).
- A **launcher** that starts everything in the right order.

---

## Flow of the Program

When you start Phoenix, here is exactly what happens:

### Option A: Full Launch (using `load.py`)

`load.py` is the launcher. It starts **three separate processes**:

1. **`bgprogs/battery_monitor.pyw`** - Battery Monitor (runs silently in background)
   - Continuously checks your laptop's battery percentage and charging status.
   - Announces battery levels at specific thresholds (e.g., 50%, 75%, 100% when charging; 85%, 50%, 35%, 25% when on battery).
   - Alerts you when to plug in or unplug the charger.

2. **`bgprogs/time_monitor.pyw`** - Time & Schedule Manager (runs silently in background)
   - Checks and triggers alarms, timers, reminders, and scheduled events.
   - Announces the current time every hour.
   - Announces a water-drinking reminder on startup.
   - Runs periodic checks on your projects (via the Personal Manager).

3. **`main_assistant.py`** - The main Voice Assistant (runs in the foreground)
   - This is the program you interact with.
   - Listens for voice commands (activated by saying "Phoenix").
   - Processes your command, finds the matching intent, and executes the corresponding action.

Before launching these three, `load.py` also:
- Terminates any previously running background Python processes (to avoid duplicates).
- Plays a startup greeting based on the time of day ("Good morning", "Good afternoon", etc.).

### Option B: Quick Start (using `main_assistant.py` directly)

If you just want the voice assistant without battery monitoring and time-based features, you can run `main_assistant.py` directly. This gives you the full voice/chat command experience but without background monitoring.

---

## Project Structure

```
Phoenix/
|-- main_assistant.py              # Main voice assistant (the brain)
|-- load.py                   # Launcher - starts everything
|
|-- bgprogs/                  # Background processes
|   |-- battery_monitor.pyw       # Battery monitor
|   |-- time_monitor.pyw         # Time/alarm/reminder/schedule handler
|
|-- helpers/                  # All the logic lives here
|   |-- HelperPHNX.py         # Speech engine, voice recognition, GUI
|   |-- UtilitiesPHNX.py      # 100+ utility functions (open/close apps, volume, etc.)
|   |-- TimeBasedHandlePHNX.py    # Timer, alarm, reminder, schedule logic
|   |-- TimeBasedRunPHNX.py       # Runs time-based checks in a loop
|   |-- PersonalManagerPHNX.py    # Project/goal/todo tracker
|   |-- OllamaHelperPHNX.py      # LLM integration (Ollama/Mistral) for NLP
|
|-- data/                     # JSON data storage
|   |-- intents.json          # All voice command patterns and responses
|   |-- TimeData.json         # Alarms, timers, reminders, schedules
|   |-- PersonalManager.json  # Projects, goals, todos
|   |-- songs.txt             # Your saved song names
|   |-- remember.json         # Stored memory/notes
|
|-- NetMonitor/               # Network speed monitor widget
|   |-- network_monitor.py    # PyQt5 edge widget showing upload/download speed
|
|-- assets/
|   |-- img/                  # GUI indicator images (green.png, red.png)
|   |-- sound/                # Startup sounds and background music
|
|-- scripts/                  # Utility scripts
|   |-- phoenix.bat           # Batch launcher
|
|-- batch/                    # Batch files
|   |-- main.bat              # Main batch launcher
|   |-- on_boot_startup.bat   # Auto-start on Windows boot
|
|-- tests/                    # Test files
|-- Requirements.txt          # pip dependencies
|-- pyproject.toml            # Project config (uv/pip compatible)
```

---

## Core Files Explained

### `main_assistant.py` - The Brain

This is the file you interact with. Here is what it does step by step:

1. **Initializes** the speech engine, voice recognition, GUI, and all handler classes.
2. **Enters a loop** where it continuously listens for your voice (or reads typed input).
3. When you say something, it **preprocesses** the text (removes the wake word "Phoenix", splits compound commands with "and").
4. It **matches your command** against patterns in `intents.json` using a similarity algorithm (`SequenceMatcher`). Each pattern belongs to a "tag" (like `"saytime"`, `"openelse"`, `"playsong"`).
5. If a match is found above a confidence threshold (65%), it **executes the corresponding action** via the `_execute_action` method, which maps tags to functions in `UtilitiesPHNX.py`.
6. If the command is conversational (greetings, jokes, etc.), Phoenix picks a random response from the intents file and speaks it.

### `helpers/HelperPHNX.py` - Speech & Recognition

Contains three classes:

- **`SpeechEngine`** - Converts text to speech using `pyttsx3` (Windows SAPI5 voices). Adds personality by randomly replacing "sir" with fun honorifics like "boss", "captain", "commander", "sensei", etc.
- **`VoiceRecognition`** - Listens to the microphone using the `speech_recognition` library and converts audio to text via Google Speech Recognition (requires internet).
- **`VoiceAssistantGUI`** - A tiny Tkinter overlay in the corner of your screen. Shows a green dot when listening and a red dot when processing your command.

### `helpers/UtilitiesPHNX.py` - The Action Library

This is the largest file (~3300 lines) and contains 100+ functions that Phoenix can call. Some highlights:

- **App management:** Open/close specific apps (browser, VS Code, file explorer, etc.)
- **Window control:** Minimize, maximize, hide, fullscreen, pin on top, move between virtual desktops
- **System control:** Shutdown, restart, sleep, hibernate the PC
- **Media:** Play/pause music, play songs from YouTube, suggest songs, manage a song list
- **Adjustments:** Brightness up/down, volume up/down, mute/unmute speakers
- **Information:** Current time, date, weather (via Open-Meteo API), battery status
- **Browsing:** Search Google, YouTube, Instagram; open specific websites (GitHub, LinkedIn, Flipkart, Amazon)
- **Productivity:** Set timers, alarms, reminders; manage schedules
- **Virtual desktops:** Switch between desktops, setup predefined desktop layouts (study, alpha, trash, extra)
- **Keyboard automation:** Type text, press keys, keyboard shortcuts
- **Screenshots, Bluetooth toggle, Hotspot toggle**

### `helpers/TimeBasedHandlePHNX.py` - Timer/Alarm/Reminder/Schedule

Contains four handler classes:

- **`TimerHandle`** - Set countdown timers ("set a timer for 5 minutes"). Timers are saved to `TimeData.json` and a background thread watches for when they expire.
- **`AlarmHandle`** - Set alarms for specific times ("set an alarm for 7 AM"). Supports one-time and repeating alarms, with labels.
- **`ReminderHandle`** - Set reminders with a message and date/time ("remind me to call mom at 3 PM").
- **`ScheduleHandle`** - Define a daily schedule with timed messages (e.g., "workout at 4:30 AM", "coding session at 7 AM").

### `helpers/PersonalManagerPHNX.py` - Project & Goal Tracker

A personal management system that tracks:

- **Projects** - Create, update, and get status of projects. Tracks timeline entries and flags stale projects.
- **Goals** - Long-term goal tracking.
- **Todos** - Today's tasks, tomorrow's tasks, and completed tasks.

Data is stored in `data/PersonalManager.json`.

### `helpers/OllamaHelperPHNX.py` - LLM Integration

Optional integration with a locally running [Ollama](https://ollama.ai/) server (Mistral 7B model). Used for:

- Extracting intent from natural language when pattern matching is not enough.
- Parsing project updates from spoken commands.
- Generating natural language responses.

This is optional - Phoenix works fine without Ollama running.

---

## Features

| Category | What Phoenix Can Do |
|---|---|
| **Voice Control** | Listen to voice commands, wake word activation ("Phoenix"), switch to chat mode |
| **App Management** | Open/close any app (browsers, VS Code, file explorer, drives, etc.) |
| **Window Control** | Minimize, maximize, fullscreen, hide, pin on top, move windows between desktops |
| **System Control** | Shutdown, restart, sleep, hibernate your PC. Restart Phoenix itself |
| **Volume & Brightness** | Increase/decrease volume and brightness by percentage |
| **Music** | Play songs from YouTube, play/pause, suggest songs, maintain a song list |
| **Time & Date** | Tell current time, date, and day |
| **Weather** | Get current weather for any location (using Open-Meteo API, no API key needed) |
| **Battery Monitor** | Background monitoring with spoken alerts at key battery levels |
| **Timers** | Set countdown timers ("set timer for 10 minutes") |
| **Alarms** | Set alarms for specific times, view and delete alarms |
| **Reminders** | Set reminders with custom messages, date, and time |
| **Schedule** | Daily schedule with timed announcements throughout the day |
| **Web Search** | Search Google, YouTube, Instagram from voice commands |
| **Shopping** | Quick search on Flipkart, Amazon |
| **Virtual Desktops** | Switch between Windows virtual desktops, setup predefined layouts |
| **Keyboard Control** | Type text, press key combos, navigate tabs |
| **Screenshots** | Take screenshots on command |
| **Personal Manager** | Track projects, goals, and daily todos |
| **Network Monitor** | Desktop edge widget showing real-time upload/download speed (PyQt5) |
| **Bluetooth & Hotspot** | Toggle Bluetooth and mobile Hotspot |
| **Personality** | Random honorifics, jokes, greetings, casual conversation |

---

## How Voice Commands Work

Phoenix uses an **intent-based** system. Here is how it understands you:

### 1. The Intents File (`data/intents.json`)

This JSON file contains a list of "intents". Each intent has:
- **`tag`** - A unique identifier (e.g., `"saytime"`, `"playsong"`, `"open"`)
- **`patterns`** - A list of example phrases a user might say (e.g., `"what time is it"`, `"tell me the time"`)
- **`responses`** - A list of possible replies Phoenix can speak (a random one is picked)

Example from the file:
```json
{
  "tag": "saytime",
  "patterns": ["what time is it", "tell me the time", "current time"],
  "responses": ["Let me check the time for you."]
}
```

### 2. The Matching Algorithm

When you say something, Phoenix compares your words against every pattern in every intent using Python's `SequenceMatcher` (a fuzzy string similarity algorithm). It calculates a similarity score (0-100%) for each pattern and picks the intent with the highest score.

- If the best match is **above 65%** similarity, Phoenix accepts it as the correct intent.
- Some tags (like `"openelse"`, `"playsong"`) are accepted even at lower confidence because they need flexible matching.

### 3. The Action Map

Once an intent is matched, the tag is looked up in an action map inside `main_assistant.py`. This map connects each tag to a specific function. For example:
- `"saytime"` calls `utility.tim()` which speaks the current time.
- `"playsong"` calls `utility.play_random_song(query)` which searches YouTube and plays the song.
- `"open"` delegates to `OpenAppHandler` which maps app names to opener functions.

---

## Data Files

All persistent data is stored as JSON in the `data/` folder:

| File | Purpose |
|---|---|
| `intents.json` | All voice command patterns, tags, and responses (~2000 lines) |
| `TimeData.json` | Active alarms, timers, reminders, and daily schedule |
| `PersonalManager.json` | Projects, goals, and todo items |
| `songs.txt` | Your saved list of song names |
| `remember.json` | Things you asked Phoenix to remember |

---

## Prerequisites

- **Operating System:** Windows 10 or later
- **Python:** 3.10 or higher
- **Microphone:** Required for voice mode
- **Internet:** Required for Google Speech Recognition and weather features

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd Phoenix
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

```powershell
# PowerShell
.\.venv\Scripts\Activate.ps1

# Command Prompt
.\.venv\Scripts\activate.bat
```

### 4. Install dependencies

Using pip:
```bash
pip install -r Requirements.txt
```

Or using [uv](https://github.com/astral-sh/uv) (faster):
```bash
uv sync
```

> **Note:** Some dependencies like `pyaudio` may require additional setup on Windows. If `pip install pyaudio` fails, try: `pip install pipwin && pipwin install pyaudio`

---

## How to Run

### Full Launch (recommended)

This starts everything - battery monitor, time-based features, and the voice assistant:

```bash
python load.py
```

### Voice Assistant Only

If you just want to talk to Phoenix without background monitoring:

```bash
python main_assistant.py
```

When Phoenix starts, you will see a small terminal banner:

```
   +-+-+-+-+-+-+-+
   |P|H|O|E|N|I|X|
   +-+-+-+-+-+-+-+
 ========================================
```

A green dot appears in the bottom-right corner of your screen when Phoenix is listening.

---

## Voice vs Chat Mode

Phoenix supports two input modes:

| Mode | How to Use | Switch Command |
|---|---|---|
| **Voice Mode** (default) | Speak your command after saying "Phoenix" | Say "switch to chat" to switch |
| **Chat Mode** | Type commands directly in the terminal | Type "switch to voice" or "wake up" or "stv" to switch |

In voice mode, Phoenix requires you to say the wake word **"Phoenix"** before your command. For example:
- "Phoenix, what time is it?"
- "Phoenix, open browser"
- "Phoenix, set a timer for 5 minutes"

In chat mode, you type commands directly without the wake word.

---

## Example Commands

Here are some things you can say (or type) to Phoenix:

**App Management:**
- "Phoenix, open browser" / "open VS Code" / "open file explorer"
- "Phoenix, close browser" / "close code"

**System:**
- "Phoenix, shutdown the PC" / "restart the PC" / "put PC to sleep"
- "Phoenix, restart phoenix"

**Information:**
- "Phoenix, what time is it?"
- "Phoenix, what's the date today?"
- "Phoenix, check battery"
- "Phoenix, weather in Mumbai"

**Media:**
- "Phoenix, play Shape of You song"
- "Phoenix, suggest a song"
- "Phoenix, play pause" / "next song"

**Adjustments:**
- "Phoenix, increase volume by 20"
- "Phoenix, decrease brightness by 30"
- "Phoenix, mute speakers"

**Productivity:**
- "Phoenix, set a timer for 10 minutes"
- "Phoenix, set an alarm for 7 AM"
- "Phoenix, remind me to take medicine at 3 PM"

**Window Management:**
- "Phoenix, minimize" / "maximize" / "fullscreen" / "hide"
- "Phoenix, switch to desktop 2"
- "Phoenix, pin window"

**Web:**
- "Phoenix, search how to learn Python"
- "Phoenix, search YouTube for cooking recipes"

**Conversation:**
- "Phoenix, how are you?"
- "Phoenix, tell me a joke"
- "Phoenix, who made you?"

---

## Network Monitor Widget

Phoenix includes a standalone network speed monitor (`NetMonitor/network_monitor.py`). It is a small PyQt5 widget that sits on the edge of your screen and shows real-time upload/download speeds. It launches automatically as a background thread when `main_assistant.py` starts.

---

## Future Enhancements

- More intuitive and user-friendly GUI
- Reinforcement learning for better command understanding
- Deeper Ollama/LLM integration for natural conversations
- Cross-platform support (Linux, macOS)
- Plugin system for extending functionality

### J.A.R.V.I.S Custom Voice Integration (Planned)
**Goal:** Integrate the original J.A.R.V.I.S voice (Paul Bettany) from the Marvel Cinematic Universe using a custom Piper TTS model.
- **Dataset:** Utilize the [J.A.R.V.I.S Kaggle dataset](https://www.kaggle.com/datasets/fotiemconstant/jarvis-dataset).
- **Data Preparation:** Extract clean `.wav` audio clips from the dataset and use an AI transcription tool (like OpenAI's Whisper) to generate a paired text-to-audio dataset in LJSpeech format.
- **Model Training:** Use the Piper TTS training scripts to fine-tune an existing English model on the J.A.R.V.I.S dataset for optimal, offline, lightning-fast local inference.
- **Integration:** Export the resulting `.onnx` and `.json` files into the `piper_models` directory and add a new "Jarvis" profile directly in `core/config.json`.

### Conversational Interruption (ChatGPT Voice Mode Style) (Planned)
**Goal:** Allow the user to interrupt Phoenix seamlessly while it is speaking, ending the audio instantly and processing the new prompt.
- **Asynchronous Audio:** Migrate from blocking TTS engines (like `winmm` `mciSendString`) to asynchronous playback streams that support a mid-sentence `stop()` trigger.
- **Echo Cancellation / Hotkey:** Keep the microphone "hot" while speaking by using Software Acoustic Echo Cancellation (AEC) or text-matching to ignore self-speech. Alternatively, add a global push-to-interrupt hotkey (e.g., `Spacebar`).

---

## Contributing

Contributions are welcome! Here are some ways you can help:

1. **Report Bugs** - If you find a bug, create an issue on GitHub.
2. **Suggest Features** - Open an issue to discuss ideas for new features.
3. **Submit Pull Requests** - Fix bugs or add features and submit a PR.
4. **Improve Documentation** - Help make the docs clearer and more comprehensive.

---

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
