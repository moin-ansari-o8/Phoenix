"""
Console UI for Phoenix - Clean TUI-style output
Status line stays at bottom, conversation blocks scroll above
Also manages speaking state for self-voice suppression
"""

import sys
import os
from datetime import datetime
from threading import Lock
import time

# ANSI escape codes for terminal control
CLEAR_LINE = "\033[2K"
MOVE_UP = "\033[1A"
CURSOR_START = "\r"
SAVE_CURSOR = "\033[s"
RESTORE_CURSOR = "\033[u"

# Status states
STATUS_LISTENING = "Listening..."
STATUS_DETECTED = "Voice detected..."
STATUS_PROCESSING = "Processing..."
STATUS_SPEAKING = "Speaking..."
STATUS_READY = "Ready"


class ConsoleUI:
    """
    Singleton console UI manager for Phoenix.
    Provides clean TUI-style output with:
    - Status line that updates in-place at the bottom
    - Conversation blocks that scroll above
    - Speaking state management for self-voice suppression
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._status = STATUS_LISTENING
        self._print_lock = Lock()
        self._last_status_printed = False

        # Speaking state for self-voice suppression
        self._is_speaking = False
        self._speaking_end_time = 0  # Time when speaking ended + buffer
        self._speaking_buffer = 1.5  # Seconds to ignore audio after speaking

    @staticmethod
    def get_timestamp():
        """Get current time as HH:MM:SS"""
        return datetime.now().strftime("%H:%M:%S")

    def start_speaking(self):
        """Called when Phoenix starts speaking"""
        self._is_speaking = True
        self.set_status(STATUS_SPEAKING)

    def stop_speaking(self):
        """Called when Phoenix stops speaking"""
        self._is_speaking = False
        self._speaking_end_time = time.time() + self._speaking_buffer
        self.set_status(STATUS_LISTENING)

    def should_ignore_audio(self):
        """Check if we should ignore audio (Phoenix is speaking or just finished)"""
        if self._is_speaking:
            return True
        if time.time() < self._speaking_end_time:
            return True
        return False

    def is_speaking(self):
        """Check if Phoenix is currently speaking"""
        return self._is_speaking

    def _clear_status_line(self):
        """Clear the current status line"""
        sys.stdout.write(f"{CURSOR_START}{CLEAR_LINE}")
        sys.stdout.flush()

    def _print_status(self):
        """Print the current status (overwrites current line)"""
        sys.stdout.write(f"{CURSOR_START}{CLEAR_LINE}{self._status}")
        sys.stdout.flush()
        self._last_status_printed = True

    def set_status(self, status: str):
        """Update the status line (in-place)"""
        with self._print_lock:
            self._status = status
            self._print_status()

    def listening(self):
        """Set status to listening"""
        self.set_status(STATUS_LISTENING)

    def detected(self):
        """Set status to voice detected"""
        self.set_status(STATUS_DETECTED)

    def processing(self):
        """Set status to processing"""
        self.set_status(STATUS_PROCESSING)

    def ready(self):
        """Set status to ready"""
        self.set_status(STATUS_READY)

    def print_block(self, text: str):
        """
        Print a conversation block (scrolls up, status stays at bottom).
        Use this for: user said, phoenix said, errors, etc.
        """
        with self._print_lock:
            # Clear current status line
            self._clear_status_line()
            # Print the block with newline
            print(text)
            # Reprint status at bottom
            self._print_status()

    def user_said(self, text: str, timestamp: str = None):
        """Print what the user said"""
        ts = timestamp or self.get_timestamp()
        self.print_block(f'👤 You [{ts}]: "{text}"')

    def phoenix_said(self, text: str):
        """Print what Phoenix said"""
        ts = self.get_timestamp()
        self.print_block(f"🔊 Phoenix [{ts}]: {text}")

    def info(self, text: str):
        """Print info message"""
        self.print_block(f"ℹ️  {text}")

    def error(self, text: str):
        """Print error message"""
        self.print_block(f"⚠️  {text}")

    def startup_banner(self):
        """Print startup banner"""
        banner = """
╔═══════════════════════════════════════════════════════════════╗
║                      PHOENIX VOICE ASSISTANT                   ║
╠═══════════════════════════════════════════════════════════════╣
║  Speak naturally, pause 0.8s when done. Press Ctrl+C to exit. ║
╚═══════════════════════════════════════════════════════════════╝
"""
        print(banner)
        self._print_status()


# Global instance
_ui = None


def get_ui() -> ConsoleUI:
    """Get the global ConsoleUI instance"""
    global _ui
    if _ui is None:
        _ui = ConsoleUI()
    return _ui


# Convenience functions for direct import
def set_status(status: str):
    get_ui().set_status(status)


def listening():
    get_ui().listening()


def detected():
    get_ui().detected()


def processing():
    get_ui().processing()


def ready():
    get_ui().ready()


def user_said(text: str, timestamp: str = None):
    get_ui().user_said(text, timestamp)


def phoenix_said(text: str):
    get_ui().phoenix_said(text)


def print_block(text: str):
    get_ui().print_block(text)


def info(text: str):
    get_ui().info(text)


def error(text: str):
    get_ui().error(text)


def startup_banner():
    get_ui().startup_banner()


def get_timestamp():
    return ConsoleUI.get_timestamp()


def start_speaking():
    get_ui().start_speaking()


def stop_speaking():
    get_ui().stop_speaking()


def should_ignore_audio():
    return get_ui().should_ignore_audio()


def is_speaking():
    return get_ui().is_speaking()
