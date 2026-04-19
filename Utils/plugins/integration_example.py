"""
Phoenix Plugin Integration Example

This file demonstrates how to integrate the new plugin architecture
with the existing Phoenix codebase.
"""

import sys
import logging
from pathlib import Path

# Add Phoenix root to path
PHOENIX_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PHOENIX_ROOT))

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("phoenix.integration")


class PhoenixPluginIntegration:
    """
    Integration layer between old ProcessorPHNX and new Plugin system.

    This class maps old tags/intents to new plugin actions, making
    migration gradual and non-breaking.
    """

    # Maps old tags (from ProcessorPHNX) to (plugin_name, action_name)
    TAG_TO_ACTION = {
        # Apps
        "open-brave": ("apps", "open_brave"),
        "open-arc": ("apps", "open_arc"),
        "open-vscode": ("apps", "open_code"),
        "open-code": ("apps", "open_code"),
        "open-spotify": ("apps", "open_spotify"),
        "open-youtube": ("apps", "open_youtube"),
        "open-app": ("apps", "open_app"),
        "close-app": ("apps", "close_app"),
        "close-brave": ("apps", "close_brave"),
        "close-arc": ("apps", "close_arc"),
        "close-spotify": ("apps", "close_spotify"),
        "close-vscode": ("apps", "close_code"),
        # System
        "shutdown": ("system", "shutdown"),
        "restart": ("system", "restart"),
        "hibernate": ("system", "hibernate"),
        "sleep": ("system", "sleep"),
        "lock": ("system", "lock"),
        "restart-phoenix": ("system", "restart_phoenix"),
        # Media
        "play-song": ("media", "play_song"),
        "play-random-song": ("media", "play_random"),
        "pause-music": ("media", "pause"),
        "play-music": ("media", "play"),
        "play-pause": ("media", "play_pause"),
        "next-track": ("media", "next_track"),
        "prev-track": ("media", "prev_track"),
        "volume-up": ("media", "volume_up"),
        "volume-down": ("media", "volume_down"),
        "mute": ("media", "mute"),
        "unmute": ("media", "unmute"),
        "suggest-song": ("media", "suggest_song"),
        # Information
        "time": ("information", "time"),
        "date": ("information", "date"),
        "day": ("information", "day"),
        "battery": ("information", "battery"),
        "weather": ("information", "weather"),
        "greeting": ("information", "greeting"),
        "water-reminder": ("information", "water_reminder"),
        # Windows
        "minimize-window": ("windows", "minimize"),
        "maximize-window": ("windows", "maximize"),
        "fullscreen": ("windows", "fullscreen"),
        "hide-window": ("windows", "hide"),
        "show-window": ("windows", "show"),
        "close-window": ("windows", "close"),
        "move-window": ("windows", "move"),
        "snap-left": ("windows", "snap_left"),
        "snap-right": ("windows", "snap_right"),
        "pin-window": ("windows", "pin"),
        "unpin-window": ("windows", "unpin"),
        # Browser
        "search-google": ("browser", "search_google"),
        "search-youtube": ("browser", "search_youtube"),
        "search-github": ("browser", "search_github"),
        "search-amazon": ("browser", "amazon"),
        "search-flipkart": ("browser", "flipkart"),
        "search-myntra": ("browser", "myntra"),
        "new-tab": ("browser", "new_tab"),
        "close-tab": ("browser", "close_tab"),
        # Input
        "type-text": ("input", "type_text"),
        "press-key": ("input", "press_key"),
        "screenshot": ("input", "screenshot"),
        "scroll-up": ("input", "scroll_up"),
        "scroll-down": ("input", "scroll_down"),
        # Desktop
        "switch-desktop": ("desktop", "switch_desktop"),
        "task-view": ("desktop", "task_view"),
        "setup-study": ("desktop", "setup_study"),
        "setup-trash": ("desktop", "setup_trash"),
        "setup-alpha": ("desktop", "setup_alpha"),
        # Personal
        "add-project": ("personal", "add_project"),
        "add-todo": ("personal", "add_todo"),
        "add-goal": ("personal", "add_goal"),
        "morning-briefing": ("personal", "morning_briefing"),
    }

    def __init__(self, speech_engine=None, voice_recognition=None):
        """
        Initialize integration layer.

        Args:
            speech_engine: Text-to-speech engine instance
            voice_recognition: Voice recognition instance
        """
        self.speech_engine = speech_engine
        self.voice_recognition = voice_recognition
        self.registry = None
        self._initialized = False

    def initialize(self):
        """Load plugin registry and all plugins."""
        if self._initialized:
            return

        try:
            # Import here to avoid circular imports
            from Utils.plugins import PluginRegistry

            self.registry = PluginRegistry(
                speech_engine=self.speech_engine,
                voice_recognition=self.voice_recognition,
            )
            self.registry.load_all_plugins()
            self._initialized = True
            logger.info(
                f"Plugin integration initialized with {len(self.registry.list_plugins())} plugins"
            )

        except Exception as e:
            logger.error(f"Failed to initialize plugin integration: {e}")
            raise

    def execute_tag(self, tag: str, *args, **kwargs) -> bool:
        """
        Execute action by old tag name.

        This allows ProcessorPHNX to use new plugins without rewriting
        the entire intent matching system.

        Args:
            tag: Old tag name (e.g., "open-brave", "play-random-song")
            *args, **kwargs: Additional arguments for the action

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            self.initialize()

        # Check if tag is mapped
        if tag not in self.TAG_TO_ACTION:
            logger.warning(f"Unknown tag: {tag}")
            return False

        plugin_name, action_name = self.TAG_TO_ACTION[tag]

        try:
            result = self.registry.execute(plugin_name, action_name, *args, **kwargs)
            logger.info(f"Executed {plugin_name}.{action_name} -> {result}")
            return result

        except Exception as e:
            logger.error(f"Error executing {tag}: {e}")
            return False

    def execute_direct(self, plugin: str, action: str, *args, **kwargs) -> bool:
        """
        Execute action directly by plugin and action name.

        Args:
            plugin: Plugin name (e.g., "apps", "media")
            action: Action name (e.g., "open_brave", "play_random")
            *args, **kwargs: Additional arguments

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            self.initialize()

        try:
            return self.registry.execute(plugin, action, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing {plugin}.{action}: {e}")
            return False

    def list_all_actions(self) -> dict:
        """Get all available actions from all plugins."""
        if not self._initialized:
            self.initialize()

        return self.registry.list_all_actions()


# Example usage showing integration with existing code
def example_integration():
    """
    Example showing how to update ProcessorPHNX to use plugins.

    In ProcessorPHNX._execute_action(), replace direct method calls
    with plugin integration calls.
    """

    # OLD CODE in ProcessorPHNX._execute_action():
    # ============================================
    # if tag == "open-brave":
    #     self.utility.open_brave()
    # elif tag == "play-random-song":
    #     self.utility.play_random_song()
    # elif tag == "shutdown":
    #     self.utility.shutD()

    # NEW CODE using integration:
    # ============================================
    # integration = PhoenixPluginIntegration(
    #     speech_engine=self.speech_engine,
    #     voice_recognition=self.recognizer
    # )
    # integration.execute_tag(tag)

    # Or for new code, use direct plugin calls:
    # integration.execute_direct("apps", "open_brave")

    print("Example: Integration pattern for ProcessorPHNX")
    print("=" * 50)
    print(
        """
    class PhoenixAssistant:
        def __init__(self):
            self.plugin_integration = PhoenixPluginIntegration(
                speech_engine=self.speech_engine,
                voice_recognition=self.recognizer
            )
            self.plugin_integration.initialize()
        
        def _execute_action(self, tag, entities):
            # Try new plugin system first
            if self.plugin_integration.execute_tag(tag, **entities):
                return True
            
            # Fall back to old utility methods for unmapped tags
            return self._old_execute_action(tag, entities)
    """
    )


def demo_plugins():
    """
    Demo showing plugins in action.
    """
    print("\n" + "=" * 60)
    print("PHOENIX PLUGIN DEMO")
    print("=" * 60 + "\n")

    # Mock speech engine for demo
    class MockSpeech:
        def speak(self, text):
            print(f"[SPEECH]: {text}")

    try:
        from Utils.plugins import PluginRegistry

        # Create registry with mock speech
        registry = PluginRegistry(speech_engine=MockSpeech())

        # Load all plugins
        registry.load_all_plugins()

        print("Loaded plugins:")
        for name in registry.list_plugins():
            plugin = registry.get_plugin(name)
            print(f"  - {name}: {plugin.PLUGIN_DESCRIPTION}")

        print("\n" + "-" * 40)
        print("Available actions by plugin:\n")

        all_actions = registry.list_all_actions()
        for plugin_name, actions in all_actions.items():
            print(f"{plugin_name}:")
            for action in actions[:5]:  # First 5
                print(f"    {action}")
            if len(actions) > 5:
                print(f"    ... and {len(actions) - 5} more")
            print()

        print("-" * 40)
        print("Demo: Getting time...\n")
        registry.execute("information", "time")

    except ImportError as e:
        print(f"Could not import plugins: {e}")
        print("Make sure Utils.plugins package is in PYTHONPATH")


if __name__ == "__main__":
    example_integration()
    demo_plugins()
