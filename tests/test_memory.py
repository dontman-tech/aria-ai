"""Tests for ARIA memory system."""

import tempfile
from pathlib import Path

from aria.core.memory import Memory, Message


def test_memory_add_and_retrieve():
    """Messages are stored in history."""
    mem = Memory(limit=10)
    mem.add("user", "hello")
    mem.add("assistant", "hi there")
    assert len(mem.history) == 2
    assert mem.history[0].role == "user"
    assert mem.history[0].content == "hello"
    assert mem.history[1].content == "hi there"


def test_memory_limit_trims():
    """History is trimmed to the configured limit."""
    mem = Memory(limit=3)
    for i in range(5):
        mem.add("user", f"msg {i}")
    assert len(mem.history) == 3
    assert mem.history[0].content == "msg 2"
    assert mem.history[-1].content == "msg 4"


def test_memory_remember_name():
    """Long-term profile stores the user's name."""
    mem = Memory(limit=10)
    mem.remember("name", "Tony")
    assert mem.recall("name") == "Tony"


def test_memory_remember_preference():
    """Long-term profile stores preferences."""
    mem = Memory(limit=10)
    mem.remember("preference", ("theme", "dark"))
    assert mem.recall("theme") == "dark"


def test_memory_context_messages():
    """Context messages include system prompt and profile."""
    mem = Memory(limit=10)
    mem.add("user", "hello")
    msgs = mem.context_messages("You are ARIA.")
    assert msgs[0] == {"role": "system", "content": "You are ARIA."}
    assert msgs[-1] == {"role": "user", "content": "hello"}


def test_memory_profile_in_context():
    """Profile info appears in context."""
    mem = Memory(limit=10)
    mem.remember("name", "Tony")
    msgs = mem.context_messages("system")
    # Second message should contain profile context
    profile_msg = msgs[1]["content"]
    assert "Tony" in profile_msg


def test_memory_clear():
    """Clear removes history but keeps profile."""
    mem = Memory(limit=10)
    mem.add("user", "hello")
    mem.remember("name", "Tony")
    mem.clear()
    assert len(mem.history) == 0
    assert mem.recall("name") == "Tony"


def test_memory_reset_all():
    """Reset clears everything."""
    mem = Memory(limit=10)
    mem.add("user", "hello")
    mem.remember("name", "Tony")
    mem.reset_all()
    assert len(mem.history) == 0
    assert mem.recall("name") is None


def test_memory_persistence():
    """Memory saves and loads from disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mem1 = Memory(limit=10, data_dir=tmpdir)
        mem1.add("user", "persist this")
        mem1.remember("name", "Tony")
        mem1._save()

        mem2 = Memory(limit=10, data_dir=tmpdir)
        assert len(mem2.history) == 1
        assert mem2.history[0].content == "persist this"
        assert mem2.recall("name") == "Tony"


def test_message_to_dict():
    """Message serializes to dict."""
    m = Message(role="user", content="hello", timestamp=12345)
    d = m.to_dict()
    assert d == {"role": "user", "content": "hello", "timestamp": 12345}


def test_message_from_dict():
    """Message deserializes from dict."""
    d = {"role": "assistant", "content": "hi", "timestamp": 99999}
    m = Message.from_dict(d)
    assert m.role == "assistant"
    assert m.content == "hi"
    assert m.timestamp == 99999
