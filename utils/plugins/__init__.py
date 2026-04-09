"""
Phoenix Plugin Architecture
===========================

This package contains the modular plugin system for Phoenix voice assistant.
Plugins are organized by category for maintainability and extensibility.

Structure:
    plugin-temp/
    ├── __init__.py         # This file - package initialization
    ├── base.py             # BasePlugin class and plugin registry
    └── normal/             # Standard plugins (non-MCP)
        ├── __init__.py     # Normal plugins package
        ├── apps.py         # App open/close operations
        ├── system.py       # System controls (shutdown, restart, etc.)
        ├── media.py        # Music/audio/volume controls
        ├── information.py  # Time, date, battery, weather
        ├── windows.py      # Window management
        ├── browser.py      # Browser and search operations
        ├── input.py        # Keyboard/mouse input
        ├── desktop.py      # Virtual desktop & setup operations
        └── personal.py     # Personal manager (todos, goals, projects)

Usage:
    from plugin_temp import PluginRegistry

    registry = PluginRegistry(speech_engine, voice_recognition)
    registry.load_all_plugins()

    # Execute a plugin action
    registry.execute("apps", "open_brave")
    registry.execute("system", "shutdown")
"""

from .base import BasePlugin, PluginRegistry

__version__ = "1.0.0"
__all__ = ["BasePlugin", "PluginRegistry"]
