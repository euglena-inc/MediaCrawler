# -*- coding: utf-8 -*-
"""Small state/data models for the desktop GUI."""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from .theme import C


@dataclass
class CrawlConfig:
    """GUI-collected crawl configuration. Mirrors CrawlerStartRequest fields."""

    platform: str = "xhs"
    login_type: str = "qrcode"
    crawler_type: str = "search"
    keywords: str = "编程副业,编程兼职"
    specified_ids: str = ""
    creator_ids: str = ""
    notes_count: int = 5
    comments: bool = False
    sub_comments: bool = False
    save_option: str = "jsonl"
    cookies: str = ""
    headless: bool = False


@dataclass
class AppState:
    """Mutable app state. Held on the page via page.data for clarity."""

    proc: Optional[subprocess.Popen] = None
    status: str = "idle"
    started_at: Optional[float] = None
    reader_task: Optional[asyncio.Task] = None
    log_lines: list[tuple[str, str]] = field(default_factory=list)
    last_log_render: float = 0.0

    @property
    def running(self) -> bool:
        return self.status == "running"


def status_label(status: str) -> tuple[str, str]:
    """Return the English label and color for the live status chip."""
    return {
        "idle": ("Idle", C.TAUPE_600),
        "running": ("Running", C.MOSS_600),
        "stopping": ("Stopping", C.GOLD_600),
        "error": ("Error", C.DANGER),
    }.get(status, ("Idle", C.TAUPE_600))
