"""LLM brain for ARIA - powers natural conversation.

Supports multiple providers with graceful fallback:
  - OpenAI (GPT models)
  - Anthropic (Claude models)
  - Local (any OpenAI-compatible endpoint, e.g. Ollama, LM Studio)
  - Echo (offline fallback that echoes input, for testing)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from aria.core.config import BrainConfig, PersonalityConfig

logger = logging.getLogger(__name__)


class Brain:
    """The conversational brain that interfaces with an LLM."""

    def __init__(
        self,
        brain_config: BrainConfig,
        personality: PersonalityConfig,
    ) -> None:
        self.config = brain_config
        self.personality = personality
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        provider = self.config.provider
        if provider == "openai":
            try:
                from openai import OpenAI

                api_key = os.environ.get(self.config.api_key_env, "")
                if not api_key:
                    logger.warning("No %s set, brain will use echo fallback", self.config.api_key_env)
                    self.config.provider = "echo"
                    return
                self._client = OpenAI(api_key=api_key, base_url=self.config.base_url)
                logger.info("Brain provider: OpenAI (%s)", self.config.model)
            except ImportError:
                logger.warning("openai package not installed, using echo fallback")
                self.config.provider = "echo"
        elif provider == "anthropic":
            try:
                import anthropic

                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                if not api_key:
                    logger.warning("No ANTHROPIC_API_KEY set, brain will use echo fallback")
                    self.config.provider = "echo"
                    return
                self._client = anthropic.Anthropic(api_key=api_key)
                logger.info("Brain provider: Anthropic (%s)", self.config.model)
            except ImportError:
                logger.warning("anthropic package not installed, using echo fallback")
                self.config.provider = "echo"
        elif provider == "local":
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=os.environ.get("LOCAL_LLM_KEY", "not-needed"),
                    base_url=self.config.base_url or "http://localhost:11434/v1",
                )
                logger.info("Brain provider: local (%s)", self.config.base_url)
            except ImportError:
                logger.warning("openai package not installed, using echo fallback")
                self.config.provider = "echo"
        elif provider == "echo":
            logger.info("Brain provider: echo (offline test mode)")
        else:
            logger.warning("Unknown provider '%s', using echo fallback", provider)
            self.config.provider = "echo"

    def respond(self, messages: list[dict[str, str]]) -> str:
        """Generate a response given the conversation messages.

        Args:
            messages: List of {role, content} dicts including system prompt.

        Returns:
            The assistant's response text.
        """
        provider = self.config.provider
        if provider == "echo":
            return self._echo_response(messages)

        try:
            if provider == "openai" or provider == "local":
                return self._respond_openai(messages)
            elif provider == "anthropic":
                return self._respond_anthropic(messages)
        except Exception as e:
            logger.error("Brain error (%s): %s, falling back to echo", provider, e)
        return self._echo_response(messages)

    def _respond_openai(self, messages: list[dict[str, str]]) -> str:
        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return response.choices[0].message.content or ""

    def _respond_anthropic(self, messages: list[dict[str, str]]) -> str:
        # Anthropic separates system from messages
        system_text = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_text += m["content"] + "\n"
            else:
                chat_messages.append(m)
        response = self._client.messages.create(
            model=self.config.model,
            system=system_text.strip(),
            messages=chat_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return response.content[0].text if response.content else ""

    def _echo_response(self, messages: list[dict[str, str]]) -> str:
        """Offline fallback: produce a canned but contextual response."""
        last_user = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user = m["content"]
                break
        if not last_user:
            return "I'm here, Boss. How can I help?"

        lower = last_user.lower()
        if any(w in lower for w in ("hello", "hi", "hey", "morning")):
            return "Hello, Boss. ARIA online and ready. What can I do for you?"
        if "who are you" in lower or "what are you" in lower:
            return (
                "I'm ARIA — Advanced Reasoning and Intelligent Assistant. "
                "Think of me as your personal FRIDAY. I'm here to help you get things done."
            )
        if "time" in lower:
            from datetime import datetime

            return f"It's currently {datetime.now().strftime('%I:%M %p')}, Boss."
        if "thank" in lower:
            return "Always a pleasure, Boss."
        if lower.endswith("?"):
            return (
                "I'm currently running in offline mode without a connected language model, "
                "so I can't give you a full answer to that. Set the OPENAI_API_KEY environment "
                "variable and I'll be able to converse naturally. In the meantime, I can still "
                "run commands and skills for you."
            )
        return f"Understood, Boss. I've noted: \"{last_user}\". (Offline mode — connect an LLM for full conversation.)"

    @property
    def available(self) -> bool:
        """True if a real LLM provider is connected (not echo)."""
        return self.config.provider != "echo"
