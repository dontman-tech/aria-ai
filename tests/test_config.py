"""Tests for ARIA core configuration."""

import os
import tempfile
from pathlib import Path

from aria.core.config import Config, VoiceConfig, BrainConfig, PersonalityConfig


def test_default_config():
    """Config creates with sensible defaults."""
    cfg = Config()
    assert cfg.voice.wake_word == "aria"
    assert cfg.brain.provider == "openai"
    assert cfg.personality.name == "ARIA"
    assert cfg.log_level == "INFO"


def test_config_from_dict():
    """Config loads from a dictionary."""
    data = {
        "voice": {"wake_word": "friday", "voice_rate": 200},
        "brain": {"provider": "echo", "model": "test-model"},
        "personality": {"name": "JARVIS"},
        "log_level": "DEBUG",
    }
    cfg = Config.from_dict(data)
    assert cfg.voice.wake_word == "friday"
    assert cfg.voice.voice_rate == 200
    assert cfg.brain.provider == "echo"
    assert cfg.brain.model == "test-model"
    assert cfg.personality.name == "JARVIS"
    assert cfg.log_level == "DEBUG"


def test_config_from_yaml_file():
    """Config loads from a YAML file."""
    import yaml

    yaml_content = """
voice:
  wake_word: jarvis
  stt_engine: sphinx
brain:
  provider: echo
  temperature: 0.5
personality:
  name: KAREN
log_level: WARNING
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        path = f.name

    try:
        cfg = Config.from_file(path)
        assert cfg.voice.wake_word == "jarvis"
        assert cfg.voice.stt_engine == "sphinx"
        assert cfg.brain.provider == "echo"
        assert cfg.brain.temperature == 0.5
        assert cfg.personality.name == "KAREN"
        assert cfg.log_level == "WARNING"
    finally:
        os.unlink(path)


def test_config_defaults_preserved():
    """Unspecified keys keep their defaults."""
    cfg = Config.from_dict({"voice": {"wake_word": "test"}})
    assert cfg.voice.wake_word == "test"
    assert cfg.voice.voice_rate == 175  # default
    assert cfg.brain.provider == "openai"  # default
