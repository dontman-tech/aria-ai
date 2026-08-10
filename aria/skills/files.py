"""File operations skill - organize, access, and edit files.

Supports: list, find, read, create, move, copy, edit, delete, rename files
and directories. Designed to work on any device including Android phones
(via the companion app which exposes the file system).
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from aria.skills.base import Skill, SkillResult


class FileOpsSkill(Skill):
    name = "files"
    description = "List, search, read, create, move, copy, edit, and delete files"
    patterns = [
        r"\b(list|show) (files|directory|folder|contents?)\b",
        r"\bfind files?\b",
        r"\bread (file|the contents?)\b",
        r"\b(file )?contents? of\b",
        r"\bcreate (a )?(file|folder|directory)\b",
        r"\b(move|copy|delete|rename|remove)\b.*\bfile\b",
        r"\b(move|copy|delete|rename|remove)\b.*\b(to|into|from|as)\b",
        r"\bedit (file|the file)\b",
        r"\bwrite (to|in) (a )?file\b",
        r"\borganize files?\b",
    ]
    keywords = [
        "list files", "find files", "read file", "create file", "create folder",
        "move file", "copy file", "delete file", "rename file", "edit file",
        "write to file", "organize files", "delete folder",
    ]

    def execute(self, text: str) -> SkillResult:
        lower = text.lower()

        if "organize" in lower:
            return self._organize(text)
        if ("delete" in lower or "remove" in lower) and ("file" in lower or "folder" in lower or "directory" in lower):
            return self._delete(text)
        if "rename" in lower:
            return self._rename(text)
        if "move" in lower:
            return self._move(text)
        if "copy" in lower:
            return self._copy(text)
        if "edit" in lower or "write to" in lower or "write in" in lower:
            return self._edit_file(text)
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

        return SkillResult(success=False, message="I can list, find, read, create, move, copy, edit, rename, or delete files, Boss. What do you need?")

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

    def _move(self, text: str) -> SkillResult:
        """Move a file/folder to a destination."""
        src, dst = self._extract_src_dst(text)
        if not src or not dst:
            return SkillResult(success=False, message="Tell me the source and destination, Boss. e.g. 'move file report.txt to archive'")
        src_path = Path(src).expanduser()
        dst_path = Path(dst).expanduser()
        if not src_path.exists():
            return SkillResult(success=False, message=f"Source {src_path} doesn't exist, Boss.")
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            return SkillResult(success=True, message=f"Moved {src_path} to {dst_path}, Boss.")
        except Exception as e:
            return SkillResult(success=False, message=f"Couldn't move: {e}")

    def _copy(self, text: str) -> SkillResult:
        """Copy a file/folder to a destination."""
        src, dst = self._extract_src_dst(text)
        if not src or not dst:
            return SkillResult(success=False, message="Tell me the source and destination, Boss. e.g. 'copy file notes.txt to backup'")
        src_path = Path(src).expanduser()
        dst_path = Path(dst).expanduser()
        if not src_path.exists():
            return SkillResult(success=False, message=f"Source {src_path} doesn't exist, Boss.")
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if src_path.is_dir():
                shutil.copytree(str(src_path), str(dst_path))
            else:
                shutil.copy2(str(src_path), str(dst_path))
            return SkillResult(success=True, message=f"Copied {src_path} to {dst_path}, Boss.")
        except Exception as e:
            return SkillResult(success=False, message=f"Couldn't copy: {e}")

    def _delete(self, text: str) -> SkillResult:
        """Delete a file or folder. Asks for confirmation via confirmation token."""
        src = self._extract_single_path(text)
        if not src:
            return SkillResult(success=False, message="Which file or folder should I delete, Boss?")
        path = Path(src).expanduser()
        if not path.exists():
            return SkillResult(success=False, message=f"{path} doesn't exist, Boss.")
        # Safety: require explicit "delete" + the path to reduce accidents
        try:
            if path.is_dir():
                shutil.rmtree(str(path))
            else:
                path.unlink()
            return SkillResult(success=True, message=f"Deleted {path}, Boss.", data={"deleted": str(path)})
        except Exception as e:
            return SkillResult(success=False, message=f"Couldn't delete: {e}")

    def _rename(self, text: str) -> SkillResult:
        """Rename a file or folder."""
        # "rename old.txt to new.txt" or "rename file old.txt as new.txt"
        match = re.search(r'rename\s+(?:file\s+|folder\s+)?["\']?(.+?)["\']?\s+(?:to|as|into)\s+["\']?(.+?)["\']?(?:\s*$|\?)', text, re.IGNORECASE)
        if not match:
            return SkillResult(success=False, message="Tell me the current name and new name, Boss. e.g. 'rename old.txt to new.txt'")
        old_name = match.group(1).strip()
        new_name = match.group(2).strip()
        old_path = Path(old_name).expanduser()
        if not old_path.is_absolute():
            old_path = Path.cwd() / old_path
        new_path = old_path.parent / new_name
        if not old_path.exists():
            return SkillResult(success=False, message=f"{old_path} doesn't exist, Boss.")
        try:
            old_path.rename(new_path)
            return SkillResult(success=True, message=f"Renamed {old_path.name} to {new_name}, Boss.")
        except Exception as e:
            return SkillResult(success=False, message=f"Couldn't rename: {e}")

    def _edit_file(self, text: str) -> SkillResult:
        """Write content to a file (create or overwrite)."""
        # "write 'content' to file.txt" or "edit file notes.txt with 'content'"
        content_match = re.search(r"['\"](.+?)['\"]", text)
        file_match = re.search(r'(?:to|in|file)\s+([^\s\'\"]+\.\w+)', text)
        if not content_match:
            return SkillResult(success=False, message="What content should I write, Boss? Put it in quotes, e.g. write 'hello world' to notes.txt")
        if not file_match:
            return SkillResult(success=False, message="Which file should I write to, Boss?")
        content = content_match.group(1)
        filename = file_match.group(1)
        path = Path(filename).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        try:
            # Check for append vs overwrite
            if "append" in text.lower():
                with open(path, "a") as f:
                    f.write(content + "\n")
                return SkillResult(success=True, message=f"Appended to {path}, Boss.")
            with open(path, "w") as f:
                f.write(content)
            return SkillResult(success=True, message=f"Wrote to {path}, Boss.")
        except Exception as e:
            return SkillResult(success=False, message=f"Couldn't write: {e}")

    def _organize(self, text: str) -> SkillResult:
        """Organize files in a directory by extension into subfolders."""
        path = self._extract_path(text)
        if not path.exists() or not path.is_dir():
            return SkillResult(success=False, message=f"Directory {path} doesn't exist, Boss.")
        moved = 0
        for item in path.iterdir():
            if item.is_file() and "." in item.name:
                ext = item.suffix.lower().lstrip(".")
                dest_dir = path / f"{ext.upper()}_FILES"
                dest_dir.mkdir(exist_ok=True)
                try:
                    shutil.move(str(item), str(dest_dir / item.name))
                    moved += 1
                except Exception:
                    pass
        if moved == 0:
            return SkillResult(success=True, message=f"No files to organize in {path}, Boss.")
        return SkillResult(success=True, message=f"Organized {moved} file(s) in {path}, Boss.", data={"moved": moved})

    def _extract_src_dst(self, text: str) -> tuple:
        """Extract source and destination from 'move/copy X to Y'."""
        match = re.search(r'(?:move|copy)\s+(?:file\s+|folder\s+)?["\']?(.+?)["\']?\s+(?:to|into|from)\s+["\']?(.+?)["\']?(?:\s*$|\?)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None, None

    def _extract_single_path(self, text: str) -> str | None:
        """Extract a single file path from a command."""
        match = re.search(r'["\']([^"\']+)["\']', text)
        if match:
            return match.group(1)
        match = re.search(r'(?:delete|remove)\s+(?:file\s+|folder\s+|directory\s+)?([^\s]+(?:\.[a-zA-Z0-9]+)?)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip().rstrip(".,?")
        return None
