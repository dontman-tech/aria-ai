"""Phone control skill - manage the phone device itself.

Controls phone hardware and system settings: wifi, bluetooth, brightness,
volume, flashlight, airplane mode, open apps, get battery, send notifications.
Works via the ARIA companion app's HTTP bridge (Termux:API on Android, or
shortcuts on iOS). Falls back gracefully when not on a phone.
"""

from __future__ import annotations

import json
import logging
import platform
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from typing import Optional

from aria.skills.base import Skill, SkillResult

logger = logging.getLogger(__name__)


class PhoneControlSkill(Skill):
    name = "phone_control"
    description = "Control phone: wifi, bluetooth, brightness, flashlight, volume, battery, open apps"
    patterns = [
        r"\b(turn (on|off) (wifi|wi-fi|bluetooth|flashlight|torch|airplane mode))\b",
        r"\b(toggle|enable|disable) (wifi|wi-fi|bluetooth|flashlight|torch|airplane mode)\b",
        r"\b(phone )?brightness\b",
        r"\b(phone )?battery\b",
        r"\b(set phone volume|phone volume)\b",
        r"\b(do not disturb|dnd)\b",
        r"\b(phone|device) (info|status|info|temperature)\b",
        r"\b(send notification|notify)\b",
        r"\b(open (app|application))\b.*\bon (my )?phone\b",
        r"\b(take a (screenshot|photo))\b",
        r"\b(set (an )?alarm)\b",
    ]
    keywords = [
        "wifi", "wi-fi", "bluetooth", "flashlight", "torch", "airplane mode",
        "phone battery", "phone brightness", "do not disturb", "dnd",
        "phone status", "device info", "send notification", "take screenshot",
        "set alarm", "open app on phone",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._bridge_url = self._detect_bridge()

    def _detect_bridge(self) -> Optional[str]:
        """Detect an ARIA companion app bridge endpoint (Termux:API or similar)."""
        # Check for Termux:API bridge (Android)
        try:
            # Try the default Termux:API port
            test_url = "http://127.0.0.1:8080/api/status"
            req = urllib.request.Request(test_url, headers={"User-Agent": "ARIA/1.0"})
            urllib.request.urlopen(req, timeout=1)
            return "http://127.0.0.1:8080/api"
        except Exception:
            pass
        # Check for the ARIA companion app bridge
        try:
            test_url = "http://127.0.0.1:8420/aria/status"
            req = urllib.request.Request(test_url, headers={"User-Agent": "ARIA/1.0"})
            urllib.request.urlopen(req, timeout=1)
            return "http://127.0.0.1:8420/aria"
        except Exception:
            pass
        return None

    def _call_bridge(self, action: str, params: dict | None = None) -> Optional[dict]:
        """Call the phone companion bridge. Returns JSON response or None."""
        if not self._bridge_url:
            return None
        try:
            params = params or {}
            url = f"{self._bridge_url}/{action}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "ARIA/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.debug("Bridge call failed for %s: %s", action, e)
            return None

    @property
    def on_phone(self) -> bool:
        """Heuristic: are we running on a phone with the companion bridge?"""
        return self._bridge_url is not None

    def execute(self, text: str) -> SkillResult:
        lower = text.lower()

        if "wifi" in lower or "wi-fi" in lower:
            return self._toggle_setting(text, "wifi", lower)
        if "bluetooth" in lower:
            return self._toggle_setting(text, "bluetooth", lower)
        if "airplane" in lower or "aeroplane" in lower:
            return self._toggle_setting(text, "airplane_mode", lower)
        if "flashlight" in lower or "torch" in lower:
            return self._toggle_setting(text, "flashlight", lower)
        if "do not disturb" in lower or "dnd" in lower:
            return self._toggle_setting(text, "dnd", lower)
        if "brightness" in lower:
            return self._set_brightness(text)
        if "battery" in lower:
            return self._battery(text)
        if "notification" in lower or "notify" in lower:
            return self._send_notification(text)
        if "screenshot" in lower:
            return self._screenshot(text)
        if "alarm" in lower:
            return self._set_alarm(text)
        if "volume" in lower:
            return self._set_volume(text)
        if "phone status" in lower or "device info" in lower or "device status" in lower or "phone info" in lower:
            return self._device_info()

        return SkillResult(success=False, message="I can control wifi, bluetooth, brightness, flashlight, volume, battery, notifications, alarms, and more on your phone, Boss. What do you need?")

    def _toggle_setting(self, text: str, setting: str, lower: str) -> SkillResult:
        turn_on = any(w in lower for w in ("turn on", "enable", "switch on", "activate"))
        turn_off = any(w in lower for w in ("turn off", "disable", "switch off", "deactivate"))
        # If just toggling
        if not turn_on and not turn_off:
            turn_on = True  # default to toggle/on

        result = self._call_bridge(f"toggle_{setting}", {"state": "on" if turn_on else "off"})
        if result is None:
            return self._no_bridge_response(f"{'Enable' if turn_on else 'Disable'} {setting.replace('_', ' ')}")
        state = "on" if turn_on else "off"
        return SkillResult(success=True, message=f"{setting.replace('_', ' ').title()} is now {state}, Boss.", data=result)

    def _set_brightness(self, text: str) -> SkillResult:
        match = re.search(r"(\d+)\s*%?", text)
        if match:
            level = max(0, min(100, int(match.group(1))))
            result = self._call_bridge("set_brightness", {"level": level})
            if result is None:
                return self._no_bridge_response(f"Set brightness to {level}%")
            return SkillResult(success=True, message=f"Brightness set to {level}%, Boss.", data=result)
        return SkillResult(success=False, message="What brightness percentage, Boss?")

    def _set_volume(self, text: str) -> SkillResult:
        match = re.search(r"(\d+)\s*%?", text)
        if match:
            level = max(0, min(100, int(match.group(1))))
            result = self._call_bridge("set_volume", {"level": level})
            if result is None:
                return self._no_bridge_response(f"Set phone volume to {level}%")
            return SkillResult(success=True, message=f"Phone volume set to {level}%, Boss.", data=result)
        return SkillResult(success=False, message="What volume level, Boss?")

    def _battery(self, text: str) -> SkillResult:
        result = self._call_bridge("battery")
        if result is None:
            # Fallback to psutil
            try:
                import psutil

                battery = psutil.sensors_battery()
                if battery is None:
                    return SkillResult(success=False, message="No battery detected, Boss.")
                pct = battery.percent
                plugged = "plugged in" if battery.power_plugged else "on battery"
                return SkillResult(success=True, message=f"Battery at {pct:.0f}%, {plugged}, Boss.")
            except ImportError:
                return SkillResult(success=False, message="I can't read the battery without the companion app or psutil, Boss.")
        pct = result.get("percent", "?")
        charging = "charging" if result.get("charging") else "not charging"
        return SkillResult(success=True, message=f"Phone battery at {pct}%, {charging}, Boss.", data=result)

    def _send_notification(self, text: str) -> SkillResult:
        # Extract title and message
        match = re.search(r"['\"](.+?)['\"]\s*(?:with|saying)?\s*['\"]?(.+?)['\"]?$", text)
        if match:
            title = match.group(1)
            body = match.group(2)
        else:
            match2 = re.search(r"(?:notification|notify).*['\"](.+?)['\"]", text)
            title = "ARIA"
            body = match2.group(1) if match2 else "Notification from ARIA"
        result = self._call_bridge("notify", {"title": title, "body": body})
        if result is None:
            return self._no_bridge_response(f"Send notification: {title} - {body}")
        return SkillResult(success=True, message=f"Notification sent: {title}, Boss.", data=result)

    def _screenshot(self, text: str) -> SkillResult:
        result = self._call_bridge("screenshot")
        if result is None:
            return self._no_bridge_response("Take a screenshot")
        path = result.get("path", "screenshot.png")
        return SkillResult(success=True, message=f"Screenshot saved to {path}, Boss.", data=result)

    def _set_alarm(self, text: str) -> SkillResult:
        time_match = re.search(r"(\d{1,2}[:\s]\d{2}\s*(?:am|pm)?)", text, re.IGNORECASE)
        if time_match:
            alarm_time = time_match.group(1)
        else:
            alarm_time = "07:00"
        result = self._call_bridge("set_alarm", {"time": alarm_time})
        if result is None:
            return self._no_bridge_response(f"Set alarm for {alarm_time}")
        return SkillResult(success=True, message=f"Alarm set for {alarm_time}, Boss.", data=result)

    def _device_info(self) -> SkillResult:
        result = self._call_bridge("device_info")
        if result is None:
            # Fallback
            info = {
                "platform": platform.system(),
                "machine": platform.machine(),
                "node": platform.node(),
            }
            return SkillResult(success=True, message=f"Device: {info['platform']} on {info['node']}, Boss.", data=info)
        model = result.get("model", "Unknown")
        os_ver = result.get("os_version", "")
        return SkillResult(success=True, message=f"Device: {model}, OS {os_ver}, Boss.", data=result)

    def _no_bridge_response(self, action: str) -> SkillResult:
        """Response when the phone companion bridge is not available."""
        return SkillResult(
            success=False,
            message=(
                f"I'd {action.lower()} on your phone, Boss, but the ARIA companion app "
                "bridge isn't running. Install the ARIA companion app on your phone and "
                "enable the bridge so I can control the device directly."
            ),
        )
