"""
Windows Plugin - Window Management
===================================

Handles window operations like minimize, maximize, move, resize.
Extracted from UtilitiesPHNX.py window management methods.

Actions:
    - minimize: Minimize window
    - maximize: Maximize window
    - restore: Restore window from minimized/maximized
    - close: Close window
    - fullscreen: Toggle fullscreen
    - hide: Hide window
    - move: Move window to position
    - resize: Resize window
    - focus: Bring window to front
    - pin: Pin window on top
"""

import time
from typing import Optional, Tuple, List

try:
    import pygetwindow as gw
    import pyautogui as pg
    import win32gui
    import win32con
except ImportError:
    gw = None
    pg = None
    win32gui = None
    win32con = None

from ..base import BasePlugin


class WindowsPlugin(BasePlugin):
    """Plugin for window management operations."""

    PLUGIN_NAME = "windows"
    PLUGIN_DESCRIPTION = "Window management and control"

    # Predefined positions
    POSITIONS = {
        "left": {"x": 0, "width_ratio": 0.5},
        "right": {"x": 0.5, "width_ratio": 0.5},
        "top": {"y": 0, "height_ratio": 0.5},
        "bottom": {"y": 0.5, "height_ratio": 0.5},
        "center": {"x": 0.25, "y": 0.25, "width_ratio": 0.5, "height_ratio": 0.5},
        "topleft": {"x": 0, "y": 0, "width_ratio": 0.5, "height_ratio": 0.5},
        "topright": {"x": 0.5, "y": 0, "width_ratio": 0.5, "height_ratio": 0.5},
        "bottomleft": {"x": 0, "y": 0.5, "width_ratio": 0.5, "height_ratio": 0.5},
        "bottomright": {"x": 0.5, "y": 0.5, "width_ratio": 0.5, "height_ratio": 0.5},
    }

    def __init__(self, speech_engine=None, voice_recognition=None, config: dict = None):
        # Get screen dimensions
        try:
            self.screen_width = pg.size()[0] if pg else 1920
            self.screen_height = pg.size()[1] if pg else 1080
        except Exception:
            self.screen_width = 1920
            self.screen_height = 1080

        super().__init__(speech_engine, voice_recognition, config)

    def _register_actions(self) -> None:
        """Register all window-related actions."""
        # Basic window operations
        self.register("minimize", self.minimize_window, "Minimize active window")
        self.register("maximize", self.maximize_window, "Maximize active window")
        self.register("restore", self.restore_window, "Restore window")
        self.register("close", self.close_window, "Close active window")
        self.register("fullscreen", self.toggle_fullscreen, "Toggle fullscreen")
        self.register("hide", self.hide_window, "Hide window")

        # Window positioning
        self.register("move", self.move_window, "Move window to position")
        self.register("resize", self.resize_window, "Resize window")
        self.register("snap", self.snap_window, "Snap window to position")
        self.register("center", self.center_window, "Center window on screen")

        # Focus and arrangement
        self.register("focus", self.focus_window, "Focus/bring window to front")
        self.register("pin", self.pin_window, "Pin window always on top")
        self.register("unpin", self.unpin_window, "Unpin window from top")

        # Information
        self.register("list_windows", self.list_windows, "List all open windows")
        self.register("get_active", self.get_active_window, "Get active window info")
        self.register("get_position", self.get_window_position, "Get window position")

        # Window actions
        self.register(
            "perform_action", self.perform_window_action, "Perform window action by tag"
        )
        self.register("desktop", self.show_desktop, "Show desktop")

    def _get_active_window(self):
        """Get the currently active window."""
        if gw:
            try:
                return gw.getActiveWindow()
            except Exception:
                pass
        return None

    def _get_window_by_title(self, title: str):
        """Find window by title (partial match)."""
        if gw:
            try:
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    return windows[0]
            except Exception:
                pass
        return None

    # ==================== Basic Window Operations ====================

    def minimize_window(self, title: str = None) -> bool:
        """
        Minimize a window.

        Args:
            title: Window title (active window if None)

        Returns:
            True if minimized
        """
        window = (
            self._get_window_by_title(title) if title else self._get_active_window()
        )

        if window:
            try:
                window.minimize()
                self.speak("Window minimized")
                return True
            except Exception as e:
                print(f"[ERROR] Minimize failed: {e}")

        return False

    def maximize_window(self, title: str = None) -> bool:
        """
        Maximize a window.

        Args:
            title: Window title (active window if None)

        Returns:
            True if maximized
        """
        window = (
            self._get_window_by_title(title) if title else self._get_active_window()
        )

        if window:
            try:
                window.maximize()
                self.speak("Window maximized")
                return True
            except Exception as e:
                print(f"[ERROR] Maximize failed: {e}")

        return False

    def restore_window(self, title: str = None) -> bool:
        """
        Restore a window from minimized/maximized state.

        Args:
            title: Window title (active window if None)

        Returns:
            True if restored
        """
        window = (
            self._get_window_by_title(title) if title else self._get_active_window()
        )

        if window:
            try:
                window.restore()
                self.speak("Window restored")
                return True
            except Exception as e:
                print(f"[ERROR] Restore failed: {e}")

        return False

    def close_window(self, title: str = None) -> bool:
        """
        Close a window.

        Args:
            title: Window title (active window if None)

        Returns:
            True if closed
        """
        window = (
            self._get_window_by_title(title) if title else self._get_active_window()
        )

        if window:
            try:
                window.close()
                self.speak("Window closed")
                return True
            except Exception:
                pass

        # Fallback to Alt+F4
        if pg:
            try:
                pg.hotkey("alt", "F4")
                return True
            except Exception:
                pass

        return False

    def toggle_fullscreen(self) -> bool:
        """Toggle fullscreen mode (F11)."""
        if pg:
            try:
                pg.press("F11")
                self.speak("Toggling fullscreen")
                return True
            except Exception:
                pass
        return False

    def hide_window(self, title: str = None) -> bool:
        """
        Hide a window (minimize to tray).

        Args:
            title: Window title (active window if None)

        Returns:
            True if hidden
        """
        return self.minimize_window(title)

    # ==================== Window Positioning ====================

    def move_window(self, position: str) -> bool:
        """
        Move window to a predefined position.

        Args:
            position: Position name (left, right, center, etc.) or desk number

        Returns:
            True if moved
        """
        position_lower = position.lower().strip()

        # Check for desk number (1-9)
        if position_lower.isdigit():
            desk_num = int(position_lower)
            return self._move_to_virtual_desktop(desk_num)

        window = self._get_active_window()
        if not window:
            return False

        if position_lower in self.POSITIONS:
            pos = self.POSITIONS[position_lower]
            x = int(pos.get("x", 0) * self.screen_width)
            y = int(pos.get("y", 0) * self.screen_height)
            width = int(pos.get("width_ratio", 1) * self.screen_width)
            height = int(pos.get("height_ratio", 1) * self.screen_height)

            try:
                window.moveTo(x, y)
                window.resizeTo(width, height)
                self.speak(f"Window moved to {position}")
                return True
            except Exception as e:
                print(f"[ERROR] Move failed: {e}")

        return False

    def _move_to_virtual_desktop(self, desk_num: int) -> bool:
        """Move current window to a virtual desktop."""
        if pg:
            try:
                # Win+Shift+number not standard, use pyvda approach
                pg.hotkey("win", "ctrl", str(desk_num))
                return True
            except Exception:
                pass
        return False

    def resize_window(self, width: int, height: int, title: str = None) -> bool:
        """
        Resize a window.

        Args:
            width: New width in pixels
            height: New height in pixels
            title: Window title (active window if None)

        Returns:
            True if resized
        """
        window = (
            self._get_window_by_title(title) if title else self._get_active_window()
        )

        if window:
            try:
                window.resizeTo(width, height)
                self.speak("Window resized")
                return True
            except Exception as e:
                print(f"[ERROR] Resize failed: {e}")

        return False

    def snap_window(self, position: str) -> bool:
        """
        Snap window to screen edge using Windows shortcuts.

        Args:
            position: Position (left, right, up, down, topleft, etc.)

        Returns:
            True if snapped
        """
        if not pg:
            return False

        position_lower = position.lower().strip()

        snap_keys = {
            "left": ["win", "left"],
            "right": ["win", "right"],
            "up": ["win", "up"],
            "down": ["win", "down"],
            "maximize": ["win", "up"],
            "minimize": ["win", "down"],
            "topleft": ["win", "left", "up"],
            "topright": ["win", "right", "up"],
            "bottomleft": ["win", "left", "down"],
            "bottomright": ["win", "right", "down"],
        }

        if position_lower in snap_keys:
            try:
                keys = snap_keys[position_lower]
                if len(keys) == 2:
                    pg.hotkey(keys[0], keys[1])
                elif len(keys) == 3:
                    pg.hotkey(keys[0], keys[1])
                    time.sleep(0.2)
                    pg.hotkey(keys[0], keys[2])
                self.speak(f"Window snapped to {position}")
                return True
            except Exception:
                pass

        return False

    def center_window(self, title: str = None) -> bool:
        """
        Center a window on the screen.

        Args:
            title: Window title (active window if None)

        Returns:
            True if centered
        """
        window = (
            self._get_window_by_title(title) if title else self._get_active_window()
        )

        if window:
            try:
                x = (self.screen_width - window.width) // 2
                y = (self.screen_height - window.height) // 2
                window.moveTo(x, y)
                self.speak("Window centered")
                return True
            except Exception:
                pass

        return False

    # ==================== Focus and Arrangement ====================

    def focus_window(self, title: str) -> bool:
        """
        Bring a window to the foreground.

        Args:
            title: Window title to focus

        Returns:
            True if focused
        """
        window = self._get_window_by_title(title)

        if window:
            try:
                window.activate()
                return True
            except Exception:
                pass

        return False

    def pin_window(self, title: str = None) -> bool:
        """
        Pin window to stay always on top.

        Args:
            title: Window title (active window if None)

        Returns:
            True if pinned
        """
        if not win32gui or not win32con:
            return False

        window = (
            self._get_window_by_title(title) if title else self._get_active_window()
        )

        if window:
            try:
                hwnd = win32gui.FindWindow(None, window.title)
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_TOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                )
                self.speak("Window pinned on top")
                return True
            except Exception:
                pass

        return False

    def unpin_window(self, title: str = None) -> bool:
        """
        Remove always-on-top from window.

        Args:
            title: Window title (active window if None)

        Returns:
            True if unpinned
        """
        if not win32gui or not win32con:
            return False

        window = (
            self._get_window_by_title(title) if title else self._get_active_window()
        )

        if window:
            try:
                hwnd = win32gui.FindWindow(None, window.title)
                win32gui.SetWindowPos(
                    hwnd,
                    win32con.HWND_NOTOPMOST,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
                )
                self.speak("Window unpinned")
                return True
            except Exception:
                pass

        return False

    # ==================== Information ====================

    def list_windows(self) -> List[str]:
        """
        List all visible windows.

        Returns:
            List of window titles
        """
        windows = []

        if gw:
            try:
                all_windows = gw.getAllTitles()
                windows = [w for w in all_windows if w.strip()]
            except Exception:
                pass

        if windows:
            self.speak(f"Found {len(windows)} open windows")

        return windows

    def get_active_window(self) -> Optional[dict]:
        """
        Get information about the active window.

        Returns:
            Dictionary with window info
        """
        window = self._get_active_window()

        if window:
            return {
                "title": window.title,
                "left": window.left,
                "top": window.top,
                "width": window.width,
                "height": window.height,
                "is_active": window.isActive,
                "is_maximized": window.isMaximized,
                "is_minimized": window.isMinimized,
            }

        return None

    def get_window_position(
        self, title: str = None
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Get window position (x, y, width, height).

        Args:
            title: Window title (active window if None)

        Returns:
            Tuple of (x, y, width, height)
        """
        window = (
            self._get_window_by_title(title) if title else self._get_active_window()
        )

        if window:
            return (window.left, window.top, window.width, window.height)

        return None

    # ==================== Actions ====================

    def perform_window_action(self, action: str) -> bool:
        """
        Perform window action by name.

        Args:
            action: Action name (minimize, maximize, hide, fullscreen)

        Returns:
            True if action performed
        """
        action_lower = action.lower().strip()

        action_map = {
            "minimize": self.minimize_window,
            "maximize": self.maximize_window,
            "restore": self.restore_window,
            "close": self.close_window,
            "fullscreen": self.toggle_fullscreen,
            "hide": self.hide_window,
            "center": self.center_window,
        }

        if action_lower in action_map:
            return action_map[action_lower]()

        return False

    def show_desktop(self) -> bool:
        """Show desktop (minimize all windows)."""
        if pg:
            try:
                pg.hotkey("win", "d")
                self.speak("Showing desktop")
                return True
            except Exception:
                pass
        return False
