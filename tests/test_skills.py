"""Tests for ARIA skills."""

import pytest

from aria.skills.router import SkillRouter
from aria.skills.calculator import CalculatorSkill
from aria.skills.time_date import TimeDateSkill
from aria.skills.joke import JokeSkill
from aria.skills.memory_skill import MemorySkill
from aria.core.memory import Memory


class TestCalculatorSkill:
    def setup_method(self):
        self.skill = CalculatorSkill()

    def test_addition(self):
        result = self.skill.execute("calculate 5 plus 3")
        assert result.success
        assert "8" in result.message

    def test_multiplication(self):
        result = self.skill.execute("what is 15 times 4")
        assert result.success
        assert "60" in result.message

    def test_division(self):
        result = self.skill.execute("calculate 100 divided by 4")
        assert result.success
        assert "25" in result.message

    def test_subtraction(self):
        result = self.skill.execute("calculate 50 minus 17")
        assert result.success
        assert "33" in result.message

    def test_power(self):
        result = self.skill.execute("calculate 2 to the power of 10")
        assert result.success
        assert "1,024" in result.message

    def test_square_root(self):
        result = self.skill.execute("what is the square root of 144")
        assert result.success
        assert "12" in result.message

    def test_factorial(self):
        result = self.skill.execute("calculate factorial of 5")
        assert result.success
        assert "120" in result.message

    def test_float_result(self):
        result = self.skill.execute("calculate 7 divided by 2")
        assert result.success
        assert "3.5" in result.message

    def test_matches(self):
        assert self.skill.matches("calculate 2 plus 2")
        assert self.skill.matches("what is 5 times 3")
        assert not self.skill.matches("hello there")


class TestTimeDateSkill:
    def setup_method(self):
        self.skill = TimeDateSkill()

    def test_time(self):
        result = self.skill.execute("what time is it")
        assert result.success
        assert "Boss" in result.message

    def test_date(self):
        result = self.skill.execute("what's the date today")
        assert result.success
        assert "Today is" in result.message

    def test_day(self):
        result = self.skill.execute("what day is it")
        assert result.success
        assert "It's" in result.message or "Today is" in result.message


class TestJokeSkill:
    def setup_method(self):
        self.skill = JokeSkill()

    def test_tells_joke(self):
        result = self.skill.execute("tell me a joke")
        assert result.success
        assert len(result.message) > 10


class TestMemorySkill:
    def setup_method(self):
        self.memory = Memory(limit=10)
        self.skill = MemorySkill(memory=self.memory)

    def test_remember_name(self):
        result = self.skill.execute("my name is Tony")
        assert result.success
        assert "Tony" in result.message
        assert self.memory.recall("name") == "Tony"

    def test_recall_name(self):
        self.memory.remember("name", "Tony")
        result = self.skill.execute("what's my name")
        assert result.success
        assert "Tony" in result.message

    def test_no_name_set(self):
        result = self.skill.execute("what's my name")
        assert result.success
        assert "don't know" in result.message.lower() or "not" in result.message.lower()


class TestSkillRouter:
    def test_register_all(self):
        router = SkillRouter(memory=Memory(limit=10))
        router.register_all()
        skills = router.list_skills()
        assert "calculator" in skills
        assert "time_date" in skills
        assert "joke" in skills
        assert "memory" in skills
        assert len(skills) >= 8

    def test_routes_to_calculator(self):
        router = SkillRouter(memory=Memory(limit=10))
        router.register_all()
        result = router.execute("calculate 2 plus 2")
        assert result is not None
        assert result.success
        assert "4" in result.message

    def test_routes_to_joke(self):
        router = SkillRouter(memory=Memory(limit=10))
        router.register_all()
        result = router.execute("tell me a joke")
        assert result is not None
        assert result.success

    def test_no_match_returns_none(self):
        router = SkillRouter(memory=Memory(limit=10))
        router.register_all()
        result = router.execute("xyzzy flibber")
        # May or may not match depending on fuzzy keywords, but general nonsense shouldn't
        # The wiki skill might try to match "what is" patterns, so test with truly nonsensical input
        result2 = router.execute("zzzzqqqxxx")
        assert result2 is None
