"""Utility helpers for ARIA."""

from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Optional


def is_headless() -> bool:
    """Detect if running in a headless (no display) environment."""
    if platform.system() == "Linux":
        import os

        return not bool(os.environ.get("DISPLAY"))
    return False


def command_exists(cmd: str) -> bool:
    """Check if a command is available on the system."""
    return shutil.which(cmd) is not None


def run_command(cmd: str, timeout: int = 10) -> Optional[str]:
    """Run a shell command and return its output, or None on failure."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def truncate(text: str, max_len: int = 2000) -> str:
    """Truncate text with an ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "...[truncated]"
