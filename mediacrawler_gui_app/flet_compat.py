# -*- coding: utf-8 -*-
"""Flet import guard shared by the desktop GUI package."""

from __future__ import annotations

try:
    import flet as ft
except ImportError as _flet_missing:  # pragma: no cover - environment guard
    raise SystemExit(
        "flet is required for the MediaCrawler desktop GUI.\n"
        "Install it with:  uv add flet   (or)  pip install flet\n"
        "Then run:         flet run mediacrawler_gui.py"
    ) from _flet_missing

__all__ = ["ft"]
