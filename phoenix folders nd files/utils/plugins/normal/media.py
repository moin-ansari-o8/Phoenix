"""
Media Plugin - Music and Audio Controls
========================================

Handles music playback, volume control, and audio management.
Extracted from UtilitiesPHNX.py media-related methods.

Actions:
    - play_song: Play a specific song
    - play_random: Play random song from library
    - play_pause: Toggle play/pause
    - next_track: Skip to next track
    - previous_track: Go to previous track
    - adjust_volume: Set/adjust volume
    - mute: Mute audio
    - unmute: Unmute audio
    - suggest_song: Suggest a song to play
"""

import os
import random
import json
import subprocess
import time
from typing import Optional, List

try:
    import pyautogui as pg
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
except ImportError:
    pg = None
    AudioUtilities = None

from ..base import BasePlugin


class MediaPlugin(BasePlugin):
    """Plugin for media and audio control operations."""

    PLUGIN_NAME = "media"
    PLUGIN_DESCRIPTION = "Music playback and audio controls"

    # Default songs directory
    DEFAULT_SONGS_DIR = r"C:\Users\{user}\Music"

    def __init__(self, speech_engine=None, voice_recognition=None, config: dict = None):
        self.user = os.getenv("USERNAME", "")
        self.songs_dir = config.get("songs_dir") if config else None
        if not self.songs_dir:
            self.songs_dir = self.DEFAULT_SONGS_DIR.format(user=self.user)

        # Songs database file
        phoenix_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.songs_file = os.path.join(phoenix_root, "data", "songs.json")

        super().__init__(speech_engine, voice_recognition, config)

    def _register_actions(self) -> None:
        """Register all media-related actions."""
        # Playback controls
        self.register("play_song", self.play_song, "Play a specific song")
        self.register("play_random", self.play_random_song, "Play random song")
        self.register("play_pause", self.play_pause, "Toggle play/pause")
        self.register("next_track", self.next_track, "Skip to next track")
        self.register("previous_track", self.previous_track, "Go to previous track")
        self.register("stop", self.stop_playback, "Stop playback")

        # Volume controls
        self.register("adjust_volume", self.adjust_volume, "Adjust system volume")
        self.register("set_volume", self.set_volume, "Set volume to specific level")
        self.register("mute", self.mute, "Mute audio")
        self.register("unmute", self.unmute, "Unmute audio")
        self.register("volume_up", self.volume_up, "Increase volume")
        self.register("volume_down", self.volume_down, "Decrease volume")

        # Song management
        self.register("suggest_song", self.suggest_song, "Suggest a song to play")
        self.register("add_song", self.add_song, "Add song to library")
        self.register("delete_song", self.delete_song, "Remove song from library")
        self.register("view_songs", self.view_songs, "List songs in library")

        # Rock mode
        self.register("rock_mode", self.rock_mode, "Enable rock music mode")

    def _load_songs(self) -> List[dict]:
        """Load songs from the songs database."""
        try:
            if os.path.exists(self.songs_file):
                with open(self.songs_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("songs", [])
        except Exception as e:
            print(f"[ERROR] Failed to load songs: {e}")
        return []

    def _save_songs(self, songs: List[dict]) -> bool:
        """Save songs to the songs database."""
        try:
            data = {"songs": songs}
            with open(self.songs_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save songs: {e}")
            return False

    def _get_volume_interface(self):
        """Get the Windows audio volume interface."""
        if not AudioUtilities:
            return None

        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))
        except Exception as e:
            print(f"[ERROR] Failed to get volume interface: {e}")
            return None

    # ==================== Playback Controls ====================

    def play_song(self, query: str) -> bool:
        """
        Play a specific song by name.

        Args:
            query: Song name or search term

        Returns:
            True if song started playing
        """
        songs = self._load_songs()
        query_lower = query.lower()

        # Find matching song
        for song in songs:
            if query_lower in song.get("name", "").lower():
                song_path = song.get("path", "")
                if os.path.exists(song_path):
                    try:
                        os.startfile(song_path)
                        self.speak(f"Playing {song.get('name', 'song')}")
                        return True
                    except Exception as e:
                        print(f"[ERROR] Failed to play: {e}")

        # If not in library, try Spotify search
        self.speak(f"Searching for {query}")
        return self._play_via_spotify(query)

    def _play_via_spotify(self, query: str) -> bool:
        """Search and play song via Spotify."""
        try:
            import webbrowser

            search_url = f"spotify:search:{query}"
            webbrowser.open(search_url)
            return True
        except Exception:
            return False

    def play_random_song(self, query: str = "") -> bool:
        """
        Play a random song from the library.

        Args:
            query: Optional filter for song selection

        Returns:
            True if song started playing
        """
        songs = self._load_songs()

        if not songs:
            self.speak("No songs in the library")
            return False

        # Filter if query provided
        if query:
            query_lower = query.lower()
            songs = [s for s in songs if query_lower in s.get("name", "").lower()]

        if not songs:
            self.speak("No matching songs found")
            return False

        # Pick random song
        song = random.choice(songs)
        song_path = song.get("path", "")

        if os.path.exists(song_path):
            try:
                os.startfile(song_path)
                self.speak(f"Playing {song.get('name', 'a random song')}")
                return True
            except Exception:
                pass

        self.speak("Couldn't play the song")
        return False

    def play_pause(self, query: str = "") -> bool:
        """Toggle play/pause for media."""
        if pg:
            try:
                pg.press("playpause")
                return True
            except Exception:
                pass
        return False

    def next_track(self) -> bool:
        """Skip to the next track."""
        if pg:
            try:
                pg.press("nexttrack")
                self.speak("Next track")
                return True
            except Exception:
                pass
        return False

    def previous_track(self) -> bool:
        """Go to the previous track."""
        if pg:
            try:
                pg.press("prevtrack")
                self.speak("Previous track")
                return True
            except Exception:
                pass
        return False

    def stop_playback(self) -> bool:
        """Stop media playback."""
        if pg:
            try:
                pg.press("stop")
                self.speak("Stopping playback")
                return True
            except Exception:
                pass
        return False

    # ==================== Volume Controls ====================

    def adjust_volume(self, query: str) -> bool:
        """
        Adjust volume based on query.

        Args:
            query: Natural language query (e.g., "increase volume by 20")

        Returns:
            True if volume adjusted
        """
        query_lower = query.lower()

        # Parse direction and amount
        if "mute" in query_lower:
            return self.mute()
        elif "unmute" in query_lower:
            return self.unmute()
        elif "max" in query_lower or "full" in query_lower:
            return self.set_volume(100)
        elif "half" in query_lower:
            return self.set_volume(50)

        # Try to extract number
        import re

        numbers = re.findall(r"\d+", query)
        amount = int(numbers[0]) if numbers else 10

        if any(word in query_lower for word in ["up", "increase", "raise", "higher"]):
            return self.volume_up(amount)
        elif any(
            word in query_lower for word in ["down", "decrease", "lower", "reduce"]
        ):
            return self.volume_down(amount)
        elif any(word in query_lower for word in ["set", "to"]):
            return self.set_volume(amount)

        return False

    def set_volume(self, level: int) -> bool:
        """
        Set volume to a specific level (0-100).

        Args:
            level: Volume level percentage

        Returns:
            True if volume set
        """
        level = max(0, min(100, level))  # Clamp to 0-100

        volume = self._get_volume_interface()
        if volume:
            try:
                volume.SetMasterVolumeLevelScalar(level / 100, None)
                self.speak(f"Volume set to {level} percent")
                return True
            except Exception as e:
                print(f"[ERROR] Set volume failed: {e}")

        return False

    def volume_up(self, amount: int = 10) -> bool:
        """
        Increase volume by a percentage.

        Args:
            amount: Percentage to increase (default 10)

        Returns:
            True if volume increased
        """
        volume = self._get_volume_interface()
        if volume:
            try:
                current = volume.GetMasterVolumeLevelScalar() * 100
                new_level = min(100, current + amount)
                volume.SetMasterVolumeLevelScalar(new_level / 100, None)
                self.speak(f"Volume up to {int(new_level)} percent")
                return True
            except Exception:
                pass

        # Fallback to keyboard
        if pg:
            for _ in range(amount // 2):
                pg.press("volumeup")
            return True

        return False

    def volume_down(self, amount: int = 10) -> bool:
        """
        Decrease volume by a percentage.

        Args:
            amount: Percentage to decrease (default 10)

        Returns:
            True if volume decreased
        """
        volume = self._get_volume_interface()
        if volume:
            try:
                current = volume.GetMasterVolumeLevelScalar() * 100
                new_level = max(0, current - amount)
                volume.SetMasterVolumeLevelScalar(new_level / 100, None)
                self.speak(f"Volume down to {int(new_level)} percent")
                return True
            except Exception:
                pass

        # Fallback to keyboard
        if pg:
            for _ in range(amount // 2):
                pg.press("volumedown")
            return True

        return False

    def mute(self) -> bool:
        """Mute system audio."""
        volume = self._get_volume_interface()
        if volume:
            try:
                volume.SetMute(1, None)
                self.speak("Muted")
                return True
            except Exception:
                pass

        # Fallback to keyboard
        if pg:
            pg.press("volumemute")
            return True

        return False

    def unmute(self) -> bool:
        """Unmute system audio."""
        volume = self._get_volume_interface()
        if volume:
            try:
                volume.SetMute(0, None)
                self.speak("Unmuted")
                return True
            except Exception:
                pass

        # Fallback to keyboard
        if pg:
            pg.press("volumemute")  # Toggle
            return True

        return False

    # ==================== Song Management ====================

    def suggest_song(self) -> str:
        """
        Suggest a random song from the library.

        Returns:
            Song suggestion text
        """
        songs = self._load_songs()

        if not songs:
            self.speak("No songs in the library to suggest")
            return ""

        song = random.choice(songs)
        name = song.get("name", "Unknown")

        suggestions = [
            f"How about {name}?",
            f"What about {name}?",
            f"You might like {name}",
            f"I suggest {name}",
        ]

        suggestion = random.choice(suggestions)
        self.speak(suggestion)
        return suggestion

    def add_song(self, name: str = "", path: str = "") -> bool:
        """
        Add a song to the library.

        Args:
            name: Song name
            path: Path to the song file

        Returns:
            True if song added
        """
        if not name or not path:
            self.speak("Please provide song name and path")
            return False

        songs = self._load_songs()

        # Check if already exists
        for song in songs:
            if song.get("path") == path:
                self.speak("Song already in library")
                return False

        # Add new song
        songs.append(
            {"name": name, "path": path, "added": time.strftime("%Y-%m-%d %H:%M")}
        )

        if self._save_songs(songs):
            self.speak(f"Added {name} to library")
            return True

        return False

    def delete_song(self, name: str = "") -> bool:
        """
        Remove a song from the library.

        Args:
            name: Song name to remove

        Returns:
            True if song removed
        """
        if not name:
            self.speak("Please provide song name to delete")
            return False

        songs = self._load_songs()
        name_lower = name.lower()

        # Find and remove
        new_songs = [s for s in songs if name_lower not in s.get("name", "").lower()]

        if len(new_songs) < len(songs):
            if self._save_songs(new_songs):
                self.speak(f"Removed {name} from library")
                return True
        else:
            self.speak(f"Couldn't find {name} in library")

        return False

    def view_songs(self) -> List[str]:
        """
        List all songs in the library.

        Returns:
            List of song names
        """
        songs = self._load_songs()

        if not songs:
            self.speak("Library is empty")
            return []

        names = [s.get("name", "Unknown") for s in songs]
        self.speak(f"You have {len(names)} songs in your library")

        return names

    def rock_mode(self, volume_level: float = 0.8) -> bool:
        """
        Enable rock music mode - high volume, bass boost.

        Args:
            volume_level: Volume level (0.0 to 1.0)

        Returns:
            True if mode enabled
        """
        # Set high volume
        self.set_volume(int(volume_level * 100))

        # Play random rock song (if tagged)
        songs = self._load_songs()
        rock_songs = [s for s in songs if "rock" in s.get("genre", "").lower()]

        if rock_songs:
            song = random.choice(rock_songs)
            song_path = song.get("path", "")
            if os.path.exists(song_path):
                os.startfile(song_path)
                self.speak("Rock mode activated")
                return True

        self.speak("Rock mode ready, volume maxed")
        return True
