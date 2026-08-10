#!/usr/bin/env python
"""ARIA entry point script."""

import sys
from pathlib import Path

# Ensure the package is importable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aria.core.assistant import main

if __name__ == "__main__":
    main()
