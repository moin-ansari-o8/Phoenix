"""
Information Plugin - Time, Date, Battery, Weather
=================================================

Handles information queries like time, date, battery status, weather.
Extracted from UtilitiesPHNX.py information methods.

Actions:
    - time: Get current time
    - date: Get current date
    - day: Get current day of week
    - battery: Get battery status
    - weather: Get weather information
    - greeting: Time-based greeting
"""

import os
import random
from datetime import datetime
from typing import Optional, Dict

try:
    import psutil
    import requests
except ImportError:
    psutil = None
    requests = None

from ..base import BasePlugin


class InformationPlugin(BasePlugin):
    """Plugin for information queries."""

    PLUGIN_NAME = "information"
    PLUGIN_DESCRIPTION = "Time, date, battery, and weather information"

    # Weather API configuration
    WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"

    # Time-based greetings
    GREETINGS = {
        "morning": [
            "Good morning sir.",
            "Morning sir, hope you slept well.",
            "Good morning! Ready for a productive day?",
        ],
        "afternoon": [
            "Good afternoon sir.",
            "Afternoon sir.",
            "Good afternoon! How's your day going?",
        ],
        "evening": [
            "Good evening sir.",
            "Evening sir.",
            "Good evening! Time to wind down.",
        ],
        "night": [
            "Good night sir.",
            "Night sir, rest well.",
            "Have a good night sir.",
        ],
    }

    def __init__(self, speech_engine=None, voice_recognition=None, config: dict = None):
        self.weather_api_key = os.getenv("OPENWEATHER_API_KEY", "")
        self.default_city = config.get("city", "London") if config else "London"
        super().__init__(speech_engine, voice_recognition, config)

    def _register_actions(self) -> None:
        """Register all information-related actions."""
        # Time and date
        self.register("time", self.get_time, "Get current time")
        self.register("date", self.get_date, "Get current date")
        self.register("day", self.get_day, "Get current day of week")
        self.register("datetime", self.get_datetime, "Get date and time")

        # Battery
        self.register("battery", self.get_battery, "Get battery status")
        self.register("battery_check", self.battery_check, "Check and announce battery")

        # Weather
        self.register("weather", self.get_weather, "Get weather information")
        self.register("weather_check", self.weather_check, "Check and announce weather")

        # Greetings
        self.register("greeting", self.time_based_greeting, "Time-appropriate greeting")
        self.register(
            "handle_greeting",
            self.handle_time_based_greeting,
            "Handle greeting by time of day",
        )

        # Random phrases
        self.register(
            "time_marker", self.get_time_marker, "Get 'It's' or 'The time is'"
        )
        self.register("water_reminder", self.water_reminder, "Remind to drink water")

    # ==================== Time and Date ====================

    def get_time(self) -> str:
        """
        Get current time in 12-hour format.

        Returns:
            Time string (e.g., "2:30 PM")
        """
        current_time = datetime.now().strftime("%I:%M %p")
        self.speak(f"The time is {current_time}")
        return current_time

    def get_date(self) -> str:
        """
        Get current date.

        Returns:
            Date string (e.g., "March 15, 2024")
        """
        current_date = datetime.now().strftime("%B %d, %Y")
        self.speak(f"Today is {current_date}")
        return current_date

    def get_day(self) -> str:
        """
        Get current day of week.

        Returns:
            Day string (e.g., "Friday")
        """
        day = datetime.now().strftime("%A")
        self.speak(f"Today is {day}")
        return day

    def get_datetime(self) -> Dict[str, str]:
        """
        Get both date and time.

        Returns:
            Dictionary with date, time, and day
        """
        now = datetime.now()
        result = {
            "date": now.strftime("%B %d, %Y"),
            "time": now.strftime("%I:%M %p"),
            "day": now.strftime("%A"),
        }

        self.speak(f"It's {result['day']}, {result['date']}, {result['time']}")
        return result

    # ==================== Battery ====================

    def get_battery(self) -> Optional[Dict]:
        """
        Get battery status information.

        Returns:
            Dictionary with percent, plugged status, and time remaining
        """
        if not psutil:
            return None

        try:
            battery = psutil.sensors_battery()
            if battery:
                return {
                    "percent": battery.percent,
                    "plugged": battery.power_plugged,
                    "time_left": battery.secsleft if battery.secsleft > 0 else None,
                }
        except Exception as e:
            print(f"[ERROR] Battery check failed: {e}")

        return None

    def battery_check(self) -> str:
        """
        Check and announce battery status.

        Returns:
            Battery status message
        """
        battery_info = self.get_battery()

        if not battery_info:
            self.speak("Could not get battery information")
            return "Unknown"

        percent = battery_info["percent"]
        plugged = battery_info["plugged"]

        if plugged:
            message = f"Battery is at {percent} percent and charging"
        elif percent <= 20:
            message = f"Battery is low at {percent} percent. Please plug in"
        elif percent <= 50:
            message = f"Battery is at {percent} percent"
        else:
            message = f"Battery is at {percent} percent"

        self.speak(message)
        return message

    # ==================== Weather ====================

    def get_weather(self, city: str = None) -> Optional[Dict]:
        """
        Get weather information for a city.

        Args:
            city: City name (uses default if not provided)

        Returns:
            Weather data dictionary
        """
        if not requests or not self.weather_api_key:
            return None

        city = city or self.default_city

        try:
            params = {
                "q": city,
                "appid": self.weather_api_key,
                "units": "metric",
            }
            response = requests.get(self.WEATHER_API_URL, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                return {
                    "city": data["name"],
                    "temp": data["main"]["temp"],
                    "feels_like": data["main"]["feels_like"],
                    "humidity": data["main"]["humidity"],
                    "description": data["weather"][0]["description"],
                    "wind_speed": data["wind"]["speed"],
                }
        except Exception as e:
            print(f"[ERROR] Weather fetch failed: {e}")

        return None

    def weather_check(self, query: str = "") -> str:
        """
        Check and announce weather.

        Args:
            query: Optional query containing city name

        Returns:
            Weather message
        """
        # Extract city from query
        city = None
        if query:
            # Simple extraction - look for "in <city>" pattern
            import re

            match = re.search(r"(?:in|for|at)\s+(.+?)(?:\?|$)", query, re.IGNORECASE)
            if match:
                city = match.group(1).strip()

        weather = self.get_weather(city)

        if not weather:
            # Fallback message
            message = "Sorry, I couldn't get weather information"
            self.speak(message)
            return message

        temp = round(weather["temp"])
        feels = round(weather["feels_like"])
        desc = weather["description"]
        city_name = weather["city"]

        message = f"In {city_name}, it's {temp} degrees with {desc}. Feels like {feels} degrees"
        self.speak(message)
        return message

    # ==================== Greetings ====================

    def time_based_greeting(self) -> str:
        """
        Get a greeting appropriate for the time of day.

        Returns:
            Greeting string
        """
        hour = datetime.now().hour

        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 17:
            period = "afternoon"
        elif 17 <= hour < 21:
            period = "evening"
        else:
            period = "night"

        greeting = random.choice(self.GREETINGS[period])
        self.speak(greeting)
        return greeting

    def handle_time_based_greeting(self, tag: str, response: str = "") -> str:
        """
        Handle greeting based on time-of-day tag.

        Args:
            tag: Greeting tag (morning, afternoon, evening)
            response: Optional pre-defined response

        Returns:
            Greeting message
        """
        if tag in self.GREETINGS:
            greeting = random.choice(self.GREETINGS[tag])
        else:
            greeting = self.time_based_greeting()

        self.speak(greeting)
        return greeting

    # ==================== Random Phrases ====================

    def get_time_marker(self) -> str:
        """
        Get random time announcement prefix.

        Returns:
            Phrase like "It's" or "The time is"
        """
        markers = [
            "It's",
            "The time is",
            "Currently it's",
            "Right now it's",
        ]
        return random.choice(markers)

    def water_reminder(self) -> str:
        """
        Get water reminder message.

        Returns:
            Hydration reminder
        """
        reminders = [
            "Be hydrated, sir.",
            "Drink some water, sir, be hydrated.",
            "Do drink water, be hydrated.",
            "Time for some water, sir.",
            "Stay hydrated, sir.",
        ]
        message = random.choice(reminders)
        self.speak(message)
        return message
