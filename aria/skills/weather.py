"""Weather skill - gets current weather using Open-Meteo (no API key needed)."""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Optional

from aria.skills.base import Skill, SkillResult

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "freezing fog", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "heavy rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm with hail",
}


class WeatherSkill(Skill):
    name = "weather"
    description = "Get current weather for a location"
    patterns = [
        r"\bweather\b",
        r"\btemperature (in|for|at)\b",
        r"\bforecast\b",
        r"\bhow (hot|cold) is it\b",
    ]
    keywords = ["weather", "temperature", "forecast", "rain", "humidity"]

    def execute(self, text: str) -> SkillResult:
        location = self._extract_location(text)
        if not location:
            return SkillResult(success=False, message="Which location's weather do you need, Boss?")

        coords = self._geocode(location)
        if not coords:
            return SkillResult(success=False, message=f"I couldn't find '{location}' on the map, Boss.")

        weather = self._get_weather(coords["lat"], coords["lon"])
        if not weather:
            return SkillResult(success=False, message=f"I couldn't fetch the weather for {location}, Boss.")

        temp = weather.get("temperature_2m", "?")
        code = weather.get("weather_code", 0)
        desc = WMO_CODES.get(code, "unknown conditions")
        wind = weather.get("wind_speed_10m", "?")
        humidity = weather.get("relative_humidity_2m", "?")

        msg = (
            f"In {coords['name']}, it's {temp}°C with {desc}, "
            f"wind at {wind} km/h, humidity {humidity}%, Boss."
        )
        return SkillResult(success=True, message=msg, data={"location": coords["name"], **weather})

    def _extract_location(self, text: str) -> str:
        lower = text.lower()
        for trigger in ("weather in", "weather for", "weather at", "temperature in", "temperature for", "temperature at", "forecast for", "forecast in"):
            if trigger in lower:
                idx = lower.index(trigger) + len(trigger)
                return text[idx:].strip().strip("?").strip()
        if "weather" in lower or "forecast" in lower:
            # No location specified
            return ""
        return ""

    def _geocode(self, location: str) -> Optional[dict]:
        try:
            params = urllib.parse.urlencode({"name": location, "count": 1, "language": "en", "format": "json"})
            url = f"{GEOCODE_URL}?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "ARIA/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            results = data.get("results", [])
            if results:
                r = results[0]
                return {"lat": r["latitude"], "lon": r["longitude"], "name": r["name"]}
        except Exception as e:
            logger.debug("Geocode failed: %s", e)
        return None

    def _get_weather(self, lat: float, lon: float) -> Optional[dict]:
        try:
            params = urllib.parse.urlencode({
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            })
            url = f"{WEATHER_URL}?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "ARIA/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            return data.get("current", {})
        except Exception as e:
            logger.debug("Weather fetch failed: %s", e)
        return None
