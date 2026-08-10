"""Memory skill - remember and recall facts about the user."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from aria.skills.base import Skill, SkillResult

if TYPE_CHECKING:
    from aria.core.memory import Memory


class MemorySkill(Skill):
    name = "memory"
    description = "Remember and recall facts about the user"
    patterns = [
        r"\b(remember|note|my name is|call me|i like|i prefer|my favorite)\b",
        r"\b(what.?s my|do you know my|what do you know about me)\b",
        r"\b(forget|reset|clear) (memory|everything|what you know)\b",
    ]
    keywords = ["remember", "my name", "call me", "i like", "i prefer", "my favorite", "what's my name", "forget"]

    def __init__(self, memory: "Memory | None" = None) -> None:
        super().__init__()
        self._memory = memory

    def set_memory(self, memory: "Memory") -> None:
        self._memory = memory

    def execute(self, text: str) -> SkillResult:
        if self._memory is None:
            return SkillResult(success=False, message="Memory system not initialized, Boss.")
        lower = text.lower()

        if "forget" in lower or "reset" in lower or "clear" in lower:
            self._memory.reset_all()
            return SkillResult(success=True, message="I've cleared my memory, Boss. Fresh start.")

        if "what's my name" in lower or "whats my name" in lower or "do you know my name" in lower:
            name = self._memory.recall("name")
            if name:
                return SkillResult(success=True, message=f"Your name is {name}, Boss.")
            return SkillResult(success=True, message="I don't know your name yet, Boss. Tell me and I'll remember.")

        if "what do you know about me" in lower:
            ctx = self._memory._profile_context()
            if ctx:
                return SkillResult(success=True, message=f"Here's what I know: {ctx}")
            return SkillResult(success=True, message="I don't know much about you yet, Boss. Tell me about yourself.")

        # Storing facts
        if "my name is" in lower or "call me" in lower:
            match = re.search(r"(?:my name is|call me)\s+([a-zA-Z]+)", text, re.IGNORECASE)
            if match:
                name = match.group(1).capitalize()
                self._memory.remember("name", name)
                return SkillResult(success=True, message=f"Pleasure to meet you, {name}. I'll remember that.")

        if "i like" in lower or "i prefer" in lower or "my favorite" in lower:
            match = re.search(r"(?:i like|i prefer|my favorite)\s+(.+)", text, re.IGNORECASE)
            if match:
                fact = match.group(1).strip().rstrip(".")
                # Determine category
                if "favorite" in lower:
                    category = "favorite"
                    key = re.sub(r"my favorite\s+", "", fact, flags=re.IGNORECASE)
                    self._memory.remember("preference", (f"favorite_{key}", True))
                else:
                    self._memory.remember(f"likes", fact)
                return SkillResult(success=True, message=f"Noted, Boss. I'll remember you like {fact}.")

        # Generic remember
        match = re.search(r"(?:remember|note)\s+(?:that\s+)?(.+)", text, re.IGNORECASE)
        if match:
            fact = match.group(1).strip().rstrip(".")
            self._memory.remember("note", fact)
            return SkillResult(success=True, message=f"Noted, Boss: {fact}")

        return SkillResult(success=False, message="I can remember things about you or recall what I know, Boss.")
