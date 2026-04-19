"""
Browser Plugin - Web Browser and Search Operations
===================================================

Handles browser control and web searches.
Extracted from UtilitiesPHNX.py browser-related methods.

Actions:
    - search_google: Search on Google
    - search_youtube: Search on YouTube
    - search_browser: Search in current browser
    - new_tab: Open new browser tab
    - close_tab: Close current tab
    - switch_tab: Switch between tabs
    - navigate: Navigate to URL
"""

import webbrowser
import time
import re
from typing import Optional
from urllib.parse import quote_plus

try:
    import pyautogui as pg
except ImportError:
    pg = None

from ..base import BasePlugin


class BrowserPlugin(BasePlugin):
    """Plugin for browser and web search operations."""

    PLUGIN_NAME = "browser"
    PLUGIN_DESCRIPTION = "Browser control and web searches"

    # Search URLs
    SEARCH_URLS = {
        "google": "https://www.google.com/search?q=",
        "youtube": "https://www.youtube.com/results?search_query=",
        "bing": "https://www.bing.com/search?q=",
        "duckduckgo": "https://duckduckgo.com/?q=",
        "wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search=",
        "github": "https://github.com/search?q=",
        "stackoverflow": "https://stackoverflow.com/search?q=",
        "amazon": "https://www.amazon.com/s?k=",
        "flipkart": "https://www.flipkart.com/search?q=",
        "myntra": "https://www.myntra.com/search?q=",
        "instagram": "https://www.instagram.com/explore/search/keyword/?q=",
    }

    # Direct URLs
    SITES = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://github.com",
        "chatgpt": "https://chat.openai.com",
        "gmail": "https://mail.google.com",
        "drive": "https://drive.google.com",
        "twitter": "https://twitter.com",
        "reddit": "https://www.reddit.com",
        "linkedin": "https://www.linkedin.com",
        "amazon": "https://www.amazon.com",
        "flipkart": "https://www.flipkart.com",
        "myntra": "https://www.myntra.com",
    }

    def _register_actions(self) -> None:
        """Register all browser-related actions."""
        # Search operations
        self.register("search_google", self.search_google, "Search on Google")
        self.register("search_youtube", self.search_youtube, "Search on YouTube")
        self.register("search_browser", self.search_browser, "Search in browser")
        self.register("search_wikipedia", self.search_wikipedia, "Search Wikipedia")
        self.register("search_github", self.search_github, "Search GitHub")
        self.register("search_instagram", self.search_instagram, "Search Instagram")

        # Shopping
        self.register("amazon", self.search_amazon, "Search Amazon")
        self.register("flipkart", self.search_flipkart, "Search Flipkart")
        self.register("myntra", self.search_myntra, "Search Myntra")

        # Tab controls
        self.register("new_tab", self.new_tab, "Open new tab")
        self.register("close_tab", self.close_tab, "Close current tab")
        self.register("switch_tab", self.switch_tab, "Switch tabs")
        self.register("change_tab", self.change_tab, "Change to specific tab")
        self.register("next_tab", self.next_tab, "Go to next tab")
        self.register("prev_tab", self.prev_tab, "Go to previous tab")

        # Navigation
        self.register("navigate", self.navigate, "Navigate to URL")
        self.register("open_site", self.open_site, "Open a website")
        self.register("refresh", self.refresh_page, "Refresh current page")
        self.register("back", self.go_back, "Go back")
        self.register("forward", self.go_forward, "Go forward")

    def _extract_query(self, text: str, keywords: list) -> str:
        """Extract search query by removing keywords."""
        query = text.lower()
        for kw in keywords:
            query = query.replace(kw, "").strip()
        return query

    # ==================== Search Operations ====================

    def search_google(self, query: str) -> bool:
        """
        Search on Google.

        Args:
            query: Search query

        Returns:
            True if search opened
        """
        clean_query = self._extract_query(query, ["search", "google", "for", "on"])
        if not clean_query:
            self.speak("What should I search for?")
            return False

        url = self.SEARCH_URLS["google"] + quote_plus(clean_query)
        webbrowser.open(url)
        self.speak(f"Searching for {clean_query}")
        return True

    def search_youtube(self, query: str) -> bool:
        """
        Search on YouTube.

        Args:
            query: Search query

        Returns:
            True if search opened
        """
        clean_query = self._extract_query(
            query, ["search", "youtube", "for", "on", "video"]
        )
        if not clean_query:
            self.speak("What should I search on YouTube?")
            return False

        url = self.SEARCH_URLS["youtube"] + quote_plus(clean_query)
        webbrowser.open(url)
        self.speak(f"Searching YouTube for {clean_query}")
        return True

    def search_browser(self, query: str = "") -> bool:
        """
        Search in the current browser's search bar.

        Args:
            query: Search query

        Returns:
            True if search initiated
        """
        clean_query = self._extract_query(query, ["search", "for", "browser"])

        if not clean_query:
            # Just open new tab with focus on search
            if pg:
                pg.hotkey("ctrl", "l")
            return True

        # Use Google by default
        return self.search_google(clean_query)

    def search_wikipedia(self, query: str) -> bool:
        """Search Wikipedia."""
        clean_query = self._extract_query(
            query, ["search", "wikipedia", "wiki", "for", "on"]
        )
        if not clean_query:
            self.speak("What should I search on Wikipedia?")
            return False

        url = self.SEARCH_URLS["wikipedia"] + quote_plus(clean_query)
        webbrowser.open(url)
        self.speak(f"Searching Wikipedia for {clean_query}")
        return True

    def search_github(self, query: str) -> bool:
        """Search GitHub."""
        clean_query = self._extract_query(query, ["search", "github", "for", "on"])
        if not clean_query:
            self.speak("What should I search on GitHub?")
            return False

        url = self.SEARCH_URLS["github"] + quote_plus(clean_query)
        webbrowser.open(url)
        self.speak(f"Searching GitHub for {clean_query}")
        return True

    def search_instagram(self, query: str) -> bool:
        """Search Instagram."""
        clean_query = self._extract_query(
            query, ["search", "instagram", "insta", "for", "on"]
        )
        if not clean_query:
            self.speak("Who should I search on Instagram?")
            return False

        url = self.SEARCH_URLS["instagram"] + quote_plus(clean_query)
        webbrowser.open(url)
        self.speak(f"Searching Instagram for {clean_query}")
        return True

    # ==================== Shopping ====================

    def search_amazon(self, query: str = "") -> bool:
        """Search or open Amazon."""
        clean_query = self._extract_query(
            query, ["search", "amazon", "for", "on", "buy"]
        )

        if clean_query:
            url = self.SEARCH_URLS["amazon"] + quote_plus(clean_query)
            self.speak(f"Searching Amazon for {clean_query}")
        else:
            url = self.SITES["amazon"]
            self.speak("Opening Amazon")

        webbrowser.open(url)
        return True

    def search_flipkart(self, query: str = "") -> bool:
        """Search or open Flipkart."""
        clean_query = self._extract_query(
            query, ["search", "flipkart", "for", "on", "buy"]
        )

        if clean_query:
            url = self.SEARCH_URLS["flipkart"] + quote_plus(clean_query)
            self.speak(f"Searching Flipkart for {clean_query}")
        else:
            url = self.SITES["flipkart"]
            self.speak("Opening Flipkart")

        webbrowser.open(url)
        return True

    def search_myntra(self, query: str = "") -> bool:
        """Search or open Myntra."""
        clean_query = self._extract_query(
            query, ["search", "myntra", "for", "on", "buy"]
        )

        if clean_query:
            url = self.SEARCH_URLS["myntra"] + quote_plus(clean_query)
            self.speak(f"Searching Myntra for {clean_query}")
        else:
            url = self.SITES["myntra"]
            self.speak("Opening Myntra")

        webbrowser.open(url)
        return True

    # ==================== Tab Controls ====================

    def new_tab(self) -> bool:
        """Open a new browser tab."""
        if pg:
            try:
                pg.hotkey("ctrl", "t")
                self.speak("New tab opened")
                return True
            except Exception:
                pass
        return False

    def close_tab(self) -> bool:
        """Close the current browser tab."""
        if pg:
            try:
                pg.hotkey("ctrl", "w")
                self.speak("Tab closed")
                return True
            except Exception:
                pass
        return False

    def switch_tab(self) -> bool:
        """Switch to the next tab."""
        if pg:
            try:
                pg.hotkey("ctrl", "tab")
                return True
            except Exception:
                pass
        return False

    def change_tab(self, query: str) -> bool:
        """
        Change to a specific tab by number.

        Args:
            query: Query containing tab number

        Returns:
            True if tab changed
        """
        # Extract number from query
        numbers = re.findall(r"\d+", query)
        if not numbers:
            return self.switch_tab()

        tab_num = int(numbers[0])

        if pg and 1 <= tab_num <= 9:
            try:
                pg.hotkey("ctrl", str(tab_num))
                self.speak(f"Switched to tab {tab_num}")
                return True
            except Exception:
                pass

        return False

    def next_tab(self) -> bool:
        """Go to the next tab."""
        if pg:
            try:
                pg.hotkey("ctrl", "tab")
                return True
            except Exception:
                pass
        return False

    def prev_tab(self) -> bool:
        """Go to the previous tab."""
        if pg:
            try:
                pg.hotkey("ctrl", "shift", "tab")
                return True
            except Exception:
                pass
        return False

    # ==================== Navigation ====================

    def navigate(self, url: str) -> bool:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to

        Returns:
            True if navigation started
        """
        # Add https if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        webbrowser.open(url)
        self.speak(f"Navigating to {url.split('//')[1].split('/')[0]}")
        return True

    def open_site(self, site_name: str) -> bool:
        """
        Open a known website.

        Args:
            site_name: Name of the site (youtube, google, etc.)

        Returns:
            True if site opened
        """
        site_lower = site_name.lower().strip()

        if site_lower in self.SITES:
            webbrowser.open(self.SITES[site_lower])
            self.speak(f"Opening {site_name}")
            return True

        # Try direct navigation
        return self.navigate(site_name)

    def refresh_page(self) -> bool:
        """Refresh the current page."""
        if pg:
            try:
                pg.press("F5")
                self.speak("Refreshing")
                return True
            except Exception:
                pass
        return False

    def go_back(self) -> bool:
        """Go back to the previous page."""
        if pg:
            try:
                pg.hotkey("alt", "left")
                return True
            except Exception:
                pass
        return False

    def go_forward(self) -> bool:
        """Go forward to the next page."""
        if pg:
            try:
                pg.hotkey("alt", "right")
                return True
            except Exception:
                pass
        return False
