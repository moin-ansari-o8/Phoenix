"""
Base Plugin System for Phoenix
==============================

Provides the foundation for all plugins:
- BasePlugin: Abstract base class all plugins inherit from
- PluginRegistry: Central registry for loading and executing plugins
- Common utilities shared across plugins
"""

import os
import time
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Callable, Any, Optional, List


class BasePlugin(ABC):
    """
    Abstract base class for all Phoenix plugins.

    Every plugin must:
    1. Inherit from BasePlugin
    2. Define PLUGIN_NAME and PLUGIN_DESCRIPTION
    3. Register actions in _register_actions()
    4. Implement _register_actions() method

    Example:
        class SystemPlugin(BasePlugin):
            PLUGIN_NAME = "system"
            PLUGIN_DESCRIPTION = "System control operations"

            def _register_actions(self):
                self.register("shutdown", self.shutdown)
                self.register("restart", self.restart)
    """

    PLUGIN_NAME: str = "base"
    PLUGIN_DESCRIPTION: str = "Base plugin"

    def __init__(self, speech_engine=None, voice_recognition=None, config: dict = None):
        """
        Initialize the plugin.

        Args:
            speech_engine: SpeechEngine instance for TTS
            voice_recognition: VoiceRecognition instance for STT
            config: Optional configuration dictionary
        """
        self.speech = speech_engine
        self.recognition = voice_recognition
        self.config = config or {}
        self._actions: Dict[str, Callable] = {}
        self._action_descriptions: Dict[str, str] = {}

        # Call plugin's action registration
        self._register_actions()

    @abstractmethod
    def _register_actions(self) -> None:
        """
        Register all actions this plugin provides.
        Must be implemented by subclasses.

        Use self.register(name, callable, description) to register actions.
        """
        pass

    def register(self, name: str, action: Callable, description: str = "") -> None:
        """
        Register an action with this plugin.

        Args:
            name: Action name (e.g., "shutdown", "open_brave")
            action: Callable that performs the action
            description: Human-readable description of the action
        """
        self._actions[name] = action
        self._action_descriptions[name] = description

    def execute(self, action_name: str, *args, **kwargs) -> Any:
        """
        Execute a registered action.

        Args:
            action_name: Name of the action to execute
            *args, **kwargs: Arguments to pass to the action

        Returns:
            Result of the action

        Raises:
            KeyError: If action not found
        """
        if action_name not in self._actions:
            raise KeyError(f"Action '{action_name}' not found in {self.PLUGIN_NAME}")

        return self._actions[action_name](*args, **kwargs)

    def has_action(self, action_name: str) -> bool:
        """Check if plugin has a specific action."""
        return action_name in self._actions

    def list_actions(self) -> List[str]:
        """Get list of all registered action names."""
        return list(self._actions.keys())

    def get_action_info(self) -> Dict[str, str]:
        """Get dictionary of action names to descriptions."""
        return self._action_descriptions.copy()

    # ==================== Common Utilities ====================

    def speak(self, text: str, speed: int = 174) -> None:
        """
        Speak text using the speech engine.

        Args:
            text: Text to speak
            speed: Speech rate (default 174 WPM)
        """
        if self.speech:
            self.speech.speak(text, speed)
        else:
            print(f"[TTS] {text}")

    def run_command(
        self, command: str, shell: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command.

        Args:
            command: Command to run
            shell: Whether to use shell (default True)

        Returns:
            CompletedProcess result
        """
        try:
            result = subprocess.run(
                command, shell=shell, capture_output=True, text=True, timeout=30
            )
            return result
        except subprocess.TimeoutExpired:
            print(f"[WARN] Command timed out: {command}")
            return None
        except Exception as e:
            print(f"[ERROR] Command failed: {e}")
            return None

    def run_async(self, command: str) -> subprocess.Popen:
        """
        Run a command asynchronously (non-blocking).

        Args:
            command: Command to run

        Returns:
            Popen process object
        """
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return process
        except Exception as e:
            print(f"[ERROR] Async command failed: {e}")
            return None

    def delay(self, seconds: float) -> None:
        """Sleep for specified seconds."""
        time.sleep(seconds)


class PluginRegistry:
    """
    Central registry for loading and managing plugins.

    Handles:
    - Plugin discovery and loading
    - Action routing to correct plugin
    - Plugin lifecycle management

    Example:
        registry = PluginRegistry(speech_engine, voice_recognition)
        registry.load_plugin(SystemPlugin)
        registry.load_plugin(AppsPlugin)

        # Execute action
        registry.execute("system", "shutdown")
        registry.execute("apps", "open_brave")

        # Or use unified execute with auto-discovery
        registry.auto_execute("shutdown")  # Finds correct plugin
    """

    def __init__(self, speech_engine=None, voice_recognition=None, config: dict = None):
        """
        Initialize the plugin registry.

        Args:
            speech_engine: SpeechEngine instance to pass to plugins
            voice_recognition: VoiceRecognition instance to pass to plugins
            config: Global configuration dictionary
        """
        self.speech = speech_engine
        self.recognition = voice_recognition
        self.config = config or {}
        self._plugins: Dict[str, BasePlugin] = {}
        self._action_to_plugin: Dict[str, str] = {}  # Action name -> plugin name

    def load_plugin(self, plugin_class: type, plugin_config: dict = None) -> None:
        """
        Load and register a plugin.

        Args:
            plugin_class: Plugin class (must inherit from BasePlugin)
            plugin_config: Optional plugin-specific config
        """
        if not issubclass(plugin_class, BasePlugin):
            raise TypeError(f"{plugin_class} must inherit from BasePlugin")

        # Merge configs
        config = {**self.config, **(plugin_config or {})}

        # Instantiate plugin
        plugin = plugin_class(self.speech, self.recognition, config)
        plugin_name = plugin.PLUGIN_NAME

        # Register plugin
        self._plugins[plugin_name] = plugin

        # Map actions to plugin
        for action_name in plugin.list_actions():
            full_action = f"{plugin_name}.{action_name}"
            self._action_to_plugin[action_name] = plugin_name
            self._action_to_plugin[full_action] = plugin_name

        print(
            f"[INFO] Loaded plugin: {plugin_name} ({len(plugin.list_actions())} actions)"
        )

    def load_all_plugins(self) -> None:
        """
        Load all standard plugins from the normal/ directory.
        This method imports and loads all plugin classes.
        """
        from .normal import (
            AppsPlugin,
            SystemPlugin,
            MediaPlugin,
            InformationPlugin,
            WindowsPlugin,
            BrowserPlugin,
            InputPlugin,
            DesktopPlugin,
            PersonalPlugin,
        )

        plugins = [
            AppsPlugin,
            SystemPlugin,
            MediaPlugin,
            InformationPlugin,
            WindowsPlugin,
            BrowserPlugin,
            InputPlugin,
            DesktopPlugin,
            PersonalPlugin,
        ]

        for plugin_class in plugins:
            try:
                self.load_plugin(plugin_class)
            except Exception as e:
                print(f"[ERROR] Failed to load {plugin_class}: {e}")

    def execute(self, plugin_name: str, action_name: str, *args, **kwargs) -> Any:
        """
        Execute an action from a specific plugin.

        Args:
            plugin_name: Name of the plugin
            action_name: Name of the action
            *args, **kwargs: Arguments for the action

        Returns:
            Result of the action
        """
        if plugin_name not in self._plugins:
            raise KeyError(f"Plugin '{plugin_name}' not found")

        return self._plugins[plugin_name].execute(action_name, *args, **kwargs)

    def auto_execute(self, action_name: str, *args, **kwargs) -> Any:
        """
        Execute an action, automatically finding the correct plugin.

        Args:
            action_name: Name of the action (can be "plugin.action" or just "action")
            *args, **kwargs: Arguments for the action

        Returns:
            Result of the action
        """
        # Check if action includes plugin prefix
        if "." in action_name:
            plugin_name, action = action_name.split(".", 1)
            return self.execute(plugin_name, action, *args, **kwargs)

        # Find plugin that has this action
        if action_name not in self._action_to_plugin:
            raise KeyError(f"Action '{action_name}' not found in any plugin")

        plugin_name = self._action_to_plugin[action_name]
        return self._plugins[plugin_name].execute(action_name, *args, **kwargs)

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get a plugin by name."""
        return self._plugins.get(plugin_name)

    def list_plugins(self) -> List[str]:
        """Get list of loaded plugin names."""
        return list(self._plugins.keys())

    def list_all_actions(self) -> Dict[str, List[str]]:
        """Get dictionary of plugin names to their action lists."""
        return {name: plugin.list_actions() for name, plugin in self._plugins.items()}

    def find_action(self, keyword: str) -> List[str]:
        """
        Find actions matching a keyword.

        Args:
            keyword: Keyword to search for

        Returns:
            List of matching "plugin.action" strings
        """
        matches = []
        keyword_lower = keyword.lower()

        for plugin_name, plugin in self._plugins.items():
            for action in plugin.list_actions():
                if keyword_lower in action.lower():
                    matches.append(f"{plugin_name}.{action}")

        return matches
