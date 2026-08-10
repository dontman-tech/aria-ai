"""LLM brain for ARIA - powers natural conversation.

Supports multiple providers with graceful fallback:
  - DeepSeek (deepseek-chat / deepseek-reasoner, OpenAI-compatible API)
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

# Providers that use the OpenAI-compatible Chat Completions API
OPENAI_COMPATIBLE = {"deepseek", "openai", "local"}


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
        if provider == "deepseek":
            self._init_openai_compatible(
                provider_name="DeepSeek",
                default_url="https://api.deepseek.com/v1",
                env_var="DEEPSEEK_API_KEY",
            )
        elif provider == "openai":
            self._init_openai_compatible(
                provider_name="OpenAI",
                default_url=None,
                env_var="OPENAI_API_KEY",
            )
        elif provider == "anthropic":
            try:
                import anthropic

                api_key = self._resolve_key("ANTHROPIC_API_KEY")
                if not api_key:
                    logger.warning("No Anthropic API key set, brain will use echo fallback")
                    self.config.provider = "echo"
                    return
                self._client = anthropic.Anthropic(api_key=api_key)
                logger.info("Brain provider: Anthropic (%s)", self.config.model)
            except ImportError:
                logger.warning("anthropic package not installed, using echo fallback")
                self.config.provider = "echo"
        elif provider == "local":
            self._init_openai_compatible(
                provider_name="local",
                default_url="http://localhost:11434/v1",
                env_var="LOCAL_LLM_KEY",
                allow_no_key=True,
            )
        elif provider == "echo":
            logger.info("Brain provider: echo (offline test mode)")
        else:
            logger.warning("Unknown provider '%s', using echo fallback", provider)
            self.config.provider = "echo"

    def _init_openai_compatible(
        self,
        provider_name: str,
        default_url: str | None,
        env_var: str,
        allow_no_key: bool = False,
    ) -> None:
        """Initialize an OpenAI-compatible client (DeepSeek, OpenAI, local)."""
        try:
            from openai import OpenAI
        except ImportError:
            logger.warning("openai package not installed, using echo fallback")
            self.config.provider = "echo"
            return

        api_key = self._resolve_key(env_var)
        if not api_key:
            if allow_no_key:
                api_key = "not-needed"
            else:
                logger.warning("No %s set, brain will use echo fallback", env_var)
                self.config.provider = "echo"
                return

        base_url = self.config.base_url or default_url
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info("Brain provider: %s (%s)", provider_name, self.config.model)

    def _resolve_key(self, env_var: str) -> str:
        """Resolve API key: runtime-stored (dashboard) first, then env var."""
        if self.config.api_key:
            return self.config.api_key
        return os.environ.get(env_var, "")

    def reconfigure(self, api_key: str | None = None, model: str | None = None, provider: str | None = None) -> bool:
        """Reconfigure the brain at runtime (e.g. after dashboard API key entry).

        Returns True if the brain is now online.
        """
        if api_key is not None:
            self.config.api_key = api_key
        if model is not None:
            self.config.model = model
        if provider is not None:
            self.config.provider = provider
        self._client = None
        self._init_client()
        return self.available

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
            if provider in OPENAI_COMPATIBLE:
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
                "so I can't give you a full answer to that. Enter your DeepSeek API key "
                "in the dashboard settings and I'll be able to converse naturally. "
                "In the meantime, I can still run commands and skills for you."
            )
        return f"Understood, Boss. I've noted: \"{last_user}\". (Offline mode — connect a DeepSeek API key for full conversation.)"

    @property
    def available(self) -> bool:
        """True if a real LLM provider is connected (not echo)."""
        return self.config.provider != "echo"
