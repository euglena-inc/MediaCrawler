# -*- coding: utf-8 -*-
"""
MediaCrawler · 小红书采集 — desktop GUI (Flet).

This is a NEW, ADDITIVE entry point. It does NOT import, modify, or replace any
crawler internals (no `import config`, no `import media_platform.*`, no
`cmd_arg.parse_cmd`). The existing crawler is driven 100% via subprocess, exactly
like `api/services/crawler_manager.py` already drives it for the FastAPI WebUI:

    uv run python main.py --platform xhs --lt qrcode --type search \
        --keywords "..." --save_data_option jsonl --headless false

So every media_platform crawler, the FastAPI api/ app, main.py CLI, config/,
the WebUI build in api/webui/, the Dockerfile and the GitHub Action keep working
unchanged. The GUI is a thin wrapper over the same CLI.

Launch:
    uv sync && flet run mediacrawler_gui.py        # dev
    python mediacrawler_gui.py                     # direct (uvicorn-free)
    flet pack mediacrawler_gui.py                  -> standalone .app/.exe

Importing this module does NOT open a window — `flet.app(...)` is guarded behind
`if __name__ == "__main__":`, so the theme/controls/helpers can be imported and
unit-tested safely.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --- Flet is the only third-party dependency this module needs. ---
# We guard ONLY the top-level `import flet` so that an import of this module
# degrades cleanly when flet is not yet installed (docs / lint without flet).
# A narrower guard is intentional: a real API mismatch (a renamed symbol) should
# surface as a normal ImportError, not masquerade as "flet missing".
try:
    import flet as ft
except ImportError as _flet_missing:  # pragma: no cover - environment guard
    raise SystemExit(
        "flet is required for the MediaCrawler desktop GUI.\n"
        "Install it with:  uv add flet   (or)  pip install flet\n"
        "Then run:         flet run mediacrawler_gui.py"
    ) from _flet_missing

from flet import (  # noqa: E402  (imported after the flet guard)
    Control,
    Dropdown,
    ElevatedButton,
    IconButton,
    Icons,
    MainAxisAlignment,
    OutlinedButton,
    ResponsiveRow,
    Row,
    Switch,
    Text,
    TextField,
    alignment,
)


# =============================================================================
# THEME — euglena design tokens, applied faithfully to the Flet canvas.
#   Canvas is CREAM (never white), text is warm COFFEE (never pure black),
#   primary is warm olive MOSS (euglena green), clay/sienna is the contrast
#   accent, gold is a soft highlight. Corners are tight (4px default), pill
#   (999px) for status chips only. Shadows are soft + warm-tinted.
# =============================================================================

HEX = ft.Colors  # alias; we mostly use hex strings below for brand fidelity.


class C:
    """Brand color tokens (mirror colors_and_type.css :root)."""

    CREAM_100 = "#FBF6EF"  # page background (canvas) — NEVER white
    CREAM_50 = "#FDFBF7"   # raised cards / surfaces
    CREAM_200 = "#F4EBDD"  # sunken surface
    CREAM_300 = "#EADCC8"  # default border
    CREAM_400 = "#DCC8AB"  # strong border

    MOSS_500 = "#5C7A42"  # primary / euglena green / success (living accent)
    MOSS_600 = "#496231"
    MOSS_700 = "#394D26"
    MOSS_200 = "#DCE6C8"  # accent soft

    CARAMEL_500 = "#B5651D"  # clay/sienna contrast accent
    GOLD_400 = "#E0B973"     # soft highlight
    GOLD_600 = "#B0863A"     # warning tone

    TAUPE_600 = "#6E5238"  # secondary text
    TAUPE_500 = "#8C6A4A"
    TAUPE_400 = "#A88A6A"  # tertiary / quiet Chinese support layer

    COFFEE_900 = "#261C12"  # primary text — NEVER pure black
    COFFEE_800 = "#362A1D"
    ON_DARK_2 = "#C9B79E"   # subtext on dark bands

    DANGER = "#B23A1E"


# Log-stream level colors (muted info, olive success, gold warning, clay/red error).
LOG_COLORS = {
    "info": C.TAUPE_600,
    "success": C.MOSS_600,
    "warning": C.GOLD_600,
    "error": C.CARAMEL_500,
    "debug": C.TAUPE_400,
}

# Fonts. Flet loads Google Fonts at runtime via page.fonts. CJK fallbacks are
# baked into the stack so Chinese stays readable even if a font fails to load.
DISPLAY_FONT = "Space Grotesk"
BODY_FONT = "Hanken Grotesk"
MONO_FONT = "JetBrains Mono"
CJK = "PingFang SC, Microsoft YaHei, system-ui, sans-serif"

DISPLAY_STACK = f"{DISPLAY_FONT}, {CJK}"
BODY_STACK = f"{BODY_FONT}, {CJK}"
MONO_STACK = f"{MONO_FONT}, ui-monospace, SF Mono, Menlo, monospace"


# Radii (tight per brand; pill is ONLY for status chips).
R_XS = 2
R_SM = 4   # DEFAULT — buttons, inputs, small cards
R_MD = 8   # feature cards, panels, flow container
R_LG = 14  # large feature / CTA bands
R_PILL = 999


def _shadow_md() -> ft.BoxShadow:
    """Soft, warm-tinted (coffee rgba) medium shadow."""
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=12,
        color="rgba(74,59,42,0.08)",
        offset=ft.Offset(0, 4),
        # Flet renamed ShadowBlurStyle -> BlurStyle; both names exist across
        # versions, so resolve whichever is present.
        blur_style=getattr(ft, "BlurStyle", getattr(ft, "ShadowBlurStyle", None)).NORMAL,
    )


def _shadow_sm() -> ft.BoxShadow:
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=3,
        color="rgba(74,59,42,0.08)",
        offset=ft.Offset(0, 1),
        blur_style=getattr(ft, "BlurStyle", getattr(ft, "ShadowBlurStyle", None)).NORMAL,
    )


# Padding helpers. Flet's padding API has shifted across versions: some expose
# `ft.padding.symmetric/.all`, others only `ft.Padding(left,top,right,bottom)`.
# We normalize to the lowest-common-denominator `ft.Padding` form so the GUI
# renders identically on 0.27+ (the pyproject floor) and newer.
def _pad_sym(horizontal: float = 0, vertical: float = 0):
    """Symmetric padding (h=left/right, v=top/bottom)."""
    return ft.Padding(left=horizontal, top=vertical, right=horizontal, bottom=vertical)


def _pad_all(n: float):
    """Uniform padding on all four sides."""
    return ft.Padding(left=n, top=n, right=n, bottom=n)


# =============================================================================
# CRAWLER DRIVER — subprocess contract (mirrors crawler_manager.py).
#   cwd = the MediaCrawler repo root (where main.py lives). We resolve it
#   relative to this file so the GUI keeps working whether launched from the
#   repo root or packaged with `flet pack` (frozen onedir exe).
#
#   FROZEN layout (beside the onedir exe at <APP_DIR>/MediaCrawler, where
#   <APP_DIR> = dist/MediaCrawler/):
#     <APP_DIR>/payload/crawler/      full MediaCrawler repo (main.py, etc.)
#     <APP_DIR>/payload/venv/         relocatable uv-created Python 3.11 venv
#     <APP_DIR>/payload/ms-playwright/  Playwright Chromium browser dir
#   In dev (NOT frozen) the repo itself is the cwd and the crawler is launched
#   via `uv run python main.py` exactly as before — behavior unchanged.
# =============================================================================

# Detect a PyInstaller/flet-pack frozen build. When frozen, sys.executable is
# the onedir exe and the payload sits beside it; when not, this file lives at
# <repo_root>/mediacrawler_gui.py and main.py is its sibling.
FROZEN = bool(getattr(sys, "frozen", False))

if FROZEN:
    # Beside the onedir exe: <APP_DIR>/MediaCrawler -> APP_DIR = exe's parent.
    APP_DIR = Path(sys.executable).resolve().parent
    REPO_ROOT = APP_DIR / "payload" / "crawler"
    CHILD_PY = APP_DIR / "payload" / "python" / "bin" / "python3"
    PW_BROWSERS = APP_DIR / "payload" / "ms-playwright"
    # Run main.py with the bundled portable Python (deps in its own site-packages;
    # NOT a venv — no uv, no system Python needed at runtime).
    BASE_CMD = [str(CHILD_PY), "main.py"]
else:
    # Dev mode — byte-for-byte equivalent to the original behavior.
    REPO_ROOT = Path(__file__).resolve().parent
    BASE_CMD = ["uv", "run", "python", "main.py"]
    PW_BROWSERS = None  # no PLAYWRIGHT_BROWSERS_PATH injection in dev.

MAIN_PY = REPO_ROOT / "main.py"
DATA_DIR = REPO_ROOT / "data"

MAX_LOG_LINES = 4000  # cap the in-memory log ring buffer to bound memory.


def _flog(msg: str) -> None:
    """事后调试用：把带时间戳的行追加到 data/gui.log（即使日志面板没显示也能查）。"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / "gui.log", "a", encoding="utf-8") as _f:
            _f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


# Platform / login / crawler / save-option enums mirror cmd_arg/arg.py exactly
# (kept as plain data here — we deliberately do NOT import the crawler package).
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
    headless: bool = False  # HEADED by default — qrcode login + captchas visible


def build_command(cfg: CrawlConfig, repo_root: Path) -> list[str]:
    """Build the exact CLI the crawler expects. Same order as crawler_manager."""
    cmd = list(BASE_CMD)
    cmd += ["--platform", cfg.platform]
    cmd += ["--lt", cfg.login_type]
    cmd += ["--type", cfg.crawler_type]
    cmd += ["--save_data_option", cfg.save_option]

    # Per-type required argument (mirrors crawler_manager._build_command).
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

    # HEADED is the key flag for visible qrcode login / slider captchas.
    # Drives BOTH config.HEADLESS and config.CDP_HEADLESS (see cmd_arg/arg.py).
    cmd += ["--headless", "true" if cfg.headless else "false"]

    # cwd is the repo root (where main.py lives) — never None.
    _ = repo_root
    return cmd


def parse_log_level(line: str) -> str:
    """Same heuristics as crawler_manager._parse_log_level (incl. CJK markers)."""
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


# =============================================================================
# STATE — a small controller wrapping the subprocess lifecycle + log buffer.
# =============================================================================


@dataclass
class AppState:
    """Mutable app state. Held on the page via page.data for clarity."""

    proc: Optional[subprocess.Popen] = None
    status: str = "idle"  # idle | running | stopping | error
    started_at: Optional[float] = None
    reader_task: Optional[asyncio.Task] = None
    log_lines: list[tuple[str, str]] = field(default_factory=list)  # (level, text)
    last_log_render: float = 0.0


def status_label(status: str) -> tuple[str, str]:
    """(EN label, hex color) for the live status chip."""
    return {
        "idle": ("Idle", C.TAUPE_600),
        "running": ("Running", C.MOSS_600),
        "stopping": ("Stopping", C.GOLD_600),
        "error": ("Error", C.DANGER),
    }.get(status, ("Idle", C.TAUPE_600))


# =============================================================================
# DATA PANEL — scan the data/ output dir for result files.
#   Default output (no --save_data_path) is data/{platform}/{file_type}/...
#   per tools/async_file_writer.py::_get_file_path. We scan json/jsonl/csv/json
#   and report name + size + (for json/jsonl) record count.
# =============================================================================


def scan_data_files(platform: str) -> list[dict]:
    """Return a list of result-file descriptors under data/{platform}/."""
    out: list[dict] = []
    base = DATA_DIR / platform
    if not base.exists():
        return out
    for ftype in ("jsonl", "json", "csv"):
        d = base / ftype
        if not d.exists():
            continue
        for p in sorted(d.glob(f"*.{ftype}"), key=os.path.getmtime, reverse=True):
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            records = count_records(p, ftype) if ftype in ("jsonl", "json") else None
            out.append(
                {
                    "name": p.name,
                    "type": ftype,
                    "size": size,
                    "records": records,
                    "mtime": p.stat().st_mtime if p.exists() else 0.0,
                    "path": str(p),
                }
            )
    return out


def count_records(p: Path, ftype: str) -> Optional[int]:
    """Best-effort record count for jsonl (lines) / json (array length)."""
    try:
        if ftype == "jsonl":
            with p.open("r", encoding="utf-8", errors="replace") as f:
                return sum(1 for line in f if line.strip())
        if ftype == "json":
            import json

            with p.open("r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            return len(data) if isinstance(data, list) else 1
    except Exception:
        return None
    return None


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0
    return f"{n:.1f} GB"


# =============================================================================
# UI BUILDERS — every section returns a Control. Theme tokens flow from C.*.
# =============================================================================


def _eyebrow(text_en: str, text_zh: str = "") -> Control:
    """Signature section kicker: UPPERCASE tracked moss-500 EN + quiet ZH."""
    parts = [
        Text(
            text_en.upper(),
            size=11,
            color=C.MOSS_500,
            weight=ft.FontWeight.W_600,
            font_family=BODY_STACK,
        )
    ]
    if text_zh:
        parts.append(
            Text(
                text_zh,
                size=11,
                color=C.TAUPE_400,
                weight=ft.FontWeight.W_500,
                font_family=BODY_STACK,
            )
        )
    return Row(
        parts,
        spacing=9,
        alignment=MainAxisAlignment.START,
    )


def _status_chip(state: AppState) -> Control:
    label, color = status_label(state.status)
    return ft.Container(
        content=Row(
            [
                ft.Container(
                    width=7,
                    height=7,
                    border_radius=R_PILL,
                    bgcolor=color,
                ),
                Text(
                    label,
                    size=12,
                    color=color,
                    weight=ft.FontWeight.W_600,
                    font_family=BODY_STACK,
                ),
            ],
            spacing=7,
            alignment=MainAxisAlignment.START,
        ),
        bgcolor=C.MOSS_200 if state.status == "running" else C.CREAM_200,
        padding=_pad_sym(horizontal=13, vertical=6),
        border_radius=R_PILL,
    )


def _elapsed_chip(state: AppState) -> Control:
    return ft.Container(
        content=Row(
            [
                ft.Icon(Icons.TIMER_OUTLINED, size=15, color=C.TAUPE_500),
                Text(
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


def _section_card(*controls: Control, padding: int = 26, bgcolor: str = C.CREAM_50) -> Control:
    """Feature/panel card: cream-50 raised, cream-300 border, radius-md."""
    return ft.Container(
        content=ft.Column(controls, spacing=14) if len(controls) > 1 else controls[0],
        bgcolor=bgcolor,
        padding=padding,
        border=ft.BorderSide(1, C.CREAM_300),
        border_radius=R_MD,
    )


# ---- Reusable styled inputs --------------------------------------------------


def _input_label(en: str, zh: str = "") -> Control:
    return Row(
        [
            Text(
                en,
                size=12,
                color=C.TAUPE_600,
                weight=ft.FontWeight.W_600,
                font_family=BODY_STACK,
            ),
            Text(zh, size=11, color=C.TAUPE_400, font_family=BODY_STACK)
            if zh
            else ft.Container(),
        ],
        spacing=8,
    )


def _dropdown(options, value, on_change=None, width: Optional[float] = None) -> Dropdown:
    return Dropdown(
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


def _dropdown_str(options, value, on_change=None, width: Optional[float] = None) -> Dropdown:
    return Dropdown(
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


def _text_field(value="", on_change=None, password=False, width=None, multiline=False) -> TextField:
    return TextField(
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


def _switch(label_en: str, label_zh: str, value: bool, on_change=None) -> Control:
    sw = Switch(
        value=value,
        on_change=on_change,
        active_color=C.MOSS_500,
        inactive_thumb_color=C.CREAM_400,
    )
    return Row(
        [
            sw,
            Text(
                label_en,
                size=13,
                color=C.COFFEE_900,
                weight=ft.FontWeight.W_600,
                font_family=BODY_STACK,
            ),
            Text(label_zh, size=11, color=C.TAUPE_400, font_family=BODY_STACK),
        ],
        spacing=10,
        alignment=MainAxisAlignment.START,
    )


# =============================================================================
# MAIN VIEW
# =============================================================================


def _load_fonts(page: ft.Page) -> None:
    """Load Google Fonts; degrade gracefully (CJK fallback stack stays usable)."""
    page.fonts = {
        DISPLAY_FONT: "https://fonts.gstatic.com/s/spacegrotesk/v16/V8mDoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7oUUxjLg.ttf",
        BODY_FONT: "https://fonts.gstatic.com/s/hankengrotesk/v8/ieVq2YZDLpAKbACPTjrLiZsAqaQ5wQPOFq7ceyq6.woff2",
        MONO_FONT: "https://fonts.gstatic.com/s/jetbrainsmono/v18/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8yKxjPVmUsaaDhw.woff2",
    }


async def main(page: ft.Page) -> None:
    """Build the MediaCrawler desktop GUI on the given page."""
    # --- Window + theme setup ---
    page.title = "MediaCrawler · 小红书采集"
    page.window.width = 1120
    page.window.height = 740
    page.window.min_width = 960
    page.window.min_height = 640
    page.bgcolor = C.CREAM_100  # canvas is CREAM, never white
    page.theme = ft.Theme(
        color_scheme_seed=C.MOSS_500,
        font_family=BODY_STACK,
    )
    page.theme_mode = ft.ThemeMode.LIGHT
    _load_fonts(page)
    page.padding = 0
    page.data = AppState()
    state: AppState = page.data

    cfg = CrawlConfig()

    # --- State mutators that refresh the UI ---
    def safe_update(reason: str = "") -> None:
        """page.update()，但把失败记到 gui.log（之前 try/except 静默吞掉了，导致面板不刷新却无日志）。"""
        try:
            page.update()
        except Exception as _e:  # noqa
            _flog("page.update FAIL (%s): %s" % (reason, _e))

    def set_status(new_status: str) -> None:
        state.status = new_status
        status_chip.content = _status_chip(state).content
        status_chip.bgcolor = _status_chip(state).bgcolor
        if new_status == "running":
            elapsed_chip.visible = True
            state.started_at = state.started_at or time.time()
        if new_status == "idle" or new_status == "error":
            if new_status == "idle":
                state.started_at = None
        sync_button_states()
        safe_update("set_status:" + new_status)

    def sync_button_states() -> None:
        running = state.status == "running"
        stopping = state.status == "stopping"
        start_btn.disabled = running or stopping
        stop_btn.disabled = not running
        # While running, lock the config controls so you can't mid-edit.
        for ctl in config_controls:
            ctl.disabled = running or stopping
        refresh_btn.disabled = running or stopping

    # =====================================================================
    # HEADER
    # =====================================================================
    brand_wordmark = Text(
        "MediaCrawler",
        size=21,
        weight=ft.FontWeight.W_400,
        color=C.COFFEE_900,
        font_family=DISPLAY_STACK,
        # letter spacing baked into the font stack; tight -0.02em via display.
    )
    status_chip = ft.Container(
        content=_status_chip(state).content,
        bgcolor=C.CREAM_200,
        padding=_pad_sym(horizontal=13, vertical=6),
        border_radius=R_PILL,
    )
    elapsed_chip = _elapsed_chip(state)

    header = ft.Container(
        content=ft.Column(
            [
                Row(
                    [
                        # small moss tile as a logo stand-in (the real logo is
                        # an illustration asset; we keep a brand glyph tile here).
                        ft.Container(
                            content=ft.Icon(Icons.RADAR_OUTLINED, color=C.MOSS_500, size=20),
                            width=34,
                            height=34,
                            bgcolor=C.MOSS_200,
                            border_radius=R_SM,
                            alignment=ft.Alignment(0, 0),
                        ),
                        brand_wordmark,
                    ],
                    spacing=12,
                    alignment=MainAxisAlignment.START,
                ),
                Row(
                    [
                        _eyebrow("Adaptive automation", "自适应采集 · 小红书"),
                        ft.Container(expand=True),
                        elapsed_chip,
                        status_chip,
                    ],
                    spacing=12,
                    alignment=MainAxisAlignment.START,
                ),
            ],
            spacing=8,
        ),
        bgcolor=C.CREAM_50,
        padding=_pad_sym(horizontal=28, vertical=18),
        border=ft.Border(bottom=ft.BorderSide(1, C.CREAM_300)),
    )

    # =====================================================================
    # CONTROL PANEL
    # =====================================================================
    platform_dd = _dropdown(PLATFORMS, cfg.platform, width=240)
    login_dd = _dropdown(LOGIN_TYPES, cfg.login_type, width=200)
    crawler_dd = _dropdown(CRAWLER_TYPES, cfg.crawler_type, width=240)
    save_dd = _dropdown_str(SAVE_OPTIONS, cfg.save_option, width=180)

    keywords_field = _text_field(cfg.keywords, width=520)
    notes_field = _text_field(str(cfg.notes_count), width=120)
    cookies_field = _text_field(cfg.cookies, password=True, width=520)

    # Dynamic inputs that swap with crawler_type (search->keywords, detail->ids,
    # creator->creator_ids), mirroring crawler_manager per-type args.
    primary_arg_label = _input_label("Keywords", "关键词（逗号分隔）")
    primary_arg_field = keywords_field
    secondary_block = ft.Column(
        [_input_label("Login cookies (optional)", "可选 · cookie 登录时填写"), cookies_field],
        spacing=6,
        visible=(cfg.login_type == "cookie"),
    )

    comments_switch_ctl = _switch(
        "Fetch comments", "抓取评论", cfg.comments
    )
    sub_comments_switch_ctl = _switch(
        "Fetch sub-comments", "抓取子评论", cfg.sub_comments
    )

    def on_platform(e):
        cfg.platform = platform_dd.value

    def on_login(e):
        cfg.login_type = login_dd.value
        secondary_block.visible = cfg.login_type == "cookie"
        try:
            page.update()
        except Exception:
            pass

    def on_crawler(e):
        cfg.crawler_type = crawler_dd.value
        if cfg.crawler_type == "search":
            primary_arg_label.controls[0].value = "Keywords"
            primary_arg_label.controls[1].value = "关键词（逗号分隔）"
            primary_arg_field.value = cfg.keywords
            primary_arg_field.password = False
            primary_arg_field.can_reveal_password = False
        elif cfg.crawler_type == "detail":
            primary_arg_label.controls[0].value = "Note IDs / URLs"
            primary_arg_label.controls[1].value = "笔记 ID 或链接（逗号分隔）"
            primary_arg_field.value = cfg.specified_ids
            primary_arg_field.password = False
            primary_arg_field.can_reveal_password = False
        else:  # creator
            primary_arg_label.controls[0].value = "Creator IDs / URLs"
            primary_arg_label.controls[1].value = "创作者主页链接（逗号分隔）"
            primary_arg_field.value = cfg.creator_ids
            primary_arg_field.password = False
            primary_arg_field.can_reveal_password = False
        try:
            page.update()
        except Exception:
            pass

    def on_save(e):
        cfg.save_option = save_dd.value

    def on_keywords(e):
        v = primary_arg_field.value or ""
        if cfg.crawler_type == "search":
            cfg.keywords = v
        elif cfg.crawler_type == "detail":
            cfg.specified_ids = v
        else:
            cfg.creator_ids = v

    def on_notes(e):
        try:
            cfg.notes_count = max(1, int(notes_field.value or "5"))
        except ValueError:
            cfg.notes_count = 5

    def on_cookies(e):
        cfg.cookies = cookies_field.value or ""

    def on_comments(e):
        cfg.comments = comments_switch_ctl.controls[0].value

    def on_sub_comments(e):
        cfg.sub_comments = sub_comments_switch_ctl.controls[0].value

    # Wire handlers
    platform_dd.on_select = on_platform
    login_dd.on_select = on_login
    crawler_dd.on_select = on_crawler
    save_dd.on_select = on_save
    keywords_field.on_change = on_keywords
    notes_field.on_change = on_notes
    cookies_field.on_change = on_cookies
    comments_switch_ctl.controls[0].on_change = on_comments
    sub_comments_switch_ctl.controls[0].on_change = on_sub_comments

    # Headed-mode notice — the crawler opens a REAL browser window for QR login.
    notice = ft.Container(
        content=Row(
            [
                ft.Icon(Icons.QR_CODE_2_OUTLINED, color=C.MOSS_500, size=18),
                Text(
                    "请在弹出的浏览器窗口中扫码登录  /  Scan the QR in the browser window that opened",
                    size=12.5,
                    color=C.TAUPE_600,
                    font_family=BODY_STACK,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=10,
        ),
        bgcolor=C.MOSS_200,
        padding=_pad_sym(horizontal=14, vertical=10),
        border_radius=R_SM,
        border=ft.BorderSide(1, C.MOSS_200),
    )

    # Primary Start / Stop buttons (brand button spec).
    start_btn = ElevatedButton(
        content=Row(
            [
                ft.Icon(Icons.PLAY_ARROW_ROUNDED, color=C.CREAM_50, size=18),
                Text(
                    "Start crawl",
                    size=15,
                    color=C.CREAM_50,
                    weight=ft.FontWeight.W_700,
                    font_family=BODY_STACK,
                ),
            ],
            spacing=8,
        ),
        style=ft.ButtonStyle(bgcolor=C.MOSS_700, color=C.CREAM_50),
        elevation=0,
        on_click=lambda e: asyncio.ensure_future(start_crawl()),
    )
    stop_btn = OutlinedButton(
        content=Row(
            [
                ft.Icon(Icons.STOP_CIRCLE_OUTLINED, color=C.CARAMEL_500, size=18),
                Text(
                    "Stop",
                    size=14.5,
                    color=C.COFFEE_900,
                    weight=ft.FontWeight.W_600,
                    font_family=BODY_STACK,
                ),
            ],
            spacing=8,
        ),
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.TRANSPARENT,
            side=ft.border.BorderSide(1.5, C.CREAM_400),
            shape=ft.RoundedRectangleBorder(radius=R_SM),
        ),
        on_click=lambda e: asyncio.ensure_future(stop_crawl()),
        disabled=True,
    )

    # The control panel card.
    config_controls: list[Control] = [
        platform_dd,
        login_dd,
        crawler_dd,
        save_dd,
        keywords_field,
        notes_field,
        cookies_field,
        comments_switch_ctl.controls[0],
        sub_comments_switch_ctl.controls[0],
    ]

    # QR 登录码图片面板：爬虫跑起来后，watcher 把 data/login_qrcode.png 刷进来。
    qr_image = ft.Image(
        src="", width=220, height=220, visible=False, fit=ft.BoxFit.CONTAIN, border_radius=R_SM
    )

    control_panel = _section_card(
        Row(
            [
                _eyebrow("Control panel", "采集配置"),
            ]
        ),
        ResponsiveRow(
            [
                ft.Column(
                    [_input_label("Platform", "平台"), platform_dd], col={"sm": 6, "md": 4}
                ),
                ft.Column(
                    [_input_label("Login type", "登录方式"), login_dd], col={"sm": 6, "md": 4}
                ),
                ft.Column(
                    [_input_label("Crawler type", "采集类型"), crawler_dd],
                    col={"sm": 6, "md": 4},
                ),
                ft.Column(
                    [_input_label("Save option", "存储方式"), save_dd], col={"sm": 6, "md": 4}
                ),
                ft.Column(
                    [_input_label("Notes per crawl", "笔记数量"), notes_field],
                    col={"sm": 6, "md": 4},
                ),
            ],
            spacing=16,
            run_spacing=16,
        ),
        ft.Column([primary_arg_label, primary_arg_field], spacing=6),
        secondary_block,
        ft.Column(
            [_input_label("Comments", "评论抓取"),
             Row([comments_switch_ctl, sub_comments_switch_ctl], spacing=24)],
            spacing=8,
        ),
        notice,
        Row([start_btn, stop_btn], spacing=12, alignment=MainAxisAlignment.START),
        qr_image,
    )

    # =====================================================================
    # LOG STREAM
    # =====================================================================
    log_view = ft.ListView(
        spacing=2,
        padding=_pad_sym(horizontal=14, vertical=12),
        auto_scroll=True,
        expand=True,
    )

    def _append_log_line(level: str, text: str) -> None:
        state.log_lines.append((level, text))
        if len(state.log_lines) > MAX_LOG_LINES:
            # Drop oldest 10% to bound memory (ring-buffer-ish).
            drop = max(1, len(state.log_lines) - MAX_LOG_LINES)
            state.log_lines = state.log_lines[drop:]
        log_view.controls.append(
            ft.Container(
                content=Text(
                    text,
                    size=12,
                    color=LOG_COLORS.get(level, C.TAUPE_600),
                    font_family=MONO_STACK,
                    selectable=True,
                    weight=ft.FontWeight.W_500 if level in ("error", "warning") else ft.FontWeight.W_400,
                ),
                padding=_pad_sym(horizontal=4, vertical=1),
            )
        )

    clear_btn = IconButton(
        icon=Icons.DELETE_SWEEP_OUTLINED,
        icon_color=C.TAUPE_500,
        tooltip="Clear log  /  清空日志",
        on_click=lambda e: clear_log(),
    )

    def clear_log() -> None:
        log_view.controls.clear()
        state.log_lines.clear()
        try:
            page.update()
        except Exception:
            pass

    log_panel = ft.Container(
        content=ft.Column(
            [
                Row(
                    [
                        _eyebrow("Live log", "实时日志"),
                        ft.Container(expand=True),
                        clear_btn,
                    ]
                ),
                ft.Container(
                    content=log_view,
                    bgcolor=C.COFFEE_900,  # dark inverse surface for logs
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
        padding=26,
        border=ft.BorderSide(1, C.CREAM_300),
        border_radius=R_MD,
        expand=True,
    )

    # =====================================================================
    # DATA PANEL
    # =====================================================================
    data_list = ft.ListView(spacing=8, padding=0, expand=True)
    refresh_btn = OutlinedButton(
        content=Row(
            [
                ft.Icon(Icons.REFRESH_ROUNDED, color=C.MOSS_500, size=16),
                Text(
                    "Refresh  /  刷新",
                    size=13,
                    color=C.COFFEE_900,
                    weight=ft.FontWeight.W_600,
                    font_family=BODY_STACK,
                ),
            ],
            spacing=7,
        ),
        style=ft.ButtonStyle(
            side=ft.border.BorderSide(1.5, C.CREAM_400),
            shape=ft.RoundedRectangleBorder(radius=R_SM),
        ),
        on_click=lambda e: refresh_data(),
    )

    def _data_row(d: dict) -> Control:
        rec = ""
        if d.get("records") is not None:
            rec = f"  ·  {d['records']} records"
        return ft.Container(
            content=Row(
                [
                    ft.Container(
                        content=ft.Icon(
                            {
                                "jsonl": Icons.LIST_ALT_OUTLINED,
                                "json": Icons.DATA_OBJECT,
                                "csv": Icons.TABLE_VIEW_OUTLINED,
                            }.get(d["type"], Icons.INSERT_DRIVE_FILE_OUTLINED),
                            size=17,
                            color=C.MOSS_500,
                        ),
                        width=32,
                        height=32,
                        bgcolor=C.MOSS_200,
                        border_radius=R_SM,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Column(
                        [
                            Text(
                                d["name"],
                                size=13,
                                color=C.COFFEE_900,
                                weight=ft.FontWeight.W_600,
                                font_family=MONO_STACK,
                            ),
                            Text(
                                f"{d['type'].upper()}  ·  {human_size(d['size'])}{rec}",
                                size=11,
                                color=C.TAUPE_500,
                                font_family=BODY_STACK,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=12,
            ),
            bgcolor=C.CREAM_50,
            padding=_pad_sym(horizontal=14, vertical=10),
            border=ft.BorderSide(1, C.CREAM_300),
            border_radius=R_SM,
        )

    def refresh_data() -> None:
        files = scan_data_files(cfg.platform)
        data_list.controls.clear()
        if not files:
            data_list.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(Icons.FOLDER_OPEN_OUTLINED, color=C.TAUPE_400, size=28),
                            Text(
                                "No results yet  /  暂无采集结果",
                                size=13,
                                color=C.TAUPE_500,
                                font_family=BODY_STACK,
                            ),
                            Text(
                                f"After a crawl, files appear under data/{cfg.platform}/",
                                size=11,
                                color=C.TAUPE_400,
                                font_family=MONO_STACK,
                            ),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=24,
                    alignment=ft.Alignment(0, 0),
                )
            )
        else:
            for d in files:
                data_list.controls.append(_data_row(d))
        try:
            page.update()
        except Exception:
            pass

    data_panel = ft.Container(
        content=ft.Column(
            [
                Row(
                    [
                        _eyebrow("Results", "采集结果"),
                        ft.Container(expand=True),
                        refresh_btn,
                    ]
                ),
                ft.Container(content=data_list, expand=True),
            ],
            spacing=10,
            expand=True,
        ),
        bgcolor=C.CREAM_50,
        padding=26,
        border=ft.BorderSide(1, C.CREAM_300),
        border_radius=R_MD,
        expand=True,
    )

    # =====================================================================
    # CRAWL LIFECYCLE — start / stop / reader loop
    # =====================================================================

    async def _read_output(proc: subprocess.Popen) -> None:
        """Stream stdout (stderr merged in) line-by-line. Mirror _read_output."""
        loop = asyncio.get_event_loop()
        assert proc.stdout is not None
        try:
            while proc.poll() is None:
                line = await loop.run_in_executor(None, proc.stdout.readline)
                if not line:
                    break  # EOF
                line = line.strip()
                if not line:
                    continue
                _append_log_line(parse_log_level(line), line)
                _flog("out: " + line)
                # Throttle UI updates: batch a few lines per paint.
                now = time.time()
                if now - state.last_log_render > 0.06:  # ~16fps cap
                    state.last_log_render = now
                    safe_update("read:throttle")
            # Drain any remaining buffered output.
            remaining = await loop.run_in_executor(None, proc.stdout.read)
            if remaining:
                for raw in remaining.splitlines():
                    s = raw.strip()
                    if s:
                        _append_log_line(parse_log_level(s), s)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            _flog("reader EXCEPTION: " + str(exc))
            _append_log_line("error", f"Log reader error: {exc}")
        finally:
            rc = proc.returncode
            _flog("reader done rc=%s final_status=%s" % (rc, state.status))
            if rc == 0:
                _append_log_line("success", "Crawler completed successfully · 采集完成")
                set_status("idle")
            elif rc is None or state.status == "stopping":
                _append_log_line("info", "Crawler stopped · 已停止")
                set_status("idle")
            else:
                _append_log_line("error", f"Crawler exited with code {rc}")
                set_status("error")
            safe_update("read:finally")
            # Auto-refresh the data panel when a crawl finishes.
            refresh_data()

    async def start_crawl() -> None:
        if state.status in ("running", "stopping"):
            return
        # Validate per-type required arg, mirroring crawler_manager behavior.
        if cfg.crawler_type == "search" and not cfg.keywords.strip():
            _append_log_line("error", "Keywords are required for search mode  /  搜索模式需要关键词")
            set_status("error")
            try:
                page.update()
            except Exception:
                pass
            return
        if cfg.crawler_type == "detail" and not cfg.specified_ids.strip():
            _append_log_line("error", "Note IDs are required for detail mode  /  详情模式需要笔记 ID")
            set_status("error")
            try:
                page.update()
            except Exception:
                pass
            return
        if cfg.crawler_type == "creator" and not cfg.creator_ids.strip():
            _append_log_line("error", "Creator IDs are required for creator mode  /  创作者模式需要创作者 ID")
            set_status("error")
            try:
                page.update()
            except Exception:
                pass
            return

        # Clear previous log for a clean run.
        log_view.controls.clear()
        state.log_lines.clear()

        cmd = build_command(cfg, REPO_ROOT)
        _flog("start_crawl type=%s kw=%r headless=%s" % (cfg.crawler_type, cfg.keywords, cfg.headless))
        _flog("cmd: " + " ".join(cmd))
        _append_log_line("info", "$ " + " ".join(cmd))
        _append_log_line(
            "info",
            f"cwd: {REPO_ROOT}  ·  platform={cfg.platform}  type={cfg.crawler_type}  login={cfg.login_type}",
        )
        set_status("running")
        try:
            page.update()
        except Exception:
            pass

        # Child env: always unbuffered. When frozen, point Playwright at the
        # bundled browser dir so the crawler finds Chromium-1118. In dev the
        # environment is untouched (PLAYWRIGHT_BROWSERS_PATH not injected).
        child_env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        if FROZEN and PW_BROWSERS is not None:
            child_env["PLAYWRIGHT_BROWSERS_PATH"] = str(PW_BROWSERS)

        # 清掉可能残留的、占用 browser_data profile 锁的 Chromium（上次崩溃/强杀残留），
        # 否则下次 launch_persistent_context 会 "正在现有的浏览器会话中打开" -> TargetClosedError。
        try:
            subprocess.run(
                ["pkill", "-9", "-f", "browser_data/xhs_user_data_dir"],
                check=False, capture_output=True,
            )
        except Exception:
            pass

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1,
                cwd=str(REPO_ROOT),
                env=child_env,
                start_new_session=True,  # 独立进程组：stop 时 killpg 能连 Chrome 一起杀
            )
        except FileNotFoundError as exc:
            _flog("Popen FileNotFoundError: " + str(exc))
            _append_log_line(
                "error",
                f"Failed to launch subprocess (is `uv` on PATH?): {exc}",
            )
            set_status("error")
            try:
                page.update()
            except Exception:
                pass
            return
        except Exception as exc:
            import traceback as _tb
            _flog("Popen EXCEPTION: " + str(exc) + "\n" + _tb.format_exc())
            _append_log_line("error", f"Failed to start crawler: {exc}")
            set_status("error")
            try:
                page.update()
            except Exception:
                pass
            return

        state.proc = proc
        try:
            _flog("launched pid=%s pgid=%s" % (proc.pid, os.getpgid(proc.pid)))
        except Exception as _e:  # noqa
            _flog("launched pid=%s (%s)" % (proc.pid, _e))
        state.reader_task = asyncio.create_task(_read_output(proc))

    async def stop_crawl() -> None:
        proc = state.proc
        _flog("stop_crawl: proc=%s poll=%s" % (proc, (proc.poll() if proc else None)))
        if proc is None or proc.poll() is not None:
            return
        set_status("stopping")
        _append_log_line("warning", "Sending SIGTERM to crawler process  ·  正在停止...")
        try:
            page.update()
        except Exception:
            pass
        try:
            # 杀整个进程组（含 Playwright 起的 Chrome 子进程），避免 Chrome 成为孤儿、
            # 占着 browser_data profile 锁导致下次 Start 报 TargetClosedError。
            try:
                _pgid = os.getpgid(proc.pid)
                os.killpg(_pgid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                proc.send_signal(signal.SIGTERM)
            # Wait up to ~15s for graceful exit (same cadence as stop()).
            for _ in range(30):
                if proc.poll() is not None:
                    break
                await asyncio.sleep(0.5)
            if proc.poll() is None:
                _append_log_line("warning", "Process not responding, sending SIGKILL  ·  强制结束")
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        except Exception as exc:  # pragma: no cover - defensive
            _append_log_line("error", f"Error stopping crawler: {exc}")
        finally:
            if state.reader_task and not state.reader_task.done():
                state.reader_task.cancel()
            state.proc = None
            set_status("idle")

    # =====================================================================
    # ELAPSED TIMER — updates the header chip every second while running.
    # =====================================================================
    async def _tick_timer() -> None:
        while True:
            await asyncio.sleep(1.0)
            if state.status == "running" and state.started_at:
                elapsed = int(time.time() - state.started_at)
                mm, ss = divmod(elapsed, 60)
                elapsed_chip.content.controls[1].value = f"{mm:02d}:{ss:02d}"
                try:
                    page.update()
                except Exception:
                    pass

    asyncio.create_task(_tick_timer())

    # =====================================================================
    # FOOTER — small bilingual note (English primary).
    # =====================================================================
    footer = ft.Container(
        content=Row(
            [
                ft.Icon(Icons.RADAR_OUTLINED, color=C.TAUPE_400, size=14),
                Text(
                    "MediaCrawler desktop GUI — a thin subprocess wrapper over main.py. No black boxes.",
                    size=11.5,
                    color=C.TAUPE_400,
                    font_family=BODY_STACK,
                ),
                ft.Container(width=8),
                Text(
                    "桌面端仅以子进程方式驱动现有爬虫，100% 复用既有能力。",
                    size=10.5,
                    color=C.TAUPE_400,
                    font_family=BODY_STACK,
                ),
                ft.Container(expand=True),
                Text(
                    f"data/{cfg.platform}/",
                    size=11,
                    color=C.TAUPE_500,
                    font_family=MONO_STACK,
                ),
            ],
            spacing=8,
            alignment=MainAxisAlignment.START,
        ),
        bgcolor=C.COFFEE_900,
        padding=_pad_sym(horizontal=28, vertical=12),
    )

    # =====================================================================
    # ASSEMBLE PAGE
    # =====================================================================
    body = ft.Container(
        content=ft.Column(
            [
                control_panel,
                ft.Row(
                    [log_panel, data_panel],
                    spacing=16,
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            ],
            spacing=16,
            expand=True,
        ),
        padding=_pad_all(24),
        expand=True,
    )

    page.add(
        ft.Column(
            [header, ft.Container(content=body, expand=True), footer],
            spacing=0,
            expand=True,
        )
    )

    # Initial state + a first data scan.
    sync_button_states()
    refresh_data()
    _append_log_line("info", "Ready. Configure your crawl and press Start  ·  就绪，配置后点击开始")
    try:
        page.update()
    except Exception:
        pass

    # QR watcher：爬取期间每 1.5s 检查 data/login_qrcode.png，有新文件就以 base64
    # 刷新显示（base64 避免本地文件被缓存、保证每次扫码都能看到最新二维码）。
    async def _qr_watcher() -> None:
        import base64 as _b64
        last_mtime = 0.0
        qr_path = DATA_DIR / "login_qrcode.png"
        while True:
            try:
                if state.running and qr_path.exists():
                    mtime = qr_path.stat().st_mtime
                    if mtime != last_mtime:
                        last_mtime = mtime
                        qr_image.src_base64 = _b64.b64encode(qr_path.read_bytes()).decode()
                        qr_image.visible = True
                        page.update()
                elif not state.running and qr_image.visible:
                    qr_image.visible = False
                    page.update()
            except Exception:
                pass
            await asyncio.sleep(1.5)

    page.run_task(_qr_watcher)


# =============================================================================
# ENTRY POINT — guarded so importing the module never opens a window.
# =============================================================================

if __name__ == "__main__":
    # flet.app dispatches an async target on its own event loop, so we pass the
    # coroutine directly (NOT a sync wrapper around asyncio.run, which would
    # conflict with flet's internal loop).
    ft.app(target=main)
