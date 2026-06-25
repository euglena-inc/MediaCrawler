# -*- coding: utf-8 -*-
"""Brand tokens and small Flet compatibility helpers for the desktop GUI."""

from __future__ import annotations

from .flet_compat import ft

HEX = ft.Colors


class C:
    """Brand color tokens (mirror colors_and_type.css :root)."""

    CREAM_100 = "#FBF6EF"
    CREAM_50 = "#FDFBF7"
    CREAM_200 = "#F4EBDD"
    CREAM_300 = "#EADCC8"
    CREAM_400 = "#DCC8AB"

    MOSS_500 = "#5C7A42"
    MOSS_600 = "#496231"
    MOSS_700 = "#394D26"
    MOSS_200 = "#DCE6C8"

    CARAMEL_500 = "#B5651D"
    GOLD_400 = "#E0B973"
    GOLD_600 = "#B0863A"

    TAUPE_600 = "#6E5238"
    TAUPE_500 = "#8C6A4A"
    TAUPE_400 = "#A88A6A"

    COFFEE_900 = "#261C12"
    COFFEE_800 = "#362A1D"
    ON_DARK_2 = "#C9B79E"

    DANGER = "#B23A1E"


LOG_COLORS = {
    "info": C.TAUPE_600,
    "success": C.MOSS_600,
    "warning": C.GOLD_600,
    "error": C.CARAMEL_500,
    "debug": C.TAUPE_400,
}

DISPLAY_FONT = "Space Grotesk"
BODY_FONT = "Hanken Grotesk"
MONO_FONT = "JetBrains Mono"
CJK = "PingFang SC, Microsoft YaHei, system-ui, sans-serif"

DISPLAY_STACK = f"{DISPLAY_FONT}, {CJK}"
BODY_STACK = f"{BODY_FONT}, {CJK}"
MONO_STACK = f"{MONO_FONT}, ui-monospace, SF Mono, Menlo, monospace"

R_XS = 2
R_SM = 4
R_MD = 8
R_LG = 14
R_PILL = 999


def _blur_style():
    """Return the Flet blur-style enum across old and new Flet names."""
    return getattr(ft, "BlurStyle", getattr(ft, "ShadowBlurStyle", None)).NORMAL


def shadow_md() -> ft.BoxShadow:
    """Soft, warm-tinted medium shadow."""
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=12,
        color="rgba(74,59,42,0.08)",
        offset=ft.Offset(0, 4),
        blur_style=_blur_style(),
    )


def shadow_sm() -> ft.BoxShadow:
    """Soft, warm-tinted small shadow."""
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=3,
        color="rgba(74,59,42,0.08)",
        offset=ft.Offset(0, 1),
        blur_style=_blur_style(),
    )


def pad_sym(horizontal: float = 0, vertical: float = 0):
    """Symmetric padding (h=left/right, v=top/bottom)."""
    return ft.Padding(left=horizontal, top=vertical, right=horizontal, bottom=vertical)


def pad_all(n: float):
    """Uniform padding on all four sides."""
    return ft.Padding(left=n, top=n, right=n, bottom=n)
