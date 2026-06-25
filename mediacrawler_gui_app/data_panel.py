# -*- coding: utf-8 -*-
"""Result-file panel for the desktop GUI."""

from __future__ import annotations

from .controls import eyebrow
from .flet_compat import ft
from .models import CrawlConfig
from .results import human_size, scan_data_files
from .theme import BODY_STACK, C, MONO_STACK, R_MD, R_SM, pad_sym


class DataPanel:
    """Mutable result-list controls and refresh operation."""

    def __init__(self, page: ft.Page, cfg: CrawlConfig) -> None:
        self.page = page
        self.cfg = cfg
        self.data_list = ft.ListView(spacing=8, padding=0, expand=True)
        self.refresh_btn = self._create_refresh_button()
        self.root = self._create_root()

    def _create_refresh_button(self) -> ft.OutlinedButton:
        return ft.OutlinedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.REFRESH_ROUNDED, color=C.MOSS_500, size=16),
                    ft.Text(
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
            on_click=lambda e: self.refresh(),
        )

    def _create_root(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [eyebrow("Results", "采集结果"), ft.Container(expand=True), self.refresh_btn]
                    ),
                    ft.Container(content=self.data_list, expand=True),
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

    def _data_row(self, item: dict) -> ft.Control:
        record_text = ""
        if item.get("records") is not None:
            record_text = f"  ·  {item['records']} records"
        icon = {
            "jsonl": ft.Icons.LIST_ALT_OUTLINED,
            "json": ft.Icons.DATA_OBJECT,
            "csv": ft.Icons.TABLE_VIEW_OUTLINED,
        }.get(item["type"], ft.Icons.INSERT_DRIVE_FILE_OUTLINED)
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(icon, size=17, color=C.MOSS_500),
                        width=32,
                        height=32,
                        bgcolor=C.MOSS_200,
                        border_radius=R_SM,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                item["name"],
                                size=13,
                                color=C.COFFEE_900,
                                weight=ft.FontWeight.W_600,
                                font_family=MONO_STACK,
                            ),
                            ft.Text(
                                f"{item['type'].upper()}  ·  {human_size(item['size'])}{record_text}",
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
            padding=pad_sym(horizontal=14, vertical=10),
            border=ft.BorderSide(1, C.CREAM_300),
            border_radius=R_SM,
        )

    def refresh(self) -> None:
        files = scan_data_files(self.cfg.platform)
        self.data_list.controls.clear()
        if not files:
            self.data_list.controls.append(self._empty_state())
        else:
            for item in files:
                self.data_list.controls.append(self._data_row(item))
        try:
            self.page.update()
        except Exception:
            pass

    def _empty_state(self) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.FOLDER_OPEN_OUTLINED, color=C.TAUPE_400, size=28),
                    ft.Text(
                        "No results yet  /  暂无采集结果",
                        size=13,
                        color=C.TAUPE_500,
                        font_family=BODY_STACK,
                    ),
                    ft.Text(
                        f"After a crawl, files appear under data/{self.cfg.platform}/",
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
