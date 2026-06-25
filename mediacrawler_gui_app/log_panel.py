# -*- coding: utf-8 -*-
"""Live log panel for crawler subprocess output."""

from __future__ import annotations

from dataclasses import dataclass

from .controls import eyebrow
from .flet_compat import ft
from .models import AppState
from .runtime import MAX_LOG_LINES
from .theme import BODY_STACK, C, LOG_COLORS, MONO_STACK, R_MD, pad_sym


@dataclass
class LogPanel:
    """Mutable log-panel controls and operations."""

    root: ft.Control
    view: ft.ListView

    def append_line(self, state: AppState, level: str, text: str) -> None:
        state.log_lines.append((level, text))
        if len(state.log_lines) > MAX_LOG_LINES:
            drop = max(1, len(state.log_lines) - MAX_LOG_LINES)
            state.log_lines = state.log_lines[drop:]
            del self.view.controls[:drop]
        self.view.controls.append(
            ft.Container(
                content=ft.Text(
                    text,
                    size=12,
                    color=LOG_COLORS.get(level, C.TAUPE_600),
                    font_family=MONO_STACK,
                    selectable=True,
                    weight=ft.FontWeight.W_500
                    if level in ("error", "warning")
                    else ft.FontWeight.W_400,
                ),
                padding=pad_sym(horizontal=4, vertical=1),
            )
        )

    def clear(self, page: ft.Page, state: AppState) -> None:
        self.view.controls.clear()
        state.log_lines.clear()
        try:
            page.update()
        except Exception:
            pass


def create_log_panel(page: ft.Page, state: AppState) -> LogPanel:
    """Create the live log panel and its clear action."""
    log_view = ft.ListView(
        spacing=2,
        padding=pad_sym(horizontal=14, vertical=12),
        auto_scroll=True,
        expand=True,
    )
    panel = LogPanel(root=ft.Container(), view=log_view)
    clear_btn = ft.IconButton(
        icon=ft.Icons.DELETE_SWEEP_OUTLINED,
        icon_color=C.TAUPE_500,
        tooltip="Clear log  /  清空日志",
        on_click=lambda e: panel.clear(page, state),
    )
    panel.root = ft.Container(
        content=ft.Column(
            [
                ft.Row([eyebrow("Live log", "实时日志"), ft.Container(expand=True), clear_btn]),
                ft.Container(
                    content=log_view,
                    bgcolor=C.COFFEE_900,
                    border_radius=R_MD,
                    border=ft.BorderSide(1, C.COFFEE_800),
                    padding=0,
                    expand=True,
                ),
            ],
            spacing=10,
            expand=True,
        ),
        bgcolor=C.CREAM_50,
        padding=18,
        border=ft.BorderSide(1, C.CREAM_300),
        border_radius=R_MD,
        expand=True,
    )
    _ = BODY_STACK
    return panel
