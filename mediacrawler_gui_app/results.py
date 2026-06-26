# -*- coding: utf-8 -*-
"""Result-file discovery for the desktop GUI data panel."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .runtime import DATA_DIR


def scan_data_files(platform: str) -> list[dict]:
    """Return result-file descriptors under data/{platform}/."""
    out: list[dict] = []
    base = DATA_DIR / platform
    if not base.exists():
        return out

    for ftype in ("jsonl", "json", "csv"):
        data_dir = base / ftype
        if not data_dir.exists():
            continue
        for path in data_dir.glob(f"*.{ftype}"):
            try:
                stat = path.stat()
                size = stat.st_size
                mtime = stat.st_mtime
            except OSError:
                size = 0
                mtime = 0.0
            records = count_records(path, ftype) if ftype in ("jsonl", "json") else None
            out.append(
                {
                    "name": path.name,
                    "type": ftype,
                    "size": size,
                    "records": records,
                    "mtime": mtime,
                    "path": str(path),
                }
            )
    out.sort(key=lambda item: item["mtime"], reverse=True)
    return out


def count_records(path: Path, ftype: str) -> Optional[int]:
    """Best-effort record count for jsonl (lines) / json (array length)."""
    try:
        if ftype == "jsonl":
            with path.open("r", encoding="utf-8", errors="replace") as file:
                return sum(1 for line in file if line.strip())
        if ftype == "json":
            import json

            with path.open("r", encoding="utf-8", errors="replace") as file:
                data = json.load(file)
            return len(data) if isinstance(data, list) else 1
    except Exception:
        return None
    return None


def human_size(n: int) -> str:
    """Format a byte count for the result-list UI."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0
    return f"{n:.1f} GB"
