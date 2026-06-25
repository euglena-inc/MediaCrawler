# -*- coding: utf-8 -*-
"""Flet page assembly for the MediaCrawler desktop GUI."""

from __future__ import annotations

import asyncio
import time

from .control_panel import ControlPanelRefs, create_control_panel
from .controls import load_fonts
from .data_panel import DataPanel
from .flet_compat import ft
from .header import HeaderRefs, create_header
from .lifecycle import CrawlerLifecycle
from .log_panel import LogPanel, create_log_panel
from .models import AppState, CrawlConfig
from .runtime import flog
from .theme import BODY_STACK, C, MONO_STACK, pad_all, pad_sym


async def main(page: ft.Page) -> None:
    """Build the MediaCrawler desktop GUI on the given page."""
    _configure_page(page)
    state = AppState()
    cfg = CrawlConfig()
    page.data = state

    header = create_header(state)
    log_panel = create_log_panel(page, state)
    data_panel = DataPanel(page, cfg)
    lifecycle: CrawlerLifecycle | None = None

    def safe_update(reason: str = "") -> None:
        try:
            page.update()
        except Exception as exc:  # noqa
            flog("page.update FAIL (%s): %s" % (reason, exc))

    def set_status(new_status: str) -> None:
        state.status = new_status
        header.apply_status(state)
        if new_status == "running":
            header.elapsed_chip.visible = True
            state.started_at = state.started_at or time.time()
        if new_status in ("idle", "error") and new_status == "idle":
            state.started_at = None
        sync_button_states()
        safe_update("set_status:" + new_status)

    def sync_button_states() -> None:
        running = state.status == "running"
        stopping = state.status == "stopping"
        can_start = not running and not stopping
        can_stop = running
        control_panel.start_btn.disabled = False
        control_panel.stop_btn.disabled = False
        control_panel.apply_button_visual_state(can_start, can_stop)
        for control in control_panel.config_controls:
            control.disabled = running or stopping
        data_panel.refresh_btn.disabled = running or stopping

    async def start_from_button() -> None:
        if lifecycle is not None:
            await lifecycle.start_crawl()

    async def stop_from_button() -> None:
        if lifecycle is not None:
            await lifecycle.stop_crawl()

    control_panel = create_control_panel(page, cfg, start_from_button, stop_from_button)
    lifecycle = CrawlerLifecycle(
        page=page,
        state=state,
        cfg=cfg,
        log_view=log_panel.view,
        qr_image=control_panel.qr_image,
        append_log_line=lambda level, text: log_panel.append_line(state, level, text),
        set_status=set_status,
        safe_update=safe_update,
        refresh_data=data_panel.refresh,
    )

    page.add(_build_page_shell(header, control_panel, data_panel, log_panel, cfg))
    sync_button_states()
    data_panel.refresh()
    log_panel.append_line(state, "info", "Ready. Configure your crawl and press Start  ·  就绪，配置后点击开始")
    safe_update("initial")

    asyncio.create_task(lifecycle.tick_timer(header.elapsed_chip))
    page.run_task(lifecycle.qr_watcher)
    page.run_task(lifecycle.data_refresher)


def _configure_page(page: ft.Page) -> None:
    page.title = "MediaCrawler · 小红书采集"
    page.window.width = 1120
    page.window.height = 740
    page.window.min_width = 960
    page.window.min_height = 640
    page.bgcolor = C.CREAM_100
    page.theme = ft.Theme(color_scheme_seed=C.MOSS_500, font_family=BODY_STACK)
    page.theme_mode = ft.ThemeMode.LIGHT
    load_fonts(page)
    page.padding = 0


def _build_page_shell(
    header: HeaderRefs,
    control_panel: ControlPanelRefs,
    data_panel: DataPanel,
    log_panel: LogPanel,
    cfg: CrawlConfig,
) -> ft.Control:
    body = ft.Container(
        content=ft.Row(
            [
                ft.Container(content=control_panel.root, width=500),
                ft.Column(
                    [
                        ft.Container(content=data_panel.root, height=178),
                        log_panel.root,
                    ],
                    spacing=16,
                    expand=True,
                ),
            ],
            spacing=16,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        padding=pad_all(20),
        expand=True,
    )
    return ft.Column(
        [header.root, ft.Container(content=body, expand=True), _create_footer(cfg)],
        spacing=0,
        expand=True,
    )


def _create_footer(cfg: CrawlConfig) -> ft.Control:
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.RADAR_OUTLINED, color=C.TAUPE_400, size=14),
                ft.Text(
                    "MediaCrawler desktop GUI - a thin subprocess wrapper over main.py. No black boxes.",
                    size=11.5,
                    color=C.TAUPE_400,
                    font_family=BODY_STACK,
                ),
                ft.Container(width=8),
                ft.Text(
                    "桌面端仅以子进程方式驱动现有爬虫，100% 复用既有能力。",
                    size=10.5,
                    color=C.TAUPE_400,
                    font_family=BODY_STACK,
                ),
                ft.Container(expand=True),
                ft.Text(
                    f"data/{cfg.platform}/",
                    size=11,
                    color=C.TAUPE_500,
                    font_family=MONO_STACK,
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.START,
        ),
        bgcolor=C.COFFEE_900,
        padding=pad_sym(horizontal=28, vertical=12),
    )
