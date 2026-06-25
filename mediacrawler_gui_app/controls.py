# -*- coding: utf-8 -*-
"""Reusable styled Flet controls for the desktop GUI."""

from __future__ import annotations

from typing import Optional

from .flet_compat import ft
from .models import AppState, status_label
from .theme import (
    BODY_FONT,
    BODY_STACK,
    C,
    DISPLAY_FONT,
    DISPLAY_STACK,
    MONO_FONT,
    MONO_STACK,
    R_MD,
    R_PILL,
    R_SM,
    pad_sym,
)


def load_fonts(page: ft.Page) -> None:
    """Load Google Fonts; CJK fallback stack stays usable if loading fails."""
    page.fonts = {
        DISPLAY_FONT: "https://fonts.gstatic.com/s/spacegrotesk/v16/V8mDoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7oUUxjLg.ttf",
        BODY_FONT: "https://fonts.gstatic.com/s/hankengrotesk/v8/ieVq2YZDLpAKbACPTjrLiZsAqaQ5wQPOFq7ceyq6.woff2",
        MONO_FONT: "https://fonts.gstatic.com/s/jetbrainsmono/v18/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8yKxjPVmUsaaDhw.woff2",
    }


def eyebrow(text_en: str, text_zh: str = "") -> ft.Control:
    """Signature section kicker: uppercase moss English plus quiet Chinese."""
    parts: list[ft.Control] = [
        ft.Text(
            text_en.upper(),
            size=11,
            color=C.MOSS_500,
            weight=ft.FontWeight.W_600,
            font_family=BODY_STACK,
        )
    ]
    if text_zh:
        parts.append(
            ft.Text(
                text_zh,
                size=11,
                color=C.TAUPE_400,
                weight=ft.FontWeight.W_500,
                font_family=BODY_STACK,
            )
        )
    return ft.Row(parts, spacing=9, alignment=ft.MainAxisAlignment.START)


def status_chip(state: AppState) -> ft.Control:
    """Build the live status chip for the header."""
    label, color = status_label(state.status)
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(width=7, height=7, border_radius=R_PILL, bgcolor=color),
                ft.Text(
                    label,
                    size=12,
                    color=color,
                    weight=ft.FontWeight.W_600,
                    font_family=BODY_STACK,
                ),
            ],
            spacing=7,
            alignment=ft.MainAxisAlignment.START,
        ),
        bgcolor=C.MOSS_200 if state.status == "running" else C.CREAM_200,
        padding=pad_sym(horizontal=13, vertical=6),
        border_radius=R_PILL,
    )


def elapsed_chip() -> ft.Control:
    """Build the hidden elapsed-time chip; app.py updates the value."""
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.TIMER_OUTLINED, size=15, color=C.TAUPE_500),
                ft.Text(
                    "00:00",
                    size=12,
                    color=C.TAUPE_600,
                    font_family=MONO_STACK,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=7,
        ),
        visible=False,
    )


def section_card(*controls: ft.Control, padding: int = 26, bgcolor: str = C.CREAM_50) -> ft.Control:
    """Cream raised panel with brand border/radius."""
    return ft.Container(
        content=ft.Column(list(controls), spacing=14) if len(controls) > 1 else controls[0],
        bgcolor=bgcolor,
        padding=padding,
        border=ft.BorderSide(1, C.CREAM_300),
        border_radius=R_MD,
    )


def input_label(en: str, zh: str = "") -> ft.Control:
    """Small bilingual field label."""
    return ft.Row(
        [
            ft.Text(
                en,
                size=12,
                color=C.TAUPE_600,
                weight=ft.FontWeight.W_600,
                font_family=BODY_STACK,
            ),
            ft.Text(zh, size=11, color=C.TAUPE_400, font_family=BODY_STACK)
            if zh
            else ft.Container(),
        ],
        spacing=8,
    )


def dropdown(options, value, on_change=None, width: Optional[float] = None) -> ft.Dropdown:
    """Styled key/text dropdown."""
    return ft.Dropdown(
        options=[ft.dropdown.Option(k, text=t) for k, t in options],
        value=value,
        on_select=on_change,
        bgcolor=C.CREAM_50,
        filled=True,
        text_size=14,
        color=C.COFFEE_900,
        dense=True,
        border_color=C.CREAM_400,
        focused_border_color=C.MOSS_500,
        border_radius=R_SM,
        text_style=ft.TextStyle(font_family=BODY_STACK),
        width=width,
    )


def dropdown_str(options, value, on_change=None, width: Optional[float] = None) -> ft.Dropdown:
    """Styled string dropdown."""
    return ft.Dropdown(
        options=[ft.dropdown.Option(o) for o in options],
        value=value,
        on_select=on_change,
        bgcolor=C.CREAM_50,
        filled=True,
        text_size=14,
        color=C.COFFEE_900,
        dense=True,
        border_color=C.CREAM_400,
        focused_border_color=C.MOSS_500,
        border_radius=R_SM,
        text_style=ft.TextStyle(font_family=BODY_STACK),
        width=width,
    )


def text_field(value="", on_change=None, password=False, width=None, multiline=False) -> ft.TextField:
    """Styled text field."""
    return ft.TextField(
        value=value,
        on_change=on_change,
        password=password,
        can_reveal_password=password,
        bgcolor=C.CREAM_50,
        filled=True,
        text_size=14,
        color=C.COFFEE_900,
        dense=True,
        border_color=C.CREAM_400,
        focused_border_color=C.MOSS_500,
        border_radius=R_SM,
        text_style=ft.TextStyle(font_family=BODY_STACK),
        width=width,
        multiline=multiline,
        min_lines=1 if not multiline else 2,
    )


def switch(label_en: str, label_zh: str, value: bool, on_change=None) -> ft.Control:
    """Styled switch with bilingual label."""
    switch_control = ft.Switch(
        value=value,
        on_change=on_change,
        active_color=C.MOSS_500,
        inactive_thumb_color=C.CREAM_400,
    )
    return ft.Row(
        [
            switch_control,
            ft.Text(
                label_en,
                size=13,
                color=C.COFFEE_900,
                weight=ft.FontWeight.W_600,
                font_family=BODY_STACK,
            ),
            ft.Text(label_zh, size=11, color=C.TAUPE_400, font_family=BODY_STACK),
        ],
        spacing=10,
        alignment=ft.MainAxisAlignment.START,
    )
