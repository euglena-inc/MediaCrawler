#!/usr/bin/env bash
# 一键启动 MediaCrawler 桌面 GUI（Flet）。
# 注意：爬虫会打开一个真实可见的 Chrome 窗口 —— 小红书登录二维码在那个窗口里扫。
set -euo pipefail
cd "$(dirname "$0")"

echo "» sync deps (installs flet)…"
uv sync --quiet

echo "» launch GUI…"
exec uv run python mediacrawler_gui.py
