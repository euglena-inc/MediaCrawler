# -*- coding: utf-8 -*-
"""Public compatibility facade for the MediaCrawler desktop GUI."""

from __future__ import annotations

from .app import main
from .crawler_driver import (
    CRAWLER_TYPES,
    LOGIN_TYPES,
    PLATFORMS,
    SAVE_OPTIONS,
    build_command,
    classify_crawl_completion,
    decode_process_output,
    parse_log_level,
)
from .models import AppState, CrawlConfig, status_label
from .results import count_records, human_size, scan_data_files

__all__ = [
    "AppState",
    "CRAWLER_TYPES",
    "CrawlConfig",
    "LOGIN_TYPES",
    "PLATFORMS",
    "SAVE_OPTIONS",
    "build_command",
    "classify_crawl_completion",
    "count_records",
    "decode_process_output",
    "human_size",
    "main",
    "parse_log_level",
    "scan_data_files",
    "status_label",
]
