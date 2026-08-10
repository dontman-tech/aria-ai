"""File operations skill - list, read, find files."""

from __future__ import annotations

import os
import re
from pathlib import Path

from aria.skills.base import Skill, SkillResult


class FileOpsSkill(Skill):
    name = "files"
    description = "List, search, and read files on the system"
    patterns = [
        r"\b(list|show) (files|directory|folder)\b",
        r"\bfind files?\b",
        r"\bread file\b",
        r"\b(file )?contents? of\b",
        r"\bcreate (a )?(file|folder|directory)\b",
    ]
    keywords = ["list files", "find files", "read file", "create file", "create folder"]

    def execute(self, text: str) -> SkillResult:
        lower = text.lower()

        if "create" in lower and ("folder" in lower or "directory" in lower):
            return self._create_folder(text)
        if "create" in lower and "file" in lower:
            return self._create_file(text)
        if "find" in lower or "search" in lower:
            return self._find_files(text)
        if "read" in lower or "contents" in lower or "content of" in lower:
            return self._read_file(text)
        if "list" in lower or "show" in lower:
            return self._list_dir(text)

        return SkillResult(success=False, message="I can list, find, read, or create files, Boss. What do you need?")

    def _extract_path(self, text: str) -> Path:
        """Extract a path from the text, defaulting to cwd."""
        # Look for quoted path or path-like string
        match = re.search(r'["\']([^"\']+)["\']', text)
        if match:
            return Path(match.group(1)).expanduser()
        match = re.search(r'(?:in|at|from|of)\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|\?|\.)', text)
        if match:
            p = match.group(1).strip()
            if "/" in p or "\\" in p or p.startswith("~"):
                return Path(p).expanduser()
        return Path.cwd()

    def _list_dir(self, text: str) -> SkillResult:
        path = self._extract_path(text)
        if not path.exists() or not path.is_dir():
            return SkillResult(success=False, message=f"Directory {path} doesn't exist, Boss.")
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        if not entries:
            return SkillResult(success=True, message=f"{path} is empty, Boss.")
        lines = []
        for e in entries[:30]:
            prefix = "📁 " if e.is_dir() else "📄 "
            lines.append(f"{prefix}{e.name}")
        msg = f"Contents of {path}:\n" + "\n".join(lines)
        if len(entries) > 30:
            msg += f"\n...and {len(entries) - 30} more"
        return SkillResult(success=True, message=msg, should_speak=False)

    def _find_files(self, text: str) -> SkillResult:
        # Extract search pattern
        match = re.search(r'(?:named|called|matching|containing)\s+["\']?([^"\']+?)["\']?(?:\s|$|\?)', text)
        pattern = match.group(1) if match else "*"
        path = self._extract_path(text)

        results = list(path.rglob(pattern))[:20]
        if not results:
            return SkillResult(success=True, message=f"No files matching '{pattern}' in {path}, Boss.")
        lines = [str(r.relative_to(path) if r.is_relative_to(path) else r) for r in results]
        msg = f"Found {len(results)} file(s) matching '{pattern}':\n" + "\n".join(lines)
        return SkillResult(success=True, message=msg, should_speak=False)

    def _read_file(self, text: str) -> SkillResult:
        path = self._extract_path(text)
        if not path.exists():
            return SkillResult(success=False, message=f"File {path} doesn't exist, Boss.")
        if not path.is_file():
            return SkillResult(success=False, message=f"{path} is not a file, Boss.")
        try:
            content = path.read_text(errors="replace")
            if len(content) > 2000:
                content = content[:2000] + "\n...[truncated]"
            return SkillResult(success=True, message=f"Contents of {path}:\n\n{content}", should_speak=False)
        except Exception as e:
            return SkillResult(success=False, message=f"Couldn't read {path}: {e}")

    def _create_folder(self, text: str) -> SkillResult:
        match = re.search(r'(?:named|called)\s+["\']?([^"\']+?)["\']?(?:\s|$|\?)', text)
        if not match:
            return SkillResult(success=False, message="What should I name the folder, Boss?")
        name = match.group(1).strip()
        path = Path.cwd() / name
        try:
            path.mkdir(parents=True, exist_ok=True)
            return SkillResult(success=True, message=f"Created folder {path}, Boss.")
        except Exception as e:
            return SkillResult(success=False, message=f"Couldn't create folder: {e}")

    def _create_file(self, text: str) -> SkillResult:
        match = re.search(r'(?:named|called)\s+["\']?([^"\']+?)["\']?(?:\s|$|\?)', text)
        if not match:
            return SkillResult(success=False, message="What should I name the file, Boss?")
        name = match.group(1).strip()
        path = Path.cwd() / name
        try:
            path.touch()
            return SkillResult(success=True, message=f"Created file {path}, Boss.")
        except Exception as e:
            return SkillResult(success=False, message=f"Couldn't create file: {e}")
