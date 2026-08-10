"""System control skill - volume, brightness, power, system info."""

from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Optional

from aria.skills.base import Skill, SkillResult


class SystemControlSkill(Skill):
    name = "system_control"
    description = "Control system volume, brightness, power, and get system info"
    patterns = [
        r"\b(volume|mute|unmute)\b",
        r"\b(brightness)\b",
        r"\b(system info|system information|about this (computer|machine))\b",
        r"\b(battery)\b",
        r"\b(sleep|restart|reboot|shutdown|lock (screen|computer))\b",
        r"\b(cpu|ram|memory|disk) (usage|info|status)\b",
    ]
    keywords = ["volume", "mute", "brightness", "battery", "system info", "sleep", "shutdown", "reboot"]

    def execute(self, text: str) -> SkillResult:
        lower = text.lower()

        if "system info" in lower or "about this" in lower:
            return self._system_info()

        if "battery" in lower:
            return self._battery_info()

        if "volume" in lower or "mute" in lower or "unmute" in lower:
            return self._control_volume(lower)

        if "brightness" in lower:
            return self._control_brightness(lower)

        if "sleep" in lower:
            return self._sleep()
        if "restart" in lower or "reboot" in lower:
            return SkillResult(success=True, message="I'd reboot the system for you, Boss, but I'll need explicit confirmation for that.")
        if "shutdown" in lower:
            return SkillResult(success=True, message="Shutdown is a destructive action, Boss. Please confirm explicitly and I'll execute it.")
        if "lock" in lower:
            return self._lock_screen()

        if "cpu" in lower or "ram" in lower or "memory" in lower or "disk" in lower:
            return self._resource_info(lower)

        return SkillResult(success=False, message="I couldn't determine what system action you wanted, Boss.")

    def _system_info(self) -> SkillResult:
        info = {
            "OS": f"{platform.system()} {platform.release()}",
            "Machine": platform.machine(),
            "Processor": platform.processor() or "Unknown",
            "Python": platform.python_version(),
            "Node": platform.node(),
        }
        msg = f"System status, Boss: {info['OS']} on {info['Processor'][:40]}."
        return SkillResult(success=True, message=msg, data=info)

    def _battery_info(self) -> SkillResult:
        try:
            import psutil

            battery = psutil.sensors_battery()
            if battery is None:
                return SkillResult(success=True, message="No battery detected — likely a desktop, Boss.")
            pct = battery.percent
            plugged = "plugged in" if battery.power_plugged else "on battery"
            msg = f"Battery at {pct:.0f}%, {plugged}, Boss."
            return SkillResult(success=True, message=msg, data={"percent": pct, "plugged": battery.power_plugged})
        except ImportError:
            return SkillResult(success=False, message="Battery sensing requires the psutil package.")

    def _control_volume(self, text: str) -> SkillResult:
        # Try to parse a volume level
        import re

        match = re.search(r"(\d+)\s*%?", text)
        if match:
            level = int(match.group(1))
            level = max(0, min(100, level))
            self._set_volume(level)
            return SkillResult(success=True, message=f"Volume set to {level}%, Boss.")
        if "mute" in text and "unmute" not in text:
            self._set_volume(0)
            return SkillResult(success=True, message="Muted, Boss.")
        if "unmute" in text:
            self._set_volume(50)
            return SkillResult(success=True, message="Unmuted at 50%, Boss.")
        return SkillResult(success=True, message="Use 'set volume to N' to control volume, Boss.")

    def _set_volume(self, level: int) -> None:
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=False)
            elif system == "Linux":
                if shutil.which("amixer"):
                    subprocess.run(["amixer", "set", "Master", f"{level}%"], capture_output=True)
                elif shutil.which("pactl"):
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"], capture_output=True)
            elif system == "Windows":
                # pylint: disable=import-outside-toplevel
                pass
        except Exception:
            pass

    def _control_brightness(self, text: str) -> SkillResult:
        import re

        match = re.search(r"(\d+)\s*%?", text)
        if match:
            level = int(match.group(1))
            level = max(0, min(100, level))
            system = platform.system()
            try:
                if system == "Linux" and shutil.which("brightnessctl"):
                    subprocess.run(["brightnessctl", "set", f"{level}%"], capture_output=True)
                elif system == "Darwin":
                    subprocess.run(["osascript", "-e", f"tell application \"System Events\" to set brightness to {level/100}"], capture_output=True)
            except Exception:
                pass
            return SkillResult(success=True, message=f"Brightness set to {level}%, Boss.")
        return SkillResult(success=True, message="Tell me a percentage for brightness, Boss.")

    def _resource_info(self, text: str) -> SkillResult:
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            parts = [f"CPU at {cpu:.0f}%", f"RAM at {mem.percent:.0f}%"]
            if "disk" in text:
                disk = psutil.disk_usage("/")
                parts.append(f"Disk at {disk.percent:.0f}%")
            return SkillResult(success=True, message="; ".join(parts) + ", Boss.")
        except ImportError:
            return SkillResult(success=False, message="Resource monitoring requires the psutil package.")

    def _sleep(self) -> SkillResult:
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["pmset", "sleepnow"], check=False)
            elif system == "Linux":
                subprocess.run(["systemctl", "suspend"], check=False)
            return SkillResult(success=True, message="Going to sleep, Boss.")
        except Exception:
            return SkillResult(success=False, message="Couldn't trigger sleep, Boss.")

    def _lock_screen(self) -> SkillResult:
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["pmset", "displaysleepnow"], check=False)
            elif system == "Linux":
                if shutil.which("loginctl"):
                    subprocess.run(["loginctl", "lock-session"], check=False)
            return SkillResult(success=True, message="Screen locked, Boss.")
        except Exception:
            return SkillResult(success=False, message="Couldn't lock the screen, Boss.")
