"""App launch skill - open applications and URLs."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import webbrowser
from pathlib import Path

from aria.skills.base import Skill, SkillResult

# Common app name mappings
APP_ALIASES = {
    "chrome": "google chrome",
    "firefox": "firefox",
    "vscode": "code",
    "code": "code",
    "terminal": "terminal",
    "explorer": "explorer",
    "finder": "finder",
    "calculator": "calculator",
    "notepad": "notepad",
    "spotify": "spotify",
    "slack": "slack",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
}


class AppLaunchSkill(Skill):
    name = "apps"
    description = "Open applications and websites"
    patterns = [
        r"\bopen (the )?(app|application)?\s*[\w\s]+",
        r"\blaunch\s+[\w\s]+",
        r"\bstart\s+[\w\s]+",
        r"\bgo to\s+\w",
        r"\bvisit\s+\w",
    ]
    keywords = ["open", "launch", "start app", "go to", "visit"]

    def execute(self, text: str) -> SkillResult:
        lower = text.lower()

        # Check for URL
        url_match = re.search(r"(https?://\S+|www\.\S+|\S+\.(com|org|net|io|gov|edu))", text)
        if url_match or "go to" in lower or "visit" in lower:
            return self._open_url(text)

        # Extract app name
        app_name = self._extract_app_name(text)
        if not app_name:
            return SkillResult(success=False, message="What should I open, Boss?")

        return self._open_app(app_name)

    def _extract_app_name(self, text: str) -> str:
        lower = text.lower()
        for trigger in ("open the app", "open the application", "open", "launch", "start the app", "start"):
            if lower.startswith(trigger):
                name = text[len(trigger):].strip()
                name = re.sub(r"^(for me|up)?\s*", "", name).strip()
                return APP_ALIASES.get(name.lower(), name)
        return ""

    def _open_url(self, text: str) -> SkillResult:
        url_match = re.search(r"(https?://\S+|www\.\S+|\S+\.(com|org|net|io|gov|edu))", text)
        if url_match:
            url = url_match.group(1)
            if not url.startswith("http"):
                url = "https://" + url
        else:
            # Extract site name from "go to X" or "visit X"
            for trigger in ("go to", "visit"):
                if trigger in text.lower():
                    idx = text.lower().index(trigger) + len(trigger)
                    site = text[idx:].strip().strip("?.").strip()
                    url = f"https://{site}.com" if "." not in site else f"https://{site}"
                    break
            else:
                return SkillResult(success=False, message="Which site should I open, Boss?")

        try:
            webbrowser.open(url)
            return SkillResult(success=True, message=f"Opening {url}, Boss.")
        except Exception as e:
            return SkillResult(success=False, message=f"Couldn't open that: {e}")

    def _open_app(self, app_name: str) -> SkillResult:
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["open", "-a", app_name], check=False)
            elif system == "Linux":
                # Try the app name directly, or with common prefixes
                cmd = app_name.lower().replace(" ", "")
                if shutil.which(cmd):
                    subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                else:
                    subprocess.Popen(["xdg-open", app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif system == "Windows":
                subprocess.Popen(["start", "", app_name], shell=True)
            return SkillResult(success=True, message=f"Opening {app_name}, Boss.")
        except Exception as e:
            return SkillResult(success=False, message=f"Couldn't launch {app_name}: {e}")
