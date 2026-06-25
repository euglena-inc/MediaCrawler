# -*- coding: utf-8 -*-
"""Runtime paths and subprocess constants for the desktop GUI."""

from __future__ import annotations

import sys
import time
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
PACKAGE_DIR = Path(__file__).resolve().parent

if FROZEN:
    APP_DIR = Path(sys.executable).resolve().parent
    REPO_ROOT = APP_DIR / "payload" / "crawler"
    CHILD_PY = APP_DIR / "payload" / "python" / "bin" / "python3"
    PW_BROWSERS = APP_DIR / "payload" / "ms-playwright"
    BASE_CMD = [str(CHILD_PY), "main.py"]
else:
    APP_DIR = PACKAGE_DIR.parent
    REPO_ROOT = PACKAGE_DIR.parent
    CHILD_PY = None
    PW_BROWSERS = None
    BASE_CMD = ["uv", "run", "python", "main.py"]

MAIN_PY = REPO_ROOT / "main.py"
DATA_DIR = REPO_ROOT / "data"
MAX_LOG_LINES = 4000


def flog(msg: str) -> None:
    """Append a timestamped diagnostic line to data/gui.log."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / "gui.log", "a", encoding="utf-8") as log_file:
            log_file.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass
