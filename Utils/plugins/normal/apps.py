"""
Apps Plugin - Application Open/Close Operations
================================================

Handles opening and closing applications via voice commands.
Extracts and consolidates OpenAppHandler and CloseAppHandler from UtilitiesPHNX.py.

Actions:
    - open_*: Open specific applications (brave, arc, code, spotify, etc.)
    - close_*: Close specific applications
    - open_app: Generic app opener
    - close_app: Generic app closer
"""

import os
import subprocess
import time
import webbrowser
from typing import Optional, Dict, List

try:
    import pygetwindow as gw
    import win32gui
    import win32con
    import pyautogui as pg
except ImportError:
    gw = None
    win32gui = None
    win32con = None
    pg = None

from ..base import BasePlugin


class AppsPlugin(BasePlugin):
    """Plugin for opening and closing applications."""

    PLUGIN_NAME = "apps"
    PLUGIN_DESCRIPTION = "Application open/close operations"

    # Application paths and configurations
    APP_PATHS = {
        "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        "arc": r"C:\Users\{user}\AppData\Local\Arc\Application\Arc.exe",
        "code": "code",  # VS Code CLI
        "spotify": r"{appdata}\Spotify\Spotify.exe",
        "discord": r"{localappdata}\Discord\Update.exe --processStart Discord.exe",
        "steam": r"C:\Program Files (x86)\Steam\steam.exe",
        "epic": r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
        "obs": r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "explorer": "explorer.exe",
        "settings": "ms-settings:",
        "control": "control.exe",
    }

    # Window title patterns for finding apps
    WINDOW_PATTERNS = {
        "brave": ["Brave"],
        "arc": ["Arc"],
        "code": ["Visual Studio Code", "VS Code"],
        "spotify": ["Spotify"],
        "discord": ["Discord"],
        "whatsapp": ["WhatsApp"],
        "chrome": ["Google Chrome", "Chrome"],
        "firefox": ["Firefox", "Mozilla Firefox"],
        "edge": ["Edge", "Microsoft Edge"],
    }

    def __init__(self, speech_engine=None, voice_recognition=None, config: dict = None):
        self.user = os.getenv("USERNAME", "")
        self.appdata = os.getenv("APPDATA", "")
        self.localappdata = os.getenv("LOCALAPPDATA", "")
        super().__init__(speech_engine, voice_recognition, config)

    def _register_actions(self) -> None:
        """Register all app-related actions."""
        # Generic operations
        self.register("open_app", self.open_app, "Open application by name")
        self.register("close_app", self.close_app, "Close application by name")
        self.register("focus_app", self.focus_app, "Focus/bring to front application")
        self.register("is_running", self.is_app_running, "Check if app is running")

        # Specific app openers
        self.register("open_brave", self.open_brave, "Open Brave browser")
        self.register("open_arc", self.open_arc, "Open Arc browser")
        self.register("open_code", self.open_code, "Open VS Code")
        self.register("open_spotify", self.open_spotify, "Open Spotify")
        self.register("open_discord", self.open_discord, "Open Discord")
        self.register("open_whatsapp", self.open_whatsapp, "Open WhatsApp")
        self.register("open_steam", self.open_steam, "Open Steam")
        self.register("open_epic", self.open_epic, "Open Epic Games")
        self.register("open_obs", self.open_obs, "Open OBS Studio")
        self.register("open_vlc", self.open_vlc, "Open VLC")
        self.register("open_notepad", self.open_notepad, "Open Notepad")
        self.register("open_calculator", self.open_calculator, "Open Calculator")
        self.register("open_cmd", self.open_cmd, "Open Command Prompt")
        self.register("open_powershell", self.open_powershell, "Open PowerShell")
        self.register("open_explorer", self.open_explorer, "Open File Explorer")
        self.register("open_settings", self.open_settings, "Open Windows Settings")
        self.register("open_control", self.open_control, "Open Control Panel")

        # Web shortcuts
        self.register("open_youtube", self.open_youtube, "Open YouTube")
        self.register("open_google", self.open_google, "Open Google")
        self.register("open_github", self.open_github, "Open GitHub")
        self.register("open_chatgpt", self.open_chatgpt, "Open ChatGPT")

        # Close operations
        self.register(
            "close_particular", self.close_particular_app, "Close specific app"
        )

    def _resolve_path(self, path: str) -> str:
        """Resolve path variables like {user}, {appdata}."""
        return path.format(
            user=self.user, appdata=self.appdata, localappdata=self.localappdata
        )

    def _get_windows_by_pattern(self, patterns: List[str]) -> List:
        """Get windows matching any of the given patterns."""
        if not gw:
            return []

        windows = []
        for pattern in patterns:
            try:
                found = gw.getWindowsWithTitle(pattern)
                windows.extend(found)
            except Exception:
                pass
        return windows

    def _find_window_by_name(self, app_name: str):
        """Find a window by application name."""
        if not win32gui:
            return None

        app_lower = app_name.lower()
        result = {"hwnd": None}

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if app_lower in title:
                    result["hwnd"] = hwnd
                    return False
            return True

        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass

        return result["hwnd"]

    # ==================== Generic Operations ====================

    def open_app(self, app_name: str) -> bool:
        """
        Open an application by name.

        Args:
            app_name: Name of the application (e.g., "brave", "spotify")

        Returns:
            True if opened successfully
        """
        app_lower = app_name.lower().strip()

        # Check if already running and focus it
        if self.is_app_running(app_lower):
            self.focus_app(app_lower)
            self.speak(f"{app_name} is already open, bringing to front")
            return True

        # Try known app paths
        if app_lower in self.APP_PATHS:
            path = self._resolve_path(self.APP_PATHS[app_lower])
            try:
                if path.startswith("ms-"):
                    # Windows URI
                    os.startfile(path)
                else:
                    subprocess.Popen(path, shell=True)
                self.speak(f"Opening {app_name}")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to open {app_name}: {e}")

        # Try Windows search fallback
        return self._open_via_search(app_name)

    def _open_via_search(self, app_name: str) -> bool:
        """Open app via Windows Start menu search."""
        if not pg:
            return False

        try:
            pg.press("win")
            time.sleep(0.5)
            pg.typewrite(app_name, interval=0.05)
            time.sleep(0.5)
            pg.press("enter")
            self.speak(f"Opening {app_name}")
            return True
        except Exception as e:
            print(f"[ERROR] Search open failed: {e}")
            return False

    def close_app(self, app_name: str) -> bool:
        """
        Close an application by name.

        Args:
            app_name: Name of the application to close

        Returns:
            True if closed successfully
        """
        hwnd = self._find_window_by_name(app_name)

        if hwnd and win32gui:
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                self.speak(f"Closing {app_name}")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to close {app_name}: {e}")

        self.speak(f"Couldn't find {app_name}")
        return False

    def focus_app(self, app_name: str) -> bool:
        """Bring an application window to the foreground."""
        hwnd = self._find_window_by_name(app_name)

        if hwnd and win32gui and win32con:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return True
            except Exception:
                pass

        return False

    def is_app_running(self, app_name: str) -> bool:
        """Check if an application is currently running."""
        patterns = self.WINDOW_PATTERNS.get(app_name.lower(), [app_name])
        windows = self._get_windows_by_pattern(patterns)
        return len(windows) > 0

    def close_particular_app(self, query: str) -> bool:
        """Close a specific app mentioned in the query."""
        # Extract app name from query
        keywords = ["close", "quit", "exit", "kill", "end"]
        app_name = query.lower()

        for kw in keywords:
            app_name = app_name.replace(kw, "").strip()

        return self.close_app(app_name)

    # ==================== Specific App Openers ====================

    def open_brave(self) -> bool:
        """Open Brave browser."""
        return self.open_app("brave")

    def open_arc(self) -> bool:
        """Open Arc browser."""
        return self.open_app("arc")

    def open_code(self, folder: str = None) -> bool:
        """Open VS Code, optionally with a folder."""
        try:
            if folder:
                subprocess.Popen(f'code "{folder}"', shell=True)
            else:
                subprocess.Popen("code", shell=True)
            self.speak("Opening VS Code")
            return True
        except Exception:
            return self._open_via_search("Visual Studio Code")

    def open_spotify(self) -> bool:
        """Open Spotify."""
        return self.open_app("spotify")

    def open_discord(self) -> bool:
        """Open Discord."""
        return self.open_app("discord")

    def open_whatsapp(self) -> bool:
        """Open WhatsApp."""
        return self._open_via_search("WhatsApp")

    def open_steam(self) -> bool:
        """Open Steam."""
        return self.open_app("steam")

    def open_epic(self) -> bool:
        """Open Epic Games Launcher."""
        return self.open_app("epic")

    def open_obs(self) -> bool:
        """Open OBS Studio."""
        return self.open_app("obs")

    def open_vlc(self) -> bool:
        """Open VLC Media Player."""
        return self.open_app("vlc")

    def open_notepad(self) -> bool:
        """Open Notepad."""
        subprocess.Popen("notepad.exe")
        self.speak("Opening Notepad")
        return True

    def open_calculator(self) -> bool:
        """Open Calculator."""
        subprocess.Popen("calc.exe")
        self.speak("Opening Calculator")
        return True

    def open_cmd(self) -> bool:
        """Open Command Prompt."""
        subprocess.Popen("cmd.exe")
        self.speak("Opening Command Prompt")
        return True

    def open_powershell(self) -> bool:
        """Open PowerShell."""
        subprocess.Popen("powershell.exe")
        self.speak("Opening PowerShell")
        return True

    def open_explorer(self, path: str = None) -> bool:
        """Open File Explorer, optionally to a specific path."""
        if path:
            subprocess.Popen(f'explorer "{path}"')
        else:
            subprocess.Popen("explorer.exe")
        self.speak("Opening File Explorer")
        return True

    def open_settings(self) -> bool:
        """Open Windows Settings."""
        os.startfile("ms-settings:")
        self.speak("Opening Settings")
        return True

    def open_control(self) -> bool:
        """Open Control Panel."""
        subprocess.Popen("control.exe")
        self.speak("Opening Control Panel")
        return True

    # ==================== Web Shortcuts ====================

    def open_youtube(self) -> bool:
        """Open YouTube in default browser."""
        webbrowser.open("https://www.youtube.com")
        self.speak("Opening YouTube")
        return True

    def open_google(self) -> bool:
        """Open Google in default browser."""
        webbrowser.open("https://www.google.com")
        self.speak("Opening Google")
        return True

    def open_github(self) -> bool:
        """Open GitHub in default browser."""
        webbrowser.open("https://github.com")
        self.speak("Opening GitHub")
        return True

    def open_chatgpt(self) -> bool:
        """Open ChatGPT in default browser."""
        webbrowser.open("https://chat.openai.com")
        self.speak("Opening ChatGPT")
        return True
