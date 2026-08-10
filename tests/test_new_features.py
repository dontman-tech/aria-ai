"""Tests for new features: kill switch, runtime API key, phone control, file ops."""

import os
import tempfile
from pathlib import Path

import pytest

from aria.core.config import Config, BrainConfig
from aria.core.assistant import ARIA
from aria.skills.phone_control import PhoneControlSkill
from aria.skills.files import FileOpsSkill
from aria.skills.base import SkillResult


@pytest.fixture
def aria(tmp_path):
    """ARIA instance with echo brain and temp data dir."""
    config = Config()
    config.brain.provider = "echo"
    config.voice.enabled = False
    config.data_dir = str(tmp_path)
    return ARIA(config)


@pytest.fixture
def file_skill():
    return FileOpsSkill()


# --- Kill Switch ---


class TestKillSwitch:
    def test_kill_sets_flag(self, aria):
        assert not aria.killed
        msg = aria.kill()
        assert aria.killed
        assert "Kill switch" in msg

    def test_killed_aria_refuses_commands(self, aria):
        aria.kill()
        response = aria.process("calculate 2 plus 2")
        assert "shut down" in response.lower()

    def test_kill_via_text_command(self, aria):
        response = aria.process("shut down")
        assert aria.killed
        assert "Kill switch" in response or "shutting down" in response.lower()

    def test_get_config_status(self, aria):
        status = aria.get_config_status()
        assert "provider" in status
        assert "brain_online" in status
        assert "killed" in status
        assert status["killed"] is False


# --- Runtime API Key ---


class TestRuntimeApiKey:
    def test_save_runtime_key(self, tmp_path):
        config = Config()
        config.data_dir = str(tmp_path)
        config.save_runtime_key("deepseek", "sk-test-123")
        assert config.brain.api_key == "sk-test-123"
        # Verify persisted to secrets.json
        secrets_file = tmp_path / "secrets.json"
        assert secrets_file.exists()
        import json

        saved = json.loads(secrets_file.read_text())
        assert saved["deepseek"] == "sk-test-123"

    def test_get_api_key_runtime_first(self, tmp_path):
        config = Config()
        config.data_dir = str(tmp_path)
        config.brain.api_key = "runtime-key"
        os.environ["DEEPSEEK_API_KEY"] = "env-key"
        try:
            assert config.get_api_key() == "runtime-key"
        finally:
            del os.environ["DEEPSEEK_API_KEY"]

    def test_set_api_key_method(self, aria):
        result = aria.set_api_key("deepseek", "sk-test-key", "deepseek-chat")
        # Will be offline because openai package may not be installed or key is fake
        assert "provider" in result
        assert "model" in result


# --- Phone Control ---


class TestPhoneControl:
    def test_skill_matches_wifi(self):
        skill = PhoneControlSkill()
        assert skill.matches("turn on wifi")

    def test_skill_matches_bluetooth(self):
        skill = PhoneControlSkill()
        assert skill.matches("turn off bluetooth")

    def test_skill_matches_brightness(self):
        skill = PhoneControlSkill()
        assert skill.matches("set phone brightness to 50 percent")

    def test_skill_matches_flashlight(self):
        skill = PhoneControlSkill()
        assert skill.matches("turn on flashlight")

    def test_skill_matches_battery(self):
        skill = PhoneControlSkill()
        assert skill.matches("phone battery")

    def test_skill_matches_open_app(self):
        skill = PhoneControlSkill()
        assert skill.matches("open app com.twitter.android")

    def test_skill_matches_open_url(self):
        skill = PhoneControlSkill()
        assert skill.matches("open https://example.com on my phone")

    def test_skill_matches_device_info(self):
        skill = PhoneControlSkill()
        assert skill.matches("phone device info")

    def test_no_bridge_returns_message(self):
        skill = PhoneControlSkill()
        skill._bridge_url = None  # force no bridge
        result = skill.execute("turn on wifi")
        assert result.success is False
        assert "companion app" in result.message.lower()

    def test_battery_fallback_psutil(self):
        skill = PhoneControlSkill()
        skill._bridge_url = None
        result = skill.execute("phone battery")
        # psutil may or may not be available
        assert isinstance(result, SkillResult)


# --- Enhanced File Operations ---


class TestFileOps:
    def test_move_file(self, file_skill, tmp_path):
        src = tmp_path / "a.txt"
        src.write_text("hello")
        dst = tmp_path / "subdir" / "b.txt"
        result = file_skill.execute(f"move file {src} to {dst}")
        assert result.success
        assert not src.exists()
        assert dst.exists()

    def test_copy_file(self, file_skill, tmp_path):
        src = tmp_path / "original.txt"
        src.write_text("data")
        dst = tmp_path / "copy.txt"
        result = file_skill.execute(f"copy file {src} to {dst}")
        assert result.success
        assert src.exists()
        assert dst.exists()

    def test_delete_file(self, file_skill, tmp_path):
        f = tmp_path / "trash.txt"
        f.write_text("delete me")
        result = file_skill.execute(f"delete file {f}")
        assert result.success
        assert not f.exists()

    def test_rename_file(self, file_skill, tmp_path):
        old = tmp_path / "old_name.txt"
        old.write_text("content")
        result = file_skill.execute(f"rename {old} to new_name.txt")
        assert result.success
        assert (tmp_path / "new_name.txt").exists()

    def test_edit_write_file(self, file_skill, tmp_path):
        target = tmp_path / "notes.txt"
        result = file_skill.execute(f"write 'hello world' to {target}")
        assert result.success
        assert target.read_text() == "hello world"

    def test_organize_files(self, file_skill, tmp_path):
        (tmp_path / "a.txt").write_text("x")
        (tmp_path / "b.jpg").write_text("x")
        (tmp_path / "c.txt").write_text("x")
        result = file_skill.execute(f"organize files in {tmp_path}")
        assert result.success
        assert (tmp_path / "TXT_FILES" / "a.txt").exists()
        assert (tmp_path / "TXT_FILES" / "c.txt").exists()
        assert (tmp_path / "JPG_FILES" / "b.jpg").exists()

    def test_skill_matches_move(self, file_skill):
        assert file_skill.matches("move file report.txt to archive")

    def test_skill_matches_delete(self, file_skill):
        assert file_skill.matches("delete file trash.txt")

    def test_skill_matches_edit(self, file_skill):
        assert file_skill.matches("edit file notes.txt")

    def test_skill_matches_organize(self, file_skill):
        assert file_skill.matches("organize files in downloads")
