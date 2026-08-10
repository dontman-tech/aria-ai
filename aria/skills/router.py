"""Skill router - matches user commands to skills and executes them."""

from __future__ import annotations

import logging
from typing import Optional

from aria.skills.base import Skill, SkillResult

logger = logging.getLogger(__name__)


class SkillRouter:
    """Routes user input to the best-matching skill."""

    def __init__(self, memory=None) -> None:
        self.skills: list[Skill] = []
        self._memory = memory

    def register(self, skill: Skill) -> None:
        """Register a skill with the router."""
        self.skills.append(skill)
        logger.debug("Registered skill: %s", skill.name)

    def register_all(self) -> None:
        """Register all built-in skills."""
        # Import here to avoid circular imports during module load
        from aria.skills.system_control import SystemControlSkill
        from aria.skills.time_date import TimeDateSkill
        from aria.skills.calculator import CalculatorSkill
        from aria.skills.web_search import WebSearchSkill
        from aria.skills.weather import WeatherSkill
        from aria.skills.files import FileOpsSkill
        from aria.skills.apps import AppLaunchSkill
        from aria.skills.wiki import WikiSkill
        from aria.skills.memory_skill import MemorySkill
        from aria.skills.joke import JokeSkill
        from aria.skills.phone_control import PhoneControlSkill

        for skill_cls in [
            PhoneControlSkill,
            SystemControlSkill,
            TimeDateSkill,
            CalculatorSkill,
            WebSearchSkill,
            WeatherSkill,
            FileOpsSkill,
            AppLaunchSkill,
            WikiSkill,
            JokeSkill,
        ]:
            try:
                self.register(skill_cls())
            except Exception as e:
                logger.warning("Failed to register %s: %s", skill_cls.__name__, e)

        # MemorySkill needs the memory instance injected
        try:
            mem_skill = MemorySkill(memory=self._memory)
            self.register(mem_skill)
        except Exception as e:
            logger.warning("Failed to register MemorySkill: %s", e)

    def find_best(self, text: str) -> Optional[Skill]:
        """Find the best-matching skill for the input."""
        best_skill = None
        best_score = 0.0
        for skill in self.skills:
            if skill.matches(text):
                score = skill.confidence(text)
                if score > best_score:
                    best_score = score
                    best_skill = skill
        return best_skill

    def execute(self, text: str) -> Optional[SkillResult]:
        """Find and execute the best skill for the input.

        Returns None if no skill matches.
        """
        skill = self.find_best(text)
        if skill is None:
            return None
        try:
            logger.debug("Executing skill %s for: %s", skill.name, text)
            return skill.execute(text)
        except Exception as e:
            logger.error("Skill %s error: %s", skill.name, e)
            return SkillResult(
                success=False,
                message=f"I ran into a problem with that: {e}",
            )

    def list_skills(self) -> list[str]:
        """Return a list of registered skill names."""
        return [s.name for s in self.skills]
