"""Backward-compatible entry point for the MediaCrawler desktop GUI."""

from __future__ import annotations

from mediacrawler_gui_app import (
    AppState,
    CrawlConfig,
    build_command,
    classify_crawl_completion,
    count_records,
    decode_process_output,
    main,
    parse_log_level,
    scan_data_files,
)

__all__ = [
    "AppState",
    "CrawlConfig",
    "build_command",
    "classify_crawl_completion",
    "count_records",
    "decode_process_output",
    "main",
    "parse_log_level",
    "scan_data_files",
]


if __name__ == "__main__":
    from mediacrawler_gui_app.flet_compat import ft

    ft.run(main)
