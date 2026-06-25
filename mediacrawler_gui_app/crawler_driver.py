# -*- coding: utf-8 -*-
"""Subprocess CLI contract for driving MediaCrawler from the GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .models import CrawlConfig
from .runtime import BASE_CMD

PLATFORMS = [
    ("xhs", "小红书 Xiaohongshu"),
    ("dy", "抖音 Douyin"),
    ("ks", "快手 Kuaishou"),
    ("bili", "哔哩哔哩 Bilibili"),
    ("wb", "微博 Weibo"),
    ("tieba", "百度贴吧 Tieba"),
    ("zhihu", "知乎 Zhihu"),
]

LOGIN_TYPES = [
    ("qrcode", "扫码 QR code"),
    ("cookie", "Cookie"),
    ("phone", "手机号 Phone"),
]

CRAWLER_TYPES = [
    ("search", "关键词搜索 Search"),
    ("detail", "笔记详情 Detail"),
    ("creator", "创作者 Creator"),
]

SAVE_OPTIONS = ["jsonl", "csv", "json", "db", "sqlite", "mongodb", "excel", "postgres"]


def build_command(cfg: CrawlConfig, repo_root: Path) -> list[str]:
    """Build the exact CLI the crawler expects. Same order as crawler_manager."""
    cmd = list(BASE_CMD)
    cmd += ["--platform", cfg.platform]
    cmd += ["--lt", cfg.login_type]
    cmd += ["--type", cfg.crawler_type]
    cmd += ["--save_data_option", cfg.save_option]

    if cfg.crawler_type == "search" and cfg.keywords.strip():
        cmd += ["--keywords", cfg.keywords.strip()]
    elif cfg.crawler_type == "detail" and cfg.specified_ids.strip():
        cmd += ["--specified_id", cfg.specified_ids.strip()]
    elif cfg.crawler_type == "creator" and cfg.creator_ids.strip():
        cmd += ["--creator_id", cfg.creator_ids.strip()]

    cmd += ["--get_comment", "true" if cfg.comments else "false"]
    cmd += ["--get_sub_comment", "true" if cfg.sub_comments else "false"]

    if cfg.notes_count and cfg.notes_count > 0:
        cmd += ["--crawler_max_notes_count", str(cfg.notes_count)]

    if cfg.cookies.strip():
        cmd += ["--cookies", cfg.cookies.strip()]

    cmd += ["--headless", "true" if cfg.headless else "false"]

    _ = repo_root
    return cmd


def parse_log_level(line: str) -> str:
    """Classify a crawler log line into the GUI color levels."""
    up = line.upper()
    if "ERROR" in up or "FAILED" in up or "TRACEBACK" in up:
        return "error"
    if "WARNING" in up or "WARN" in up:
        return "warning"
    if "SUCCESS" in up or "完成" in line or "成功" in line or "DONE" in up:
        return "success"
    if "DEBUG" in up:
        return "debug"
    return "info"


def decode_process_output(raw: bytes | str) -> str:
    """Decode crawler subprocess output without letting bad bytes kill the UI."""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return raw


def classify_crawl_completion(returncode: Optional[int], current_status: str) -> tuple[str, str, str]:
    """Return (next_status, log_level, message) for a finished crawler process."""
    if current_status == "stopping":
        return "idle", "info", "Crawler stopped · 已停止"
    if returncode == 0:
        return "idle", "success", "Crawler completed successfully · 采集完成"
    if returncode is None:
        return "error", "error", "Crawler exit status unavailable · 未能获取采集进程退出码"
    return "error", "error", f"Crawler exited with code {returncode}"
