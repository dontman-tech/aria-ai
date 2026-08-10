"""Time and date skill."""

from __future__ import annotations

from datetime import datetime

from aria.skills.base import Skill, SkillResult


class TimeDateSkill(Skill):
    name = "time_date"
    description = "Get the current time, date, or day of the week"
    patterns = [
        r"\b(what\s+)?(time|date|day)\b",
        r"\bwhat day is it\b",
        r"\btoday'?s date\b",
    ]
    keywords = ["time", "date", "what day", "today"]

    def execute(self, text: str) -> SkillResult:
        lower = text.lower()
        now = datetime.now()

        if "date" in lower or ("day" in lower and "what" in lower):
            date_str = now.strftime("%A, %B %d, %Y")
            return SkillResult(success=True, message=f"Today is {date_str}, Boss.")
        if "day" in lower:
            day_str = now.strftime("%A")
            return SkillResult(success=True, message=f"It's {day_str}, Boss.")
        # default: time
        time_str = now.strftime("%I:%M %p")
        return SkillResult(success=True, message=f"It's {time_str}, Boss.")
