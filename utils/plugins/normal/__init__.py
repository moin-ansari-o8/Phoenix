"""
Normal Plugins Package
======================

Standard (non-MCP) plugins for Phoenix voice assistant.
Each plugin handles a specific category of functionality.

Plugins:
    - apps: Application open/close operations
    - system: System power controls (shutdown, restart, hibernate, sleep)
    - media: Music playback, volume control, audio management
    - information: Time, date, battery, weather queries
    - windows: Window management (minimize, maximize, move, resize)
    - browser: Web browser and search operations
    - input: Keyboard/mouse input simulation
    - desktop: Virtual desktop management and workspace setups
    - personal: Personal task management (todos, goals, projects)
"""

from .apps import AppsPlugin
from .system import SystemPlugin
from .media import MediaPlugin
from .information import InformationPlugin
from .windows import WindowsPlugin
from .browser import BrowserPlugin
from .input import InputPlugin
from .desktop import DesktopPlugin
from .personal import PersonalPlugin

__all__ = [
    "AppsPlugin",
    "SystemPlugin",
    "MediaPlugin",
    "InformationPlugin",
    "WindowsPlugin",
    "BrowserPlugin",
    "InputPlugin",
    "DesktopPlugin",
    "PersonalPlugin",
]
