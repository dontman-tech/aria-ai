"""Conversation memory for ARIA.

Stores short-term conversation history and a persistent long-term profile
of facts the user has shared, so ARIA can recall context across sessions.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Message:
    """A single conversation message."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
        )


class Memory:
    """Manages short-term history and long-term user profile."""

    def __init__(self, limit: int = 20, data_dir: str | Path | None = None) -> None:
        self.limit = limit
        self.history: list[Message] = []
        self.profile: dict[str, Any] = {
            "name": None,
            "preferences": {},
            "facts": [],
        }
        self.data_dir = Path(data_dir) if data_dir else None
        if self.data_dir:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def add(self, role: str, content: str) -> None:
        """Add a message to history, trimming to the limit."""
        self.history.append(Message(role=role, content=content))
        if len(self.history) > self.limit:
            self.history = self.history[-self.limit :]

    def remember(self, key: str, value: Any) -> None:
        """Store a fact about the user in the long-term profile."""
        if key == "name":
            self.profile["name"] = value
        elif key == "preference":
            pref_key, pref_val = value
            self.profile["preferences"][pref_key] = pref_val
        else:
            self.profile["facts"].append({"key": key, "value": value, "ts": time.time()})
        self._save()

    def recall(self, key: str) -> Any:
        """Recall a stored fact."""
        if key == "name":
            return self.profile.get("name")
        return self.profile["preferences"].get(key)

    def context_messages(self, system_prompt: str = "") -> list[dict[str, str]]:
        """Return history as a list of {role, content} dicts for an LLM."""
        msgs: list[dict[str, str]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        profile_context = self._profile_context()
        if profile_context:
            msgs.append({"role": "system", "content": profile_context})
        for m in self.history:
            msgs.append({"role": m.role, "content": m.content})
        return msgs

    def _profile_context(self) -> str:
        """Build a context string summarizing what ARIA knows about the user."""
        parts: list[str] = []
        if self.profile.get("name"):
            parts.append(f"The user's name is {self.profile['name']}.")
        prefs = self.profile.get("preferences", {})
        if prefs:
            pref_str = ", ".join(f"{k}: {v}" for k, v in prefs.items())
            parts.append(f"User preferences: {pref_str}.")
        facts = self.profile.get("facts", [])
        if facts:
            recent = facts[-5:]
            fact_str = "; ".join(f"{f['key']}={f['value']}" for f in recent)
            parts.append(f"Known facts: {fact_str}.")
        return " ".join(parts)

    def clear(self) -> None:
        """Clear short-term history (keeps long-term profile)."""
        self.history.clear()

    def reset_all(self) -> None:
        """Clear both short-term history and long-term profile."""
        self.history.clear()
        self.profile = {"name": None, "preferences": {}, "facts": []}
        self._save()

    def _save(self) -> None:
        if not self.data_dir:
            return
        path = self.data_dir / "memory.json"
        data = {
            "history": [m.to_dict() for m in self.history],
            "profile": self.profile,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        path = self.data_dir / "memory.json"
        if not path.exists():
            return
        try:
            with open(path) as f:
                data = json.load(f)
            self.history = [Message.from_dict(m) for m in data.get("history", [])]
            self.profile = data.get("profile", self.profile)
        except (json.JSONDecodeError, KeyError):
            pass
