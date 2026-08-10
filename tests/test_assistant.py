"""Integration tests for the full ARIA assistant."""

import pytest

from aria.core.config import Config, BrainConfig
from aria.core.assistant import ARIA


@pytest.fixture
def aria():
    """Create an ARIA instance in echo/text-only mode for testing."""
    config = Config()
    config.voice.enabled = False  # No audio in test env
    config.brain.provider = "echo"
    config.brain.api_key_env = "NONEXISTENT_KEY"  # Force echo mode
    return ARIA(config)


class TestARIAAssistant:
    def test_initialization(self, aria):
        """ARIA initializes without errors."""
        assert aria.config.personality.name == "ARIA"
        assert len(aria.router.list_skills()) >= 8

    def test_process_greeting(self, aria):
        """ARIA responds to greetings."""
        response = aria.process("hello")
        assert "Boss" in response
        assert len(response) > 5

    def test_process_calculator(self, aria):
        """ARIA routes math to calculator skill."""
        response = aria.process("calculate 25 times 4")
        assert "100" in response

    def test_process_time(self, aria):
        """ARIA tells the time."""
        response = aria.process("what time is it")
        assert "Boss" in response

    def test_process_joke(self, aria):
        """ARIA tells jokes."""
        response = aria.process("tell me a joke")
        assert len(response) > 10

    def test_process_help(self, aria):
        """ARIA provides help."""
        response = aria.process("help")
        assert "ARIA" in response
        assert "Skills" in response

    def test_process_exit(self, aria):
        """ARIA handles exit command."""
        response = aria.process("exit")
        assert "Goodbye" in response or "signing off" in response.lower()

    def test_process_memory(self, aria):
        """ARIA remembers the user's name."""
        aria.process("my name is Tony")
        response = aria.process("what's my name")
        assert "Tony" in response

    def test_process_conversation(self, aria):
        """ARIA can hold a conversation in echo mode."""
        response = aria.process("who are you")
        assert "ARIA" in response
        assert "FRIDAY" in response

    def test_process_unknown_question(self, aria):
        """ARIA handles unknown questions gracefully."""
        response = aria.process("what is the meaning of life?")
        assert "Boss" in response

    def test_process_empty(self, aria):
        """ARIA handles empty input."""
        response = aria.process("")
        assert "Boss" in response or "catch" in response.lower()

    def test_run_single(self, aria):
        """The run_single method works."""
        response = aria.run_single("calculate 10 plus 10")
        assert "20" in response

    def test_system_prompt(self, aria):
        """System prompt includes persona and skills."""
        prompt = aria.system_prompt
        assert "ARIA" in prompt
        assert "calculator" in prompt
        assert "Boss" in prompt

    def test_clear_memory(self, aria):
        """Clear command resets conversation."""
        aria.process("hello")
        assert len(aria.memory.history) > 0
        aria.process("clear")
        assert len(aria.memory.history) == 1  # just the "cleared" response

    def test_skill_routing_over_brain(self, aria):
        """Skills take priority over the LLM brain."""
        response = aria.process("calculate 6 times 7")
        assert "42" in response
        # The response should come from the calculator, not the echo brain
        assert "offline" not in response.lower()
