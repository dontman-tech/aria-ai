"""Tests for ARIA brain (LLM) in echo mode."""

from aria.core.config import BrainConfig, PersonalityConfig
from aria.brain.llm import Brain


class TestBrainEcho:
    def setup_method(self):
        self.config = BrainConfig(provider="echo")
        self.personality = PersonalityConfig()
        self.brain = Brain(self.config, self.personality)

    def test_echo_mode_no_api_key(self):
        """Brain defaults to echo when no API key is available."""
        assert not self.brain.available

    def test_echo_response_greeting(self):
        result = self.brain.respond([{"role": "user", "content": "hello"}])
        assert "Boss" in result
        assert "ready" in result.lower() or "hello" in result.lower()

    def test_echo_response_identity(self):
        result = self.brain.respond([{"role": "user", "content": "who are you"}])
        assert "ARIA" in result
        assert "FRIDAY" in result

    def test_echo_response_thanks(self):
        result = self.brain.respond([{"role": "user", "content": "thank you"}])
        assert "pleasure" in result.lower()

    def test_echo_response_question(self):
        result = self.brain.respond([{"role": "user", "content": "what is the meaning of life?"}])
        assert "offline" in result.lower() or "Boss" in result

    def test_echo_response_empty(self):
        result = self.brain.respond([])
        assert "Boss" in result
