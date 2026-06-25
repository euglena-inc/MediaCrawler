# -*- coding: utf-8 -*-
"""Header construction and status-chip updates."""

from __future__ import annotations

from dataclasses import dataclass

from .controls import elapsed_chip, eyebrow, status_chip
from .flet_compat import ft
from .models import AppState
from .theme import C, DISPLAY_STACK, R_PILL, R_SM, pad_sym


@dataclass
class HeaderRefs:
    """Controls in the header that app.py mutates."""

    root: ft.Control
    status_chip: ft.Container
    elapsed_chip: ft.Control

    def apply_status(self, state: AppState) -> None:
        chip = status_chip(state)
        self.status_chip.content = chip.content
        self.status_chip.bgcolor = chip.bgcolor


def create_header(state: AppState) -> HeaderRefs:
    """Create the fixed app header."""
    brand_wordmark = ft.Text(
        "MediaCrawler",
        size=21,
        weight=ft.FontWeight.W_400,
        color=C.COFFEE_900,
        font_family=DISPLAY_STACK,
    )
    live_status = ft.Container(
        content=status_chip(state).content,
        bgcolor=C.CREAM_200,
        padding=pad_sym(horizontal=13, vertical=6),
        border_radius=R_PILL,
    )
    elapsed = elapsed_chip()

    root = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.RADAR_OUTLINED, color=C.MOSS_500, size=20),
                            width=34,
                            height=34,
                            bgcolor=C.MOSS_200,
                            border_radius=R_SM,
                            alignment=ft.Alignment(0, 0),
                        ),
                        brand_wordmark,
                    ],
                    spacing=12,
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Row(
                    [
                        eyebrow("Adaptive automation", "自适应采集 · 小红书"),
                        ft.Container(expand=True),
                        elapsed,
                        live_status,
                    ],
                    spacing=12,
                    alignment=ft.MainAxisAlignment.START,
                ),
            ],
            spacing=8,
        ),
        bgcolor=C.CREAM_50,
        padding=pad_sym(horizontal=28, vertical=18),
        border=ft.Border(bottom=ft.BorderSide(1, C.CREAM_300)),
    )
    return HeaderRefs(root=root, status_chip=live_status, elapsed_chip=elapsed)
