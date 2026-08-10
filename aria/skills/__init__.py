"""Skills package for ARIA - modular capabilities like FRIDAY's systems.

Each skill is a self-contained command handler. Skills are registered
with the SkillRouter which matches user commands to the right skill.
"""

from aria.skills.router import SkillRouter
from aria.skills.base import Skill, SkillResult

__all__ = ["Skill", "SkillResult", "SkillRouter"]
