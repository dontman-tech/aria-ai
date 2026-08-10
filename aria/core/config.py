"""ARIA configuration system.

Loads settings from a YAML config file with environment variable overrides
and sensible defaults so ARIA works out-of-the-box.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "config.yaml"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@dataclass
class VoiceConfig:
    """Speech recognition and synthesis settings."""

    enabled: bool = True
    # Speech-to-text
    stt_engine: str = "google"  # google, whisper, sphinx
    whisper_model: str = "base"
    # Text-to-speech
    tts_engine: str = "pyttsx3"  # pyttsx3, gtts
    voice_rate: int = 175  # words per minute
    voice_id: str | None = None
    voice_volume: float = 1.0
    # Wake word
    wake_word: str = "aria"
    wake_word_enabled: bool = True
    # Audio
    energy_threshold: int = 300
    pause_threshold: float = 0.8
    dynamic_energy: bool = True


@dataclass
class BrainConfig:
    """LLM / conversation brain settings."""

    provider: str = "openai"  # openai, anthropic, local, echo
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 1024
    system_prompt: str = ""
    memory_limit: int = 20  # number of past exchanges to keep in context


@dataclass
class PersonalityConfig:
    """ARIA's personality and identity."""

    name: str = "ARIA"
    creator: str = "Boss"
    persona: str = (
        "You are ARIA (Advanced Reasoning and Intelligent Assistant), a highly capable "
        "AI assistant inspired by FRIDAY from Iron Man. You are witty, efficient, and "
        "professional with a dry sense of humor. You address the user as 'Boss'. "
        "You are proactive, concise, and get things done. You speak naturally as if "
        "having a conversation, not as a robotic assistant."
    )


@dataclass
class Config:
    """Top-level configuration."""

    voice: VoiceConfig = field(default_factory=VoiceConfig)
    brain: BrainConfig = field(default_factory=BrainConfig)
    personality: PersonalityConfig = field(default_factory=PersonalityConfig)
    log_level: str = "INFO"
    data_dir: str = str(DATA_DIR)

    @classmethod
    def from_file(cls, path: str | Path | None = None) -> "Config":
        """Load configuration from a YAML file, falling back to defaults."""
        config_path = Path(path) if path else DEFAULT_CONFIG_PATH
        data: dict[str, Any] = {}
        if config_path.exists() and yaml is not None:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Build a Config from a dictionary."""
        cfg = cls()
        voice_data = data.get("voice", {})
        if voice_data:
            for k, v in voice_data.items():
                if hasattr(cfg.voice, k):
                    setattr(cfg.voice, k, v)
        brain_data = data.get("brain", {})
        if brain_data:
            for k, v in brain_data.items():
                if hasattr(cfg.brain, k):
                    setattr(cfg.brain, k, v)
        pers_data = data.get("personality", {})
        if pers_data:
            for k, v in pers_data.items():
                if hasattr(cfg.personality, k):
                    setattr(cfg.personality, k, v)
        for k in ("log_level", "data_dir"):
            if k in data:
                setattr(cfg, k, data[k])
        return cfg


def load_config(path: str | Path | None = None) -> Config:
    """Convenience helper to load config."""
    return Config.from_file(path)
