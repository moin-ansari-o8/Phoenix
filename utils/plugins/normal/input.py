"""
Input Plugin - Keyboard and Mouse Input
========================================

Handles keyboard typing, key presses, and mouse operations.
Extracted from UtilitiesPHNX.py input-related methods.

Actions:
    - type_text: Type text
    - press_key: Press a specific key
    - hotkey: Press key combination
    - screenshot: Take a screenshot
    - move_cursor: Move mouse cursor
"""

import os
import time
import re
from datetime import datetime
from typing import Tuple, Optional

try:
    import pyautogui as pg
    import keyboard
except ImportError:
    pg = None
    keyboard = None

from ..base import BasePlugin


class InputPlugin(BasePlugin):
    """Plugin for keyboard and mouse input operations."""

    PLUGIN_NAME = "input"
    PLUGIN_DESCRIPTION = "Keyboard and mouse input simulation"

    # Screenshots directory
    SCREENSHOTS_DIR = r"C:\Users\{user}\Pictures\Screenshots"

    # Key name mappings
    KEY_ALIASES = {
        "enter": "enter",
        "return": "enter",
        "escape": "escape",
        "esc": "escape",
        "space": "space",
        "tab": "tab",
        "backspace": "backspace",
        "delete": "delete",
        "del": "delete",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "home": "home",
        "end": "end",
        "pageup": "pageup",
        "pagedown": "pagedown",
        "capslock": "capslock",
        "caps": "capslock",
        "numlock": "numlock",
        "scrolllock": "scrolllock",
        "printscreen": "printscreen",
        "prtsc": "printscreen",
        "pause": "pause",
        "insert": "insert",
        "win": "win",
        "windows": "win",
        "alt": "alt",
        "ctrl": "ctrl",
        "control": "ctrl",
        "shift": "shift",
    }

    def __init__(self, speech_engine=None, voice_recognition=None, config: dict = None):
        self.user = os.getenv("USERNAME", "")
        self.screenshots_dir = self.SCREENSHOTS_DIR.format(user=self.user)
        super().__init__(speech_engine, voice_recognition, config)

    def _register_actions(self) -> None:
        """Register all input-related actions."""
        # Keyboard
        self.register("type_text", self.type_text, "Type text")
        self.register("press_key", self.press_key, "Press a key")
        self.register("hotkey", self.hotkey, "Press key combination")
        self.register("hold_key", self.hold_key, "Hold down a key")
        self.register("release_key", self.release_key, "Release a held key")

        # Special typing
        self.register("type_slow", self.type_slow, "Type text slowly")
        self.register("type_fast", self.type_fast, "Type text fast")

        # Mouse
        self.register("click", self.click, "Click at position")
        self.register("double_click", self.double_click, "Double click")
        self.register("right_click", self.right_click, "Right click")
        self.register("move_cursor", self.move_cursor, "Move cursor to position")
        self.register("scroll", self.scroll, "Scroll up or down")

        # Screen capture
        self.register("screenshot", self.screenshot, "Take a screenshot")
        self.register(
            "screenshot_region", self.screenshot_region, "Screenshot a region"
        )

        # Directional navigation
        self.register("move_direction", self.move_direction, "Move in a direction")

    def _normalize_key(self, key: str) -> str:
        """Normalize key name to pyautogui format."""
        key_lower = key.lower().strip()
        return self.KEY_ALIASES.get(key_lower, key_lower)

    def _extract_text(self, query: str) -> str:
        """Extract text to type from query."""
        # Remove command words
        keywords = ["type", "write", "enter", "input", "text"]
        text = query
        for kw in keywords:
            text = re.sub(rf"\b{kw}\b", "", text, flags=re.IGNORECASE)
        return text.strip()

    # ==================== Keyboard ====================

    def type_text(self, query: str) -> bool:
        """
        Type text.

        Args:
            query: Text to type (or query containing text)

        Returns:
            True if typed
        """
        text = self._extract_text(query)

        if not text:
            self.speak("What should I type?")
            return False

        if pg:
            try:
                pg.typewrite(text, interval=0.02)
                return True
            except Exception:
                pass

        if keyboard:
            try:
                keyboard.write(text)
                return True
            except Exception:
                pass

        return False

    def type_slow(self, text: str, interval: float = 0.1) -> bool:
        """
        Type text slowly.

        Args:
            text: Text to type
            interval: Delay between characters

        Returns:
            True if typed
        """
        if pg:
            try:
                pg.typewrite(text, interval=interval)
                return True
            except Exception:
                pass
        return False

    def type_fast(self, text: str) -> bool:
        """
        Type text as fast as possible.

        Args:
            text: Text to type

        Returns:
            True if typed
        """
        if keyboard:
            try:
                keyboard.write(text)
                return True
            except Exception:
                pass

        if pg:
            try:
                pg.typewrite(text, interval=0.01)
                return True
            except Exception:
                pass

        return False

    def press_key(self, key: str) -> bool:
        """
        Press a single key.

        Args:
            key: Key to press (e.g., "enter", "escape", "f5")

        Returns:
            True if key pressed
        """
        key_normalized = self._normalize_key(key)

        if pg:
            try:
                pg.press(key_normalized)
                return True
            except Exception:
                pass

        if keyboard:
            try:
                keyboard.send(key_normalized)
                return True
            except Exception:
                pass

        return False

    def hotkey(self, *keys) -> bool:
        """
        Press a key combination.

        Args:
            *keys: Keys to press together (e.g., "ctrl", "c")

        Returns:
            True if hotkey pressed
        """
        normalized_keys = [self._normalize_key(k) for k in keys]

        if pg:
            try:
                pg.hotkey(*normalized_keys)
                return True
            except Exception:
                pass

        if keyboard:
            try:
                keyboard.send("+".join(normalized_keys))
                return True
            except Exception:
                pass

        return False

    def hold_key(self, key: str) -> bool:
        """
        Hold down a key.

        Args:
            key: Key to hold

        Returns:
            True if key held
        """
        key_normalized = self._normalize_key(key)

        if pg:
            try:
                pg.keyDown(key_normalized)
                return True
            except Exception:
                pass

        return False

    def release_key(self, key: str) -> bool:
        """
        Release a held key.

        Args:
            key: Key to release

        Returns:
            True if key released
        """
        key_normalized = self._normalize_key(key)

        if pg:
            try:
                pg.keyUp(key_normalized)
                return True
            except Exception:
                pass

        return False

    # ==================== Mouse ====================

    def click(self, x: int = None, y: int = None, button: str = "left") -> bool:
        """
        Click at a position.

        Args:
            x: X coordinate (current if None)
            y: Y coordinate (current if None)
            button: Mouse button (left, right, middle)

        Returns:
            True if clicked
        """
        if pg:
            try:
                if x is not None and y is not None:
                    pg.click(x, y, button=button)
                else:
                    pg.click(button=button)
                return True
            except Exception:
                pass
        return False

    def double_click(self, x: int = None, y: int = None) -> bool:
        """
        Double click at a position.

        Args:
            x: X coordinate (current if None)
            y: Y coordinate (current if None)

        Returns:
            True if clicked
        """
        if pg:
            try:
                if x is not None and y is not None:
                    pg.doubleClick(x, y)
                else:
                    pg.doubleClick()
                return True
            except Exception:
                pass
        return False

    def right_click(self, x: int = None, y: int = None) -> bool:
        """
        Right click at a position.

        Args:
            x: X coordinate (current if None)
            y: Y coordinate (current if None)

        Returns:
            True if clicked
        """
        return self.click(x, y, button="right")

    def move_cursor(self, x: int, y: int, duration: float = 0.25) -> bool:
        """
        Move cursor to a position.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Movement duration in seconds

        Returns:
            True if moved
        """
        if pg:
            try:
                pg.moveTo(x, y, duration=duration)
                return True
            except Exception:
                pass
        return False

    def scroll(self, amount: int, direction: str = "down") -> bool:
        """
        Scroll the mouse wheel.

        Args:
            amount: Number of "clicks" to scroll
            direction: "up" or "down"

        Returns:
            True if scrolled
        """
        if direction.lower() == "up":
            amount = abs(amount)
        else:
            amount = -abs(amount)

        if pg:
            try:
                pg.scroll(amount)
                return True
            except Exception:
                pass
        return False

    # ==================== Screen Capture ====================

    def screenshot(self, filename: str = None) -> Optional[str]:
        """
        Take a screenshot.

        Args:
            filename: Custom filename (auto-generated if None)

        Returns:
            Path to saved screenshot
        """
        if not pg:
            return None

        try:
            # Ensure directory exists
            os.makedirs(self.screenshots_dir, exist_ok=True)

            # Generate filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"

            filepath = os.path.join(self.screenshots_dir, filename)

            # Take screenshot
            screenshot = pg.screenshot()
            screenshot.save(filepath)

            self.speak("Screenshot saved")
            return filepath

        except Exception as e:
            print(f"[ERROR] Screenshot failed: {e}")
            return None

    def screenshot_region(
        self, x: int, y: int, width: int, height: int, filename: str = None
    ) -> Optional[str]:
        """
        Take a screenshot of a specific region.

        Args:
            x: Left coordinate
            y: Top coordinate
            width: Width of region
            height: Height of region
            filename: Custom filename

        Returns:
            Path to saved screenshot
        """
        if not pg:
            return None

        try:
            os.makedirs(self.screenshots_dir, exist_ok=True)

            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_region_{timestamp}.png"

            filepath = os.path.join(self.screenshots_dir, filename)

            screenshot = pg.screenshot(region=(x, y, width, height))
            screenshot.save(filepath)

            self.speak("Screenshot saved")
            return filepath

        except Exception as e:
            print(f"[ERROR] Screenshot region failed: {e}")
            return None

    # ==================== Directional Navigation ====================

    def move_direction(self, direction: str, query: str = "") -> bool:
        """
        Move/navigate in a direction.

        Args:
            direction: Direction (forward, backward, up, down, left, right)
            query: Optional query with context

        Returns:
            True if action performed
        """
        direction_lower = direction.lower().strip()

        # Map directions to keys or actions
        direction_map = {
            "forward": ["alt", "right"],  # Browser forward
            "backward": ["alt", "left"],  # Browser back
            "up": ["up"],
            "down": ["down"],
            "left": ["left"],
            "right": ["right"],
        }

        if direction_lower in direction_map:
            keys = direction_map[direction_lower]
            return self.hotkey(*keys)

        return False
