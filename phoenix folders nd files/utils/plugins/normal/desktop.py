"""
Desktop Plugin - Virtual Desktop and Workspace Setup
=====================================================

Handles virtual desktop switching and workspace setup operations.
Extracted from UtilitiesPHNX.py desktop-related methods.

Actions:
    - switch_desktop: Switch to a virtual desktop
    - move_to_desktop: Move current window to desktop
    - setup_study: Set up study workspace
    - setup_trash: Set up leisure workspace
    - setup_alpha: Set up alpha workspace
"""

import os
import time
import subprocess
from typing import Optional

try:
    import pyautogui as pg
    import pygetwindow as gw
    import win32gui
    import win32con
except ImportError:
    pg = None
    gw = None
    win32gui = None
    win32con = None

try:
    from pyvda import VirtualDesktop, get_virtual_desktops

    PYVDA_AVAILABLE = True
except ImportError:
    PYVDA_AVAILABLE = False

from ..base import BasePlugin


class DesktopPlugin(BasePlugin):
    """Plugin for virtual desktop and workspace operations."""

    PLUGIN_NAME = "desktop"
    PLUGIN_DESCRIPTION = "Virtual desktop and workspace setup"

    # Desktop configurations
    DESKTOP_NAMES = {
        1: "Main",
        2: "Study",
        3: "Alpha",
        4: "Extra",
        5: "Trash",
    }

    def _register_actions(self) -> None:
        """Register all desktop-related actions."""
        # Virtual desktop navigation
        self.register(
            "switch_desktop", self.switch_desktop, "Switch to virtual desktop"
        )
        self.register("move_to_desktop", self.move_to_desktop, "Move window to desktop")
        self.register(
            "get_current_desktop",
            self.get_current_desktop,
            "Get current desktop number",
        )
        self.register(
            "create_desktop", self.create_desktop, "Create new virtual desktop"
        )
        self.register(
            "close_desktop", self.close_desktop, "Close current virtual desktop"
        )

        # Workspace setups
        self.register("setup_study", self.setup_study, "Set up study workspace")
        self.register("setup_alpha", self.setup_alpha, "Set up alpha workspace")
        self.register("setup_trash", self.setup_trash, "Set up leisure workspace")
        self.register("setup_extra", self.setup_extra, "Set up extra workspace")

        # Window organization
        self.register("show_desktop", self.show_desktop, "Show/minimize all windows")
        self.register("task_view", self.task_view, "Open Task View")

        # Focus management
        self.register("focus_phoenix", self.focus_phoenix, "Focus Phoenix window")
        self.register("set_focus", self.set_focus, "Set focus to active area")

    # ==================== Virtual Desktop Navigation ====================

    def switch_desktop(self, query: str) -> bool:
        """
        Switch to a specific virtual desktop.

        Args:
            query: Desktop number or name

        Returns:
            True if switched
        """
        # Parse desktop number
        desk_num = self._parse_desktop_number(query)

        if desk_num is None:
            self.speak("Which desktop should I switch to?")
            return False

        return self._switch_to_desktop(desk_num)

    def _parse_desktop_number(self, query: str) -> Optional[int]:
        """Parse desktop number from query."""
        import re

        # Try to find number in query
        numbers = re.findall(r"\d+", str(query))
        if numbers:
            return int(numbers[0])

        # Check for desktop names
        query_lower = query.lower()
        name_map = {
            "main": 1,
            "home": 1,
            "first": 1,
            "study": 2,
            "work": 2,
            "second": 2,
            "alpha": 3,
            "browse": 3,
            "third": 3,
            "extra": 4,
            "fourth": 4,
            "trash": 5,
            "leisure": 5,
            "fifth": 5,
        }

        for name, num in name_map.items():
            if name in query_lower:
                return num

        return None

    def _switch_to_desktop(self, desk_num: int) -> bool:
        """Switch to desktop by number."""
        if PYVDA_AVAILABLE:
            try:
                desktops = get_virtual_desktops()
                if 1 <= desk_num <= len(desktops):
                    desktops[desk_num - 1].go()
                    self.speak(f"Switched to desktop {desk_num}")
                    return True
            except Exception as e:
                print(f"[ERROR] pyvda switch failed: {e}")

        # Fallback to keyboard shortcuts
        if pg:
            try:
                pg.hotkey("win", "ctrl", str(desk_num))
                time.sleep(0.3)
                self.speak(f"Switched to desktop {desk_num}")
                return True
            except Exception:
                pass

        return False

    def move_to_desktop(self, desk_num: int) -> bool:
        """
        Move current window to a virtual desktop.

        Args:
            desk_num: Target desktop number

        Returns:
            True if moved
        """
        if PYVDA_AVAILABLE and gw:
            try:
                active_window = gw.getActiveWindow()
                if active_window:
                    desktops = get_virtual_desktops()
                    if 1 <= desk_num <= len(desktops):
                        # Get window handle
                        hwnd = win32gui.FindWindow(None, active_window.title)
                        from pyvda import get_apps_by_z_order, AppView

                        # Find the app and move it
                        for app in get_apps_by_z_order():
                            if app.hwnd == hwnd:
                                app.move(desktops[desk_num - 1])
                                self.speak(f"Window moved to desktop {desk_num}")
                                return True
            except Exception as e:
                print(f"[ERROR] Move to desktop failed: {e}")

        return False

    def get_current_desktop(self) -> Optional[int]:
        """
        Get the current virtual desktop number.

        Returns:
            Desktop number (1-indexed)
        """
        if PYVDA_AVAILABLE:
            try:
                current = VirtualDesktop.current()
                desktops = get_virtual_desktops()
                for i, desk in enumerate(desktops):
                    if desk == current:
                        return i + 1
            except Exception:
                pass

        return None

    def create_desktop(self) -> bool:
        """Create a new virtual desktop."""
        if pg:
            try:
                pg.hotkey("win", "ctrl", "d")
                self.speak("New desktop created")
                return True
            except Exception:
                pass
        return False

    def close_desktop(self) -> bool:
        """Close the current virtual desktop."""
        if pg:
            try:
                pg.hotkey("win", "ctrl", "F4")
                self.speak("Desktop closed")
                return True
            except Exception:
                pass
        return False

    # ==================== Workspace Setups ====================

    def setup_study(self) -> bool:
        """
        Set up study workspace - VS Code focused.

        Returns:
            True if setup completed
        """
        self.speak("Setting up study workspace")

        # Switch to study desktop
        self._switch_to_desktop(2)
        time.sleep(0.5)

        # Open/focus VS Code
        self._launch_app("Visual Studio Code")

        self.speak("Study setup complete")
        return True

    def setup_alpha(self) -> bool:
        """
        Set up alpha workspace - browsing focused.

        Returns:
            True if setup completed
        """
        self.speak("Setting up alpha workspace")

        # Switch to alpha desktop
        self._switch_to_desktop(3)
        time.sleep(0.5)

        # Open/focus Arc browser
        self._launch_app("Arc")

        self.speak("Alpha setup complete")
        return True

    def setup_trash(self) -> bool:
        """
        Set up trash/leisure workspace with multiple apps.

        Returns:
            True if setup completed
        """
        self.speak("Setting up leisure workspace")

        # Switch to trash desktop
        self._switch_to_desktop(5)
        time.sleep(0.5)

        # Apps to open
        apps = [
            "WhatsApp",
            "Spotify",
            "Armoury Crate",
        ]

        for app in apps:
            try:
                self._launch_app(app)
                time.sleep(1)
            except Exception:
                pass

        self.speak("Trash setup complete")
        return True

    def setup_extra(self) -> bool:
        """
        Set up extra workspace.

        Returns:
            True if setup completed
        """
        self.speak("Setting up extra workspace")

        # Switch to extra desktop
        self._switch_to_desktop(4)
        time.sleep(0.5)

        # Open Phone Link
        self._launch_app("Phone Link")

        self.speak("Extra setup complete")
        return True

    def _launch_app(self, app_name: str) -> bool:
        """Launch an application by searching for it."""
        if not gw or not pg:
            return False

        # Check if already open
        try:
            windows = gw.getWindowsWithTitle(app_name)
            if windows:
                # Focus existing window
                windows[0].activate()
                return True
        except Exception:
            pass

        # Open via Windows search
        try:
            pg.press("win")
            time.sleep(0.5)
            pg.typewrite(app_name, interval=0.03)
            time.sleep(0.5)
            pg.press("enter")
            time.sleep(1)
            return True
        except Exception:
            return False

    # ==================== Window Organization ====================

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

    def task_view(self) -> bool:
        """Open Task View."""
        if pg:
            try:
                pg.hotkey("win", "tab")
                return True
            except Exception:
                pass
        return False

    # ==================== Focus Management ====================

    def focus_phoenix(self) -> bool:
        """Focus the Phoenix console window."""
        if gw:
            try:
                windows = gw.getWindowsWithTitle("Phoenix")
                if windows:
                    windows[0].activate()
                    return True
            except Exception:
                pass
        return False

    def set_focus(self) -> bool:
        """
        Set focus to ensure keyboard input works.

        Returns:
            True if focus set
        """
        if pg:
            try:
                # Click in center of screen to ensure focus
                screen_width, screen_height = pg.size()
                pg.click(screen_width // 2, screen_height // 2)
                return True
            except Exception:
                pass
        return False
