"""Base classes for ARIA skills."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SkillResult:
    """The result of running a skill."""

    success: bool
    message: str
    data: dict = field(default_factory=dict)
    should_speak: bool = True

    def __str__(self) -> str:
        return self.message


class Skill(ABC):
    """Base class for all ARIA skills."""

    name: str = "base"
    description: str = ""
    # Regex patterns that trigger this skill (matched against lowercased input)
    patterns: list[str] = []
    # Keywords for fuzzy matching
    keywords: list[str] = []

    def __init__(self) -> None:
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def matches(self, text: str) -> bool:
        """Check if this skill matches the user input."""
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                return True
        text_lower = text.lower()
        for kw in self.keywords:
            if kw in text_lower:
                return True
        return False

    @abstractmethod
    def execute(self, text: str) -> SkillResult:
        """Execute the skill given the user input text."""

    def confidence(self, text: str) -> float:
        """Return a confidence score 0-1 for how well this matches."""
        best = 0.0
        for pattern in self._compiled_patterns:
            m = pattern.search(text)
            if m:
                best = max(best, 0.9)
        text_lower = text.lower()
        for kw in self.keywords:
            if kw in text_lower:
                best = max(best, 0.6)
        return best

    def __repr__(self) -> str:
        return f"<Skill: {self.name}>"
