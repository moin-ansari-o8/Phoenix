# Phoenix Plugin Architecture

## Overview

This is the modular plugin architecture for Phoenix voice assistant. The helpers folder has been broken down into focused, single-responsibility plugins for better maintainability and extensibility.

## Structure

```
plugin-temp/
├── __init__.py         # Package init, exports BasePlugin & PluginRegistry
├── base.py             # Core plugin system (BasePlugin, PluginRegistry)
├── README.md           # This file
└── normal/             # Standard plugins (non-MCP)
    ├── __init__.py     # Exports all plugin classes
    ├── apps.py         # Application open/close (13 KB, ~30 actions)
    ├── system.py       # System power controls (10 KB, ~15 actions)
    ├── media.py        # Music/audio/volume (17 KB, ~25 actions)
    ├── information.py  # Time, date, battery, weather (11 KB, ~15 actions)
    ├── windows.py      # Window management (18 KB, ~20 actions)
    ├── browser.py      # Web browser & search (13 KB, ~25 actions)
    ├── input.py        # Keyboard/mouse input (14 KB, ~20 actions)
    ├── desktop.py      # Virtual desktops & setups (12 KB, ~15 actions)
    └── personal.py     # Projects, goals, todos (16 KB, ~20 actions)
```

## Quick Start

### Basic Usage

```python
from plugin_temp import PluginRegistry

# Initialize registry with speech engine
registry = PluginRegistry(speech_engine=my_speech_engine)

# Load all plugins
registry.load_all_plugins()

# Execute actions
registry.execute("apps", "open_brave")
registry.execute("system", "shutdown")
registry.execute("media", "play_pause")

# Or auto-find plugin
registry.auto_execute("open_brave")  # Finds apps plugin automatically
```

### Individual Plugin Usage

```python
from plugin_temp.normal import AppsPlugin, SystemPlugin

# Create plugin instance
apps = AppsPlugin(speech_engine=my_speech_engine)

# List available actions
print(apps.list_actions())
# ['open_app', 'close_app', 'open_brave', 'open_code', ...]

# Execute action
apps.execute("open_brave")
```

## Plugin Categories

### 1. Apps Plugin (`apps.py`)
Handles application launching and closing.

| Action | Description |
|--------|-------------|
| `open_app` | Open any application by name |
| `close_app` | Close application by name |
| `focus_app` | Bring app to foreground |
| `open_brave` | Open Brave browser |
| `open_code` | Open VS Code |
| `open_spotify` | Open Spotify |
| `open_youtube` | Open YouTube |
| ... | (30+ more) |

### 2. System Plugin (`system.py`)
System power and control operations.

| Action | Description |
|--------|-------------|
| `shutdown` | Shut down computer |
| `restart` | Restart computer |
| `hibernate` | Hibernate |
| `sleep` | Sleep mode |
| `lock` | Lock workstation |
| `restart_phoenix` | Restart Phoenix |
| `bluetooth_toggle` | Toggle Bluetooth |
| ... | |

### 3. Media Plugin (`media.py`)
Music playback and audio controls.

| Action | Description |
|--------|-------------|
| `play_song` | Play specific song |
| `play_random` | Play random song |
| `play_pause` | Toggle play/pause |
| `next_track` | Next track |
| `adjust_volume` | Set/adjust volume |
| `mute` / `unmute` | Mute controls |
| `suggest_song` | Song suggestion |
| ... | |

### 4. Information Plugin (`information.py`)
Time, date, battery, weather queries.

| Action | Description |
|--------|-------------|
| `time` | Get current time |
| `date` | Get current date |
| `battery` | Battery status |
| `weather` | Weather info |
| `greeting` | Time-based greeting |
| `water_reminder` | Hydration reminder |
| ... | |

### 5. Windows Plugin (`windows.py`)
Window management and positioning.

| Action | Description |
|--------|-------------|
| `minimize` | Minimize window |
| `maximize` | Maximize window |
| `fullscreen` | Toggle fullscreen |
| `move` | Move window |
| `snap` | Snap to edge |
| `pin` | Always on top |
| `list_windows` | List open windows |
| ... | |

### 6. Browser Plugin (`browser.py`)
Web browser control and searches.

| Action | Description |
|--------|-------------|
| `search_google` | Google search |
| `search_youtube` | YouTube search |
| `search_github` | GitHub search |
| `amazon` | Amazon search |
| `flipkart` | Flipkart search |
| `new_tab` | Open new tab |
| `close_tab` | Close tab |
| ... | |

### 7. Input Plugin (`input.py`)
Keyboard and mouse input simulation.

| Action | Description |
|--------|-------------|
| `type_text` | Type text |
| `press_key` | Press a key |
| `hotkey` | Key combination |
| `click` | Mouse click |
| `screenshot` | Take screenshot |
| `scroll` | Scroll up/down |
| ... | |

### 8. Desktop Plugin (`desktop.py`)
Virtual desktop and workspace management.

| Action | Description |
|--------|-------------|
| `switch_desktop` | Switch virtual desktop |
| `move_to_desktop` | Move window to desktop |
| `setup_study` | Study workspace |
| `setup_trash` | Leisure workspace |
| `task_view` | Open Task View |
| ... | |

### 9. Personal Plugin (`personal.py`)
Personal task management.

| Action | Description |
|--------|-------------|
| `add_project` | Create project |
| `update_project` | Update project |
| `add_todo` | Add todo |
| `complete_todo` | Complete todo |
| `add_goal` | Create goal |
| `morning_briefing` | Get summary |
| ... | |

## Creating Custom Plugins

### Step 1: Inherit from BasePlugin

```python
from plugin_temp.base import BasePlugin

class MyCustomPlugin(BasePlugin):
    PLUGIN_NAME = "custom"
    PLUGIN_DESCRIPTION = "My custom plugin"
    
    def _register_actions(self):
        self.register("my_action", self.my_action, "Does something")
        self.register("another_action", self.another_action, "Does something else")
    
    def my_action(self, param: str) -> bool:
        self.speak(f"Doing something with {param}")
        return True
    
    def another_action(self):
        self.speak("Doing something else")
        return True
```

### Step 2: Register with PluginRegistry

```python
registry = PluginRegistry()
registry.load_plugin(MyCustomPlugin)
registry.execute("custom", "my_action", "test")
```

## Migration from Old Helpers

| Old Method (UtilitiesPHNX) | New Plugin.Action |
|---------------------------|-------------------|
| `open_brave()` | `apps.open_brave` |
| `shutD()` | `system.shutdown` |
| `play_random_song()` | `media.play_random` |
| `tim()` | `information.time` |
| `minimize_window()` | `windows.minimize` |
| `search_browser()` | `browser.search_browser` |
| `type_text()` | `input.type_text` |
| `desKtoP()` | `desktop.switch_desktop` |
| `setup_study()` | `desktop.setup_study` |

## Benefits

1. **Modularity**: Each plugin is self-contained
2. **Testability**: Plugins can be tested in isolation
3. **Discoverability**: `list_actions()` shows available commands
4. **Extensibility**: Easy to add new plugins
5. **Type Safety**: Clear interfaces and return types
6. **Error Handling**: Centralized error handling in base class
7. **Logging**: Built-in logging support
8. **Configuration**: Plugin-specific config support

## Future: MCP Plugins

The `normal/` folder is for standard plugins. Future MCP (Model Context Protocol) plugins will go in a separate `mcp/` folder:

```
plugin-temp/
├── normal/    # Standard plugins
└── mcp/       # MCP server plugins (future)
    ├── __init__.py
    └── ...
```

## Dependencies

Plugins have optional dependencies. They gracefully degrade if dependencies are missing:

- `pyautogui`: Keyboard/mouse automation
- `pygetwindow`: Window management
- `win32gui/win32con`: Windows-specific operations
- `pycaw`: Audio volume control
- `pyvda`: Virtual desktop management
- `psutil`: System information
- `requests`: Weather API

Install all:
```bash
pip install pyautogui pygetwindow pywin32 pycaw pyvda psutil requests
```
