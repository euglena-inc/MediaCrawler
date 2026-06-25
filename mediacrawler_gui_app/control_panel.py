# -*- coding: utf-8 -*-
"""Crawler configuration panel and Start/Stop controls."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from .controls import dropdown, dropdown_str, eyebrow, input_label, section_card, switch, text_field
from .crawler_driver import CRAWLER_TYPES, LOGIN_TYPES, PLATFORMS, SAVE_OPTIONS
from .flet_compat import ft
from .models import CrawlConfig
from .theme import BODY_STACK, C, R_SM, pad_sym

AsyncHandler = Callable[[], Awaitable[None]]


@dataclass
class ControlPanelRefs:
    """Controls that app.py needs to mutate from lifecycle state."""

    root: ft.Control
    start_btn: ft.Container
    stop_btn: ft.Container
    qr_image: ft.Image
    config_controls: list[ft.Control]
    apply_button_visual_state: Callable[[bool, bool], None]


def create_control_panel(
    page: ft.Page,
    cfg: CrawlConfig,
    on_start: AsyncHandler,
    on_stop: AsyncHandler,
) -> ControlPanelRefs:
    """Create the left-hand crawler configuration panel."""
    platform_dd = dropdown(PLATFORMS, cfg.platform, width=210)
    login_dd = dropdown(LOGIN_TYPES, cfg.login_type, width=210)
    crawler_dd = dropdown(CRAWLER_TYPES, cfg.crawler_type, width=210)
    save_dd = dropdown_str(SAVE_OPTIONS, cfg.save_option, width=210)

    keywords_field = text_field(cfg.keywords, width=430)
    notes_field = text_field(str(cfg.notes_count), width=120)
    cookies_field = text_field(cfg.cookies, password=True, width=430)
    primary_arg_label = input_label("Keywords", "关键词（逗号分隔）")
    primary_arg_field = keywords_field
    secondary_block = ft.Column(
        [input_label("Login cookies (optional)", "可选 · cookie 登录时填写"), cookies_field],
        spacing=6,
        visible=(cfg.login_type == "cookie"),
    )
    comments_switch_ctl = switch("Fetch comments", "抓取评论", cfg.comments)
    sub_comments_switch_ctl = switch("Fetch sub-comments", "抓取子评论", cfg.sub_comments)

    def try_update() -> None:
        try:
            page.update()
        except Exception:
            pass

    def on_platform(e) -> None:
        cfg.platform = platform_dd.value

    def on_login(e) -> None:
        cfg.login_type = login_dd.value
        secondary_block.visible = cfg.login_type == "cookie"
        try_update()

    def on_crawler(e) -> None:
        cfg.crawler_type = crawler_dd.value
        labels = {
            "search": ("Keywords", "关键词（逗号分隔）", cfg.keywords),
            "detail": ("Note IDs / URLs", "笔记 ID 或链接（逗号分隔）", cfg.specified_ids),
            "creator": ("Creator IDs / URLs", "创作者主页链接（逗号分隔）", cfg.creator_ids),
        }
        label_en, label_zh, value = labels[cfg.crawler_type]
        primary_arg_label.controls[0].value = label_en
        primary_arg_label.controls[1].value = label_zh
        primary_arg_field.value = value
        primary_arg_field.password = False
        primary_arg_field.can_reveal_password = False
        try_update()

    def on_save(e) -> None:
        cfg.save_option = save_dd.value

    def on_keywords(e) -> None:
        value = primary_arg_field.value or ""
        if cfg.crawler_type == "search":
            cfg.keywords = value
        elif cfg.crawler_type == "detail":
            cfg.specified_ids = value
        else:
            cfg.creator_ids = value

    def on_notes(e) -> None:
        try:
            cfg.notes_count = max(1, int(notes_field.value or "5"))
        except ValueError:
            cfg.notes_count = 5

    def on_cookies(e) -> None:
        cfg.cookies = cookies_field.value or ""

    def on_comments(e) -> None:
        cfg.comments = comments_switch_ctl.controls[0].value

    def on_sub_comments(e) -> None:
        cfg.sub_comments = sub_comments_switch_ctl.controls[0].value

    platform_dd.on_select = on_platform
    login_dd.on_select = on_login
    crawler_dd.on_select = on_crawler
    save_dd.on_select = on_save
    keywords_field.on_change = on_keywords
    notes_field.on_change = on_notes
    cookies_field.on_change = on_cookies
    comments_switch_ctl.controls[0].on_change = on_comments
    sub_comments_switch_ctl.controls[0].on_change = on_sub_comments

    notice = _create_notice()
    start_btn = _create_start_button(on_start)
    stop_btn = _create_stop_button(on_stop)

    def apply_button_visual_state(can_start: bool, can_stop: bool) -> None:
        start_icon, start_text = start_btn.content.controls
        stop_icon, stop_text = stop_btn.content.controls
        start_icon.color = C.CREAM_50 if can_start else C.TAUPE_600
        start_text.color = C.CREAM_50 if can_start else C.TAUPE_600
        start_btn.bgcolor = C.MOSS_700 if can_start else C.CREAM_300
        start_btn.border = ft.BorderSide(1.5, C.MOSS_700 if can_start else C.CREAM_400)
        stop_icon.color = C.CREAM_50 if can_stop else C.TAUPE_500
        stop_text.color = C.CREAM_50 if can_stop else C.TAUPE_500
        stop_btn.bgcolor = C.CARAMEL_500 if can_stop else ft.Colors.TRANSPARENT
        stop_btn.border = ft.BorderSide(1.5, C.CARAMEL_500 if can_stop else C.CREAM_400)

    config_controls = [
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
    qr_image = ft.Image(
        src="", width=220, height=220, visible=False, fit=ft.BoxFit.CONTAIN, border_radius=R_SM
    )

    root = section_card(
        ft.Row([eyebrow("Control panel", "采集配置")]),
        _selector_grid(platform_dd, login_dd, crawler_dd, save_dd, notes_field),
        ft.Column([primary_arg_label, primary_arg_field], spacing=6),
        secondary_block,
        ft.Row([start_btn, stop_btn], spacing=12, alignment=ft.MainAxisAlignment.START),
        notice,
        ft.Column(
            [
                input_label("Comments", "评论抓取"),
                ft.Row([comments_switch_ctl, sub_comments_switch_ctl], spacing=14, wrap=True),
            ],
            spacing=8,
        ),
        qr_image,
        padding=18,
    )
    return ControlPanelRefs(
        root=root,
        start_btn=start_btn,
        stop_btn=stop_btn,
        qr_image=qr_image,
        config_controls=config_controls,
        apply_button_visual_state=apply_button_visual_state,
    )


def _selector_grid(platform_dd, login_dd, crawler_dd, save_dd, notes_field) -> ft.Control:
    return ft.ResponsiveRow(
        [
            ft.Column([input_label("Platform", "平台"), platform_dd], col={"sm": 6, "md": 6}),
            ft.Column([input_label("Login type", "登录方式"), login_dd], col={"sm": 6, "md": 6}),
            ft.Column([input_label("Crawler type", "采集类型"), crawler_dd], col={"sm": 6, "md": 6}),
            ft.Column([input_label("Save option", "存储方式"), save_dd], col={"sm": 6, "md": 6}),
            ft.Column([input_label("Notes per crawl", "笔记数量"), notes_field], col={"sm": 6, "md": 6}),
        ],
        spacing=12,
        run_spacing=12,
    )


def _create_notice() -> ft.Control:
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.QR_CODE_2_OUTLINED, color=C.MOSS_500, size=18),
                ft.Text(
                    "请在弹出的浏览器窗口中扫码登录  /  Scan the QR in the browser window that opened",
                    size=12.5,
                    color=C.TAUPE_600,
                    font_family=BODY_STACK,
                    weight=ft.FontWeight.W_500,
                    expand=True,
                ),
            ],
            spacing=10,
        ),
        bgcolor=C.MOSS_200,
        padding=pad_sym(horizontal=14, vertical=10),
        border_radius=R_SM,
        border=ft.BorderSide(1, C.MOSS_200),
    )


def _create_start_button(on_start: AsyncHandler) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, color=C.CREAM_50, size=18),
                ft.Text(
                    "Start crawl",
                    size=15,
                    color=C.CREAM_50,
                    weight=ft.FontWeight.W_700,
                    font_family=BODY_STACK,
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=C.MOSS_700,
        border=ft.BorderSide(1.5, C.MOSS_700),
        border_radius=R_SM,
        padding=pad_sym(horizontal=22, vertical=10),
        ink=True,
        on_click=lambda e: asyncio.ensure_future(on_start()),
    )


def _create_stop_button(on_stop: AsyncHandler) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.STOP_CIRCLE_OUTLINED, color=C.CARAMEL_500, size=18),
                ft.Text(
                    "Stop",
                    size=14.5,
                    color=C.COFFEE_900,
                    weight=ft.FontWeight.W_600,
                    font_family=BODY_STACK,
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.TRANSPARENT,
        border=ft.BorderSide(1.5, C.CREAM_400),
        border_radius=R_SM,
        padding=pad_sym(horizontal=22, vertical=10),
        ink=True,
        on_click=lambda e: asyncio.ensure_future(on_stop()),
    )
