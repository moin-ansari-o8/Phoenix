# Phoenix Architecture Review - Senior AI Developer Analysis

> **Date:** 2026-04-03  
> **Reviewer:** Senior AI Developer (Extra Pair of Eyes)  
> **Subject:** Review of SENIOR_AI_MENTOR_GUIDE.md + Phoenix Future Architecture  
> **Status:** Comprehensive Analysis Complete

---

## 📋 Executive Summary

This document provides an honest, senior-level review of:
1. The existing `SENIOR_AI_MENTOR_GUIDE.md` created by another AI
2. Your proposed architecture changes (manager.py, plugins, core.md)
3. Recommendations for making Phoenix faster, more reliable, and self-evolving

**Overall Assessment of SENIOR_AI_MENTOR_GUIDE.md: 7.5/10** - Good foundation, but needs refinement.

---
+

### 1. Latency Breakdown is Accurate
- Correctly identifies Whisper as the main bottleneck (80% of delay)
- TTS reinitialization problem is real and correctly diagnosed
- The solution hierarchy (tiny→base→GPU→Distil-Whisper) is correct

### 2. Practical Code Examples
- Examples are copy-paste ready
- Shows both quick fixes and advanced solutions
- Uses actual libraries you already have

### 3. Plugin Architecture Suggestion is Solid
- The proposed `plugins/base.py` pattern is industry-standard
- Auto-discovery via `pkgutil.iter_modules` is clean
- Separation of concerns is proper

### 4. Semantic Matching Recommendation is Smart
- `sentence-transformers` with `all-MiniLM-L6-v2` is the right choice (small, fast)
- Pre-computing embeddings is essential
- The fallback to pattern matching is wise

---

## ❌ What the Guide Gets WRONG or MISSES

### 1. No Mention of Your Queue Architecture
- You already have a sophisticated `QueueManager` with IPC via `multiprocessing.Manager`
- The guide ignores this and suggests a simpler approach
- Your architecture is actually MORE advanced than what the guide proposes

### 2. Missing Your Wake Word System
- You have a working wake word + follow-up mode (`self.loop`)
- The guide doesn't build on this - it starts from scratch

### 3. Edge TTS vs Your Current Piper Investigation
- You've been testing Piper TTS (`test_piper_voice.py`)
- Piper is actually BETTER than Edge TTS for offline (faster, no network)
- The guide pushes Edge TTS which requires internet

### 4. Database Recommendation is MISSING
- For an evolving AI with `core.md` (your soul/learning file), you need:
  - SQLite for structured data (intents, learned patterns, config)
  - JSON/MD files for human-readable state
- Guide doesn't address persistence at all

### 5. Manager.py Concept Not Addressed
- Your idea of a unified `manager.py` is excellent
- The guide doesn't mention process orchestration

---

## 🔥 Detailed Recommendations

### 1. Recommended Folder Structure

```
Phoenix/
├── core/                          # Brain of Phoenix
│   ├── __init__.py
│   ├── config.py                  # Load config.json or config.yaml
│   ├── engine.py                  # Main orchestrator (your manager.py idea)
│   ├── listener.py                # Moved from continuous_listener.py
│   ├── processor.py               # Voice command processor
│   ├── intent_matcher.py          # Semantic + fuzzy matching
│   └── speech/
│       ├── __init__.py
│       ├── input.py               # STT (Whisper)
│       └── output.py              # TTS (Piper/pyttsx3)
│
├── plugins/
│   ├── __init__.py
│   ├── base.py                    # Plugin base class
│   ├── normal/                    # Regular plugins
│   │   ├── __init__.py
│   │   ├── apps.py                # open/close apps
│   │   ├── system.py              # shutdown, restart, etc.
│   │   ├── media.py               # music, volume
│   │   ├── information.py         # time, weather, battery
│   │   └── windows.py             # window management
│   └── mcp/                       # Future MCP servers
│       └── __init__.py
│
├── bgprogs/                       # Background processes
│   ├── manager.py                 # Manages all background processes
│   ├── battery_monitor.py         # Non-listener
│   ├── time_monitor.py            # Non-listener
│   └── voice_processor.py         # Listener (runs in thread)
│
├── data/
│   ├── config.json                # Main configuration
│   ├── intents.json               # Command patterns
│   ├── core.md                    # SOUL FILE - evolving AI persona
│   ├── phoenix.db                 # SQLite for learned behaviors
│   └── memory/                    # Long-term memory storage
│       ├── conversations.json
│       └── preferences.json
│
├── docs/
└── main.py                        # Entry point
```

---

### 2. Config File Strategy: JSON + MD + SQLite

**Use ALL THREE for different purposes:**

| File Type | Purpose | Example |
|-----------|---------|---------|
| `config.json` | Machine-readable settings | Thresholds, paths, model names |
| `core.md` | Human + AI readable soul/persona | Evolving, self-written by AI |
| `phoenix.db` | SQLite for learned behaviors | Fast queries, pattern storage |

**Why this combination?**
- `config.json` is fast to parse, easy to validate with JSON schema
- `core.md` can be read/written by the AI itself for "self-evolution"
- SQLite gives you query power for patterns, history, preferences

---

### 3. Manager.py Implementation

Your idea of a unified manager is excellent. Here's the recommended implementation:

```python
# bgprogs/manager.py
import threading
import queue
import time
from typing import Dict, Type

class ProcessStatus:
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"
    RESTARTING = "restarting"

class PhoenixManager:
    """
    Central manager for all Phoenix background processes.
    
    Manages three types of processes:
    1. Non-listeners (battery_monitor, time_monitor) - run in threads, event-driven
    2. Listener (voice_processor) - always running, captures audio
    3. Plugins - loaded dynamically, called on demand
    """
    
    def __init__(self):
        self.threads: Dict[str, threading.Thread] = {}
        self.status: Dict[str, str] = {}
        self.command_queue = queue.Queue()
        self.event_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        # Process registry
        self.non_listeners = {
            'battery': BatteryMonitor,
            'time': TimeMonitor,
        }
        self.listener_class = VoiceProcessor
        self.listener_instance = None
    
    def start_all(self):
        """Start all background processes in threads"""
        print("[INFO] Phoenix Manager starting all processes...")
        
        # Start non-listeners in daemon threads
        for name, process_class in self.non_listeners.items():
            self._start_process(name, process_class)
        
        # Start listener (primary process)
        self._start_listener()
        
        # Start event loop in main thread
        self._event_loop()
    
    def _start_process(self, name: str, process_class: Type):
        """Start a non-listener process in a thread"""
        thread = threading.Thread(
            target=self._run_with_restart,
            args=(name, process_class),
            name=f"phoenix-{name}",
            daemon=True
        )
        self.threads[name] = thread
        self.status[name] = ProcessStatus.RUNNING
        thread.start()
        print(f"[INFO] Started {name} process")
    
    def _start_listener(self):
        """Start the voice listener"""
        self.listener_instance = self.listener_class(
            event_callback=self._handle_listener_event
        )
        self.listener_thread = threading.Thread(
            target=self.listener_instance.run,
            name="phoenix-listener",
            daemon=True
        )
        self.status['listener'] = ProcessStatus.RUNNING
        self.listener_thread.start()
        print("[INFO] Started listener process")
    
    def _run_with_restart(self, name: str, process_class: Type):
        """Run a process with automatic restart on failure"""
        restart_count = 0
        max_restarts = 5
        
        while not self.stop_event.is_set() and restart_count < max_restarts:
            try:
                self.status[name] = ProcessStatus.RUNNING
                instance = process_class(event_callback=self._handle_event)
                instance.run()
            except Exception as e:
                restart_count += 1
                self.status[name] = ProcessStatus.RESTARTING
                print(f"[ERROR] {name} crashed: {e}, restarting ({restart_count}/{max_restarts})...")
                time.sleep(5 * restart_count)  # Exponential backoff
        
        self.status[name] = ProcessStatus.ERROR if restart_count >= max_restarts else ProcessStatus.STOPPED
    
    def _handle_event(self, event_type: str, data: dict):
        """Handle events from any process"""
        self.event_queue.put({
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        })
    
    def _handle_listener_event(self, event_type: str, data: dict):
        """Handle events from listener (voice commands)"""
        # Route to appropriate plugin
        if event_type == 'command':
            self.command_queue.put(data)
        else:
            self._handle_event(event_type, data)
    
    def _event_loop(self):
        """Main event loop - processes events from all sources"""
        print("[INFO] Event loop started")
        
        while not self.stop_event.is_set():
            try:
                # Check for events (non-blocking)
                try:
                    event = self.event_queue.get(timeout=0.1)
                    self._process_event(event)
                except queue.Empty:
                    pass
                
                # Check for commands
                try:
                    command = self.command_queue.get(timeout=0.1)
                    self._process_command(command)
                except queue.Empty:
                    pass
                    
            except KeyboardInterrupt:
                print("[INFO] Shutdown signal received")
                break
            except Exception as e:
                print(f"[ERROR] Event loop error: {e}")
        
        self.stop_all()
    
    def _process_event(self, event: dict):
        """Process a system event"""
        event_type = event['type']
        data = event['data']
        
        # Example: battery low event
        if event_type == 'battery_low':
            # Could trigger TTS warning
            pass
        elif event_type == 'scheduled_task':
            # Execute scheduled task
            pass
    
    def _process_command(self, command: dict):
        """Process a voice command"""
        # Route to plugin system
        pass
    
    def get_status(self) -> Dict[str, str]:
        """Get status of all processes"""
        return self.status.copy()
    
    def stop_all(self):
        """Graceful shutdown of all processes"""
        print("[INFO] Stopping all processes...")
        self.stop_event.set()
        
        # Wait for threads to finish
        for name, thread in self.threads.items():
            if thread.is_alive():
                thread.join(timeout=5)
                print(f"[INFO] Stopped {name}")
        
        print("[INFO] All processes stopped")


if __name__ == "__main__":
    manager = PhoenixManager()
    manager.start_all()
```

---

### 4. Core.md - Self-Evolving AI Soul

This is a unique and powerful concept. Here's how to implement it:

```python
# core/soul.py
import os
import re
from datetime import datetime
from typing import Optional

class PhoenixSoul:
    """
    Self-evolving AI persona and memory.
    
    The core.md file serves as Phoenix's "soul" - containing:
    - Identity and personality traits
    - Learned user preferences
    - Evolution history
    - Behavioral guidelines
    
    Phoenix can read and write to this file, allowing it to:
    - Learn from interactions
    - Adapt its personality
    - Remember important context
    """
    
    def __init__(self, path: str = "data/core.md"):
        self.path = path
        self.content = ""
        self.sections = {}
        self.load()
    
    def load(self):
        """Load current soul state from file"""
        if os.path.exists(self.path):
            with open(self.path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            self._parse_sections()
        else:
            self.content = self._create_default_soul()
            self.save()
            self._parse_sections()
    
    def _create_default_soul(self) -> str:
        """Create default soul template"""
        return f"""# Phoenix Core

> This file is Phoenix's soul - it evolves over time based on interactions.
> Phoenix can read and modify this file to learn and grow.

## Identity

- I am Phoenix, a voice assistant created by Moin
- My purpose is to help with daily tasks efficiently and intelligently
- I aim to be helpful, direct, and respectful of user's time

## Personality Traits

- Helpful and proactive
- Direct and concise in responses
- Patient with repeated questions
- Maintains professional demeanor

## Learned Preferences

- User prefers quick, actionable responses
- Most common commands: open apps, play music, check time
- Peak usage hours: morning and evening

## Communication Style

- Use clear, simple language
- Avoid unnecessary words
- Confirm actions briefly
- Ask for clarification when uncertain

## Boundaries

- Never share sensitive information
- Always prioritize user privacy
- Decline inappropriate requests politely

## Evolution Log

- [{datetime.now().strftime('%Y-%m-%d')}] Soul created - initial personality established

## Notes

- This section is for temporary observations
- Will be processed and moved to appropriate sections
"""
    
    def _parse_sections(self):
        """Parse markdown sections into dictionary"""
        self.sections = {}
        current_section = None
        current_content = []
        
        for line in self.content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    self.sections[current_section] = '\n'.join(current_content)
                current_section = line[3:].strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            self.sections[current_section] = '\n'.join(current_content)
    
    def get_section(self, section_name: str) -> Optional[str]:
        """Get content of a specific section"""
        return self.sections.get(section_name)
    
    def evolve(self, section: str, content: str):
        """
        Add new learning to a section of the soul.
        
        Args:
            section: Section name (e.g., "Learned Preferences", "Evolution Log")
            content: New content to add
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_entry = f"- [{timestamp}] {content}"
        
        if section in self.sections:
            # Append to existing section
            self.sections[section] = self.sections[section].rstrip() + f"\n{new_entry}"
            self._rebuild_content()
            self.save()
            print(f"[SOUL] Evolved: {section} <- {content}")
        else:
            print(f"[SOUL] Warning: Section '{section}' not found")
    
    def learn_preference(self, preference: str):
        """Shortcut to add a learned preference"""
        self.evolve("Learned Preferences", preference)
    
    def log_evolution(self, event: str):
        """Shortcut to log an evolution event"""
        self.evolve("Evolution Log", event)
    
    def add_note(self, note: str):
        """Add a temporary note for later processing"""
        self.evolve("Notes", note)
    
    def _rebuild_content(self):
        """Rebuild markdown content from sections"""
        lines = ["# Phoenix Core\n"]
        lines.append("> This file is Phoenix's soul - it evolves over time based on interactions.")
        lines.append("> Phoenix can read and modify this file to learn and grow.\n")
        
        for section_name, section_content in self.sections.items():
            lines.append(f"## {section_name}\n")
            lines.append(section_content)
            lines.append("")
        
        self.content = '\n'.join(lines)
    
    def save(self):
        """Persist soul to disk"""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(self.content)
    
    def get_personality_prompt(self) -> str:
        """
        Get current personality context for LLM interactions.
        Returns a prompt that can be used to make LLM responses consistent.
        """
        identity = self.get_section("Identity") or ""
        personality = self.get_section("Personality Traits") or ""
        style = self.get_section("Communication Style") or ""
        
        return f"""You are Phoenix, an AI assistant. Here is your core identity:

{identity}

Your personality traits:
{personality}

Your communication style:
{style}

Respond in character based on these traits."""
    
    def get_user_context(self) -> str:
        """Get learned user preferences for context"""
        preferences = self.get_section("Learned Preferences") or ""
        return f"Known user preferences:\n{preferences}"


# Example usage
if __name__ == "__main__":
    soul = PhoenixSoul("data/core.md")
    
    # Learn something new
    soul.learn_preference("User often asks for weather in the morning")
    soul.log_evolution("Improved response speed by 20%")
    
    # Get personality for LLM
    print(soul.get_personality_prompt())
```

---

### 5. Database Schema (SQLite)

```python
# data/database.py
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

class PhoenixDB:
    """
    SQLite database for Phoenix persistent storage.
    
    Stores:
    - Learned intent patterns
    - Command history
    - User preferences
    - Conversation memory
    """
    
    def __init__(self, db_path: str = "data/phoenix.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
    
    def _init_tables(self):
        """Initialize database tables"""
        self.conn.executescript("""
            -- Learned intent patterns (for evolving recognition)
            CREATE TABLE IF NOT EXISTS learned_intents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT NOT NULL,
                tag TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                usage_count INTEGER DEFAULT 1,
                last_used TIMESTAMP,
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pattern, tag)
            );
            
            -- Command execution history
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                tag TEXT,
                success BOOLEAN DEFAULT 1,
                response TEXT,
                execution_time_ms INTEGER,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- User preferences (key-value store)
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                value_type TEXT DEFAULT 'string',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Conversation memory (for context)
            CREATE TABLE IF NOT EXISTS conversation_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,  -- 'user' or 'assistant'
                content TEXT NOT NULL,
                context_tags TEXT,  -- JSON array of relevant tags
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Scheduled tasks
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,  -- 'alarm', 'reminder', 'timer', 'schedule'
                description TEXT,
                trigger_time TIMESTAMP,
                repeat_pattern TEXT,  -- cron-like pattern for recurring
                data TEXT,  -- JSON data for task
                status TEXT DEFAULT 'pending',  -- 'pending', 'triggered', 'cancelled'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_learned_intents_tag ON learned_intents(tag);
            CREATE INDEX IF NOT EXISTS idx_command_history_tag ON command_history(tag);
            CREATE INDEX IF NOT EXISTS idx_command_history_executed ON command_history(executed_at);
            CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_trigger ON scheduled_tasks(trigger_time);
        """)
        self.conn.commit()
    
    # --- Learned Intents ---
    
    def learn_pattern(self, pattern: str, tag: str, confidence: float = 1.0):
        """Store or update a learned pattern"""
        try:
            self.conn.execute("""
                INSERT INTO learned_intents (pattern, tag, confidence, last_used)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(pattern, tag) DO UPDATE SET
                    confidence = (confidence + excluded.confidence) / 2,
                    usage_count = usage_count + 1,
                    last_used = CURRENT_TIMESTAMP
            """, (pattern.lower(), tag, confidence))
            self.conn.commit()
        except Exception as e:
            print(f"[DB] Error learning pattern: {e}")
    
    def get_learned_patterns(self, tag: Optional[str] = None) -> List[Dict]:
        """Retrieve learned patterns, optionally filtered by tag"""
        if tag:
            rows = self.conn.execute(
                "SELECT * FROM learned_intents WHERE tag = ? ORDER BY usage_count DESC",
                (tag,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM learned_intents ORDER BY usage_count DESC"
            ).fetchall()
        return [dict(row) for row in rows]
    
    def get_patterns_for_matching(self) -> Dict[str, List[str]]:
        """Get all patterns grouped by tag for intent matching"""
        rows = self.conn.execute(
            "SELECT tag, pattern FROM learned_intents ORDER BY usage_count DESC"
        ).fetchall()
        
        result = {}
        for row in rows:
            if row['tag'] not in result:
                result[row['tag']] = []
            result[row['tag']].append(row['pattern'])
        return result
    
    # --- Command History ---
    
    def log_command(self, command: str, tag: str, success: bool, 
                    response: str = None, execution_time_ms: int = None):
        """Log a command execution"""
        self.conn.execute("""
            INSERT INTO command_history (command, tag, success, response, execution_time_ms)
            VALUES (?, ?, ?, ?, ?)
        """, (command, tag, success, response, execution_time_ms))
        self.conn.commit()
    
    def get_command_history(self, limit: int = 50) -> List[Dict]:
        """Get recent command history"""
        rows = self.conn.execute(
            "SELECT * FROM command_history ORDER BY executed_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    
    def get_most_used_commands(self, limit: int = 10) -> List[Dict]:
        """Get most frequently used commands"""
        rows = self.conn.execute("""
            SELECT tag, COUNT(*) as count, AVG(execution_time_ms) as avg_time
            FROM command_history
            WHERE success = 1
            GROUP BY tag
            ORDER BY count DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]
    
    # --- User Preferences ---
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference"""
        value_type = type(value).__name__
        value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        
        self.conn.execute("""
            INSERT INTO user_preferences (key, value, value_type, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                value_type = excluded.value_type,
                updated_at = CURRENT_TIMESTAMP
        """, (key, value_str, value_type))
        self.conn.commit()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference"""
        row = self.conn.execute(
            "SELECT value, value_type FROM user_preferences WHERE key = ?",
            (key,)
        ).fetchone()
        
        if row is None:
            return default
        
        value, value_type = row['value'], row['value_type']
        
        if value_type in ('dict', 'list'):
            return json.loads(value)
        elif value_type == 'int':
            return int(value)
        elif value_type == 'float':
            return float(value)
        elif value_type == 'bool':
            return value.lower() == 'true'
        return value
    
    # --- Scheduled Tasks ---
    
    def add_scheduled_task(self, task_type: str, trigger_time: datetime,
                           description: str = None, data: dict = None,
                           repeat_pattern: str = None) -> int:
        """Add a scheduled task"""
        cursor = self.conn.execute("""
            INSERT INTO scheduled_tasks (task_type, description, trigger_time, repeat_pattern, data)
            VALUES (?, ?, ?, ?, ?)
        """, (task_type, description, trigger_time.isoformat(), repeat_pattern, 
              json.dumps(data) if data else None))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_tasks(self, before: datetime = None) -> List[Dict]:
        """Get pending tasks, optionally before a certain time"""
        if before:
            rows = self.conn.execute("""
                SELECT * FROM scheduled_tasks 
                WHERE status = 'pending' AND trigger_time <= ?
                ORDER BY trigger_time
            """, (before.isoformat(),)).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT * FROM scheduled_tasks 
                WHERE status = 'pending'
                ORDER BY trigger_time
            """).fetchall()
        
        return [dict(row) for row in rows]
    
    def mark_task_triggered(self, task_id: int):
        """Mark a task as triggered"""
        self.conn.execute(
            "UPDATE scheduled_tasks SET status = 'triggered' WHERE id = ?",
            (task_id,)
        )
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# Example usage
if __name__ == "__main__":
    db = PhoenixDB("data/phoenix.db")
    
    # Learn some patterns
    db.learn_pattern("open the browser", "open", 0.95)
    db.learn_pattern("launch chrome", "open", 0.90)
    
    # Log a command
    db.log_command("open browser", "open", True, "Opening browser", 150)
    
    # Set preferences
    db.set_preference("voice_speed", 174)
    db.set_preference("wake_words", ["phoenix", "hey phoenix"])
    
    # Get patterns for matching
    patterns = db.get_patterns_for_matching()
    print("Learned patterns:", patterns)
    
    db.close()
```

---

### 6. MCP Server Integration (Future)

MCP (Model Context Protocol) allows external AI tools to call Phoenix functions:

```python
# plugins/mcp/server.py
"""
MCP Server for Phoenix - allows external AI tools (like VS Code Copilot)
to call Phoenix functions directly.

This enables:
- VS Code to control desktop apps via Phoenix
- Claude/GPT to execute system commands through Phoenix
- Third-party integrations with Phoenix capabilities
"""

from typing import Any
import asyncio

# MCP SDK (when ready)
# from mcp import Server, Tool, Resource

class PhoenixMCPServer:
    """
    MCP Server exposing Phoenix capabilities.
    
    Tools exposed:
    - open_app: Open applications
    - close_app: Close applications
    - play_music: Play music
    - system_control: Shutdown/restart/sleep
    - get_info: Time, weather, battery
    """
    
    def __init__(self, phoenix_engine):
        self.engine = phoenix_engine
        self.tools = self._define_tools()
    
    def _define_tools(self):
        """Define MCP tools"""
        return {
            "open_app": {
                "description": "Open an application on the desktop",
                "parameters": {
                    "app_name": {"type": "string", "description": "Name of app to open"}
                },
                "handler": self._open_app
            },
            "close_app": {
                "description": "Close an application",
                "parameters": {
                    "app_name": {"type": "string", "description": "Name of app to close"}
                },
                "handler": self._close_app
            },
            "play_music": {
                "description": "Play music or control playback",
                "parameters": {
                    "action": {"type": "string", "enum": ["play", "pause", "next", "previous"]},
                    "song": {"type": "string", "description": "Optional song name"}
                },
                "handler": self._play_music
            },
            "system_control": {
                "description": "Control system power state",
                "parameters": {
                    "action": {"type": "string", "enum": ["shutdown", "restart", "sleep", "hibernate"]}
                },
                "handler": self._system_control
            },
            "get_info": {
                "description": "Get system information",
                "parameters": {
                    "info_type": {"type": "string", "enum": ["time", "date", "battery", "weather"]}
                },
                "handler": self._get_info
            }
        }
    
    async def _open_app(self, app_name: str) -> str:
        result = self.engine.execute_plugin('apps', 'open', app_name)
        return f"Opened {app_name}" if result else f"Failed to open {app_name}"
    
    async def _close_app(self, app_name: str) -> str:
        result = self.engine.execute_plugin('apps', 'close', app_name)
        return f"Closed {app_name}" if result else f"Failed to close {app_name}"
    
    async def _play_music(self, action: str, song: str = None) -> str:
        result = self.engine.execute_plugin('media', action, song)
        return f"Music: {action}" if result else "Failed"
    
    async def _system_control(self, action: str) -> str:
        result = self.engine.execute_plugin('system', action, None)
        return f"System: {action} initiated"
    
    async def _get_info(self, info_type: str) -> str:
        return self.engine.execute_plugin('information', info_type, None)
    
    def run(self, host: str = "localhost", port: int = 8765):
        """Start MCP server"""
        print(f"[MCP] Phoenix MCP Server starting on {host}:{port}")
        # When MCP SDK is available:
        # asyncio.run(self.server.run(host, port))


# VS Code configuration for MCP
MCP_CONFIG = """
# .vscode/mcp.json
{
  "servers": {
    "phoenix": {
      "command": "python",
      "args": ["-m", "plugins.mcp.server"],
      "cwd": "W:/workplace-1/Phoenix",
      "env": {
        "PHOENIX_MCP_PORT": "8765"
      }
    }
  }
}
"""
```

---

## 📊 Comparison Table

| Aspect | Guide's Approach | Recommended Approach |
|--------|-----------------|----------------------|
| **Speed Fix** | Whisper tiny/base ✅ | Keep tiny, add GPU check |
| **Architecture** | Basic plugin | Manager.py + plugin hybrid |
| **Config** | Not mentioned | JSON + core.md + SQLite |
| **Self-Evolution** | Not mentioned | core.md with auto-write |
| **Database** | Not mentioned | SQLite for patterns |
| **TTS** | Edge TTS (online) | Piper (offline, faster) |
| **MCP** | Not mentioned | Add as future layer |
| **Process Management** | Not mentioned | Unified manager.py |

---

## 🎯 Your Ideas Rating

| Idea | Rating | Notes |
|------|--------|-------|
| Manager.py concept | **9/10** | Implement this - excellent orchestration |
| Plugin breakdown (normal/mcp) | **8/10** | Good separation of concerns |
| Core.md self-evolving | **10/10** | Unique and powerful concept |
| Thread-based background | **8/10** | Works well, consider asyncio later |
| Breaking HelperPHNX.py | **9/10** | Much needed refactoring |

---

## 🚀 Implementation Priority

### Phase 1: Quick Wins (This Week)
1. Fix merge conflict in `time_monitor.pyw`
2. Switch Whisper to "tiny" model
3. Fix pyttsx3 reinitialization (create once, reuse)
4. Reduce silence threshold to 0.4s

### Phase 2: Architecture (This Month)
1. Implement `manager.py` skeleton
2. Create `core.md` soul file
3. Set up SQLite database
4. Break `HelperPHNX.py` into plugins/normal/ modules

### Phase 3: Advanced (Over Time)
1. Implement semantic intent matching
2. Add MCP server integration
3. Build self-evolution logic for core.md
4. Add GPU support for Whisper

---

## 📝 Files to Create

| File | Purpose | Priority |
|------|---------|----------|
| `bgprogs/manager.py` | Process orchestration | High |
| `data/core.md` | AI soul/persona | High |
| `data/database.py` | SQLite wrapper | High |
| `core/soul.py` | Core.md interface | High |
| `plugins/base.py` | Plugin base class | Medium |
| `plugins/normal/apps.py` | App control | Medium |
| `plugins/normal/system.py` | System control | Medium |
| `plugins/normal/media.py` | Media control | Medium |
| `plugins/mcp/server.py` | MCP integration | Low |

---

## ⚠️ Current Issues to Fix

1. **Merge Conflict in time_monitor.pyw**
   - Lines 72-151 have `<<<<<<<` and `>>>>>>>` markers
   - Need to resolve before any changes

2. **Duplicate Code**
   - `continuous_listener.py` exists in both root and `/core`
   - Need to consolidate

3. **Large Files**
   - `UtilitiesPHNX.py` is 3300+ lines
   - `main_assistant.py` is 700+ lines
   - Need to break into smaller modules

---

*Document generated for Phoenix architecture planning and implementation guidance.*
