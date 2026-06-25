# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/tools/crawler_util.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 12:53
# @Desc    : Crawler utility functions

import base64
import json
import random
import re
import urllib
import urllib.parse
from io import BytesIO
from typing import Dict, List, Optional, Tuple, cast

import httpx
from PIL import Image, ImageDraw, ImageShow
from playwright.async_api import BrowserContext, Cookie, Page

from . import utils
from .httpx_util import make_async_client


async def find_login_qrcode(page: Page, selector: str) -> str:
    """find login qrcode image from target selector"""
    try:
        elements = await page.wait_for_selector(
            selector=selector,
        )
        login_qrcode_img = str(await elements.get_property("src"))  # type: ignore
        if "http://" in login_qrcode_img or "https://" in login_qrcode_img:
            async with make_async_client(follow_redirects=True) as client:
                utils.logger.info(f"[find_login_qrcode] get qrcode by url:{login_qrcode_img}")
                resp = await client.get(login_qrcode_img, headers={"User-Agent": get_user_agent()})
                if resp.status_code == 200:
                    image_data = resp.content
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    return base64_image
                raise Exception(f"fetch login image url failed, response message:{resp.text}")
        return login_qrcode_img

    except Exception as e:
        print(e)
        return ""


async def find_qrcode_img_from_canvas(page: Page, canvas_selector: str) -> str:
    """
    find qrcode image from canvas element
    Args:
        page:
        canvas_selector:

    Returns:

    """

    # Wait for Canvas element to load
    canvas = await page.wait_for_selector(canvas_selector)

    # Take screenshot of Canvas element
    screenshot = await canvas.screenshot()

    # Convert screenshot to base64 format
    base64_image = base64.b64encode(screenshot).decode('utf-8')
    return base64_image


def _qrcode_to_ascii(image) -> str:
    """把二维码 PIL 图像渲染成可扫描的 ASCII（██/空格）。

    用左上角定位符（finder pattern，固定 7 个模块宽）精确定位模块尺寸和 QR 原点，
    再从原点按模块步进对齐采样，保证输出忠实于原二维码、手机可扫。
    """
    img = image.convert("L")
    w, h = img.size
    px = img.load()

    def is_dark(x, y):
        return px[x, y] < 128

    # 最上方含暗点的行 = QR 顶部（跳过周围静默区）
    top = 0
    found_top = False
    for y in range(h):
        if any(is_dark(x, y) for x in range(w)):
            top = y
            found_top = True
            break
    if not found_top:
        return "[QR] empty qrcode image"

    # top 行里第一段连续暗点 = 左上定位符的顶边，正好 7 个模块宽
    left = 0
    for x in range(w):
        if is_dark(x, top):
            left = x
            break
    finder_top_pixels = 0
    x = left
    while x < w and is_dark(x, top):
        finder_top_pixels += 1
        x += 1
    module_size = max(1, round(finder_top_pixels / 7))

    # 从 QR 原点 (left, top) 按 module_size 对齐采样；██ = 暗，两个空格 = 亮（约成正方形模块）
    lines = []
    y = top
    while y < h:
        row = []
        x = left
        while x < w:
            row.append("██" if is_dark(x, y) else "  ")
            x += module_size
        lines.append("".join(row))
        y += module_size
    return "\n".join(lines)


def show_qrcode(qr_code) -> None:  # type: ignore
    """parse base64 encode qrcode image and show it.

    headless/API 部署里没有 GUI 图片查看器，PIL Image.show() 不生效。
    改为：保存 PNG（供 API/浏览器取用）+ 把 ASCII 二维码打印到 stdout
    （被日志流/WebUI/kubectl logs 捕获），手机可直接扫描。
    """
    import os

    if "," in qr_code:
        qr_code = qr_code.split(",")[1]
    qr_code = base64.b64decode(qr_code)
    image = Image.open(BytesIO(qr_code))

    # 保存 PNG 到 cwd 下的 data/（爬虫 cwd = 仓库根 / payload/crawler），桌面 GUI
    # 和 WebUI 都能从这里读到 login_qrcode.png 并显示；/app/data 仅容器里有。
    try:
        os.makedirs("data", exist_ok=True)
        image.save("data/login_qrcode.png")
        print(f"[QR] saved login QR PNG -> {os.path.abspath('data/login_qrcode.png')}", flush=True)
    except Exception as e:  # noqa
        print(f"[QR] save qrcode png failed: {e}", flush=True)

    # 打印 ASCII 二维码到控制台。
    # 优先：pyzbar 解码出二维码内容，再用 qrcode 库重渲染成精确模块网格（最稳，手机可扫）。
    # 退回：直接对原图按定位符采样（best-effort）。
    ascii_qr = ""
    try:
        from io import StringIO
        import qrcode
        from pyzbar.pyzbar import decode as _zbar_decode

        decoded = _zbar_decode(image)
        if decoded:
            qr = qrcode.QRCode(
                border=2,
                box_size=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
            )
            qr.add_data(decoded[0].data)
            qr.make(fit=True)
            buf = StringIO()
            qr.print_ascii(out=buf, invert=True)
            ascii_qr = buf.getvalue().rstrip()
    except Exception as e:  # noqa
        print(f"[QR] decode+rerender 不可用，退回图像渲染: {e}", flush=True)

    if not ascii_qr:
        ascii_qr = _qrcode_to_ascii(image)

    border = "=" * 48
    print("\n" + border, flush=True)
    print("[QR] 请用小红书 App 扫描下方二维码登录（约 120s 内有效）", flush=True)
    print("[QR] 扫不了时，浏览器直接打开原图: http://<节点IP>:30101/api/qrcode", flush=True)
    print(ascii_qr, flush=True)
    print(border, flush=True)


def get_user_agent() -> str:
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.53 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.5112.79 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.5060.53 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.4844.84 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5112.79 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5060.53 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.4844.84 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5112.79 Safari/537.36"
    ]
    return random.choice(ua_list)


def get_mobile_user_agent() -> str:
    ua_list = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"
    ]
    return random.choice(ua_list)


def convert_cookies(cookies: Optional[List[Cookie]]) -> Tuple[str, Dict]:
    if not cookies:
        return "", {}
    cookies_str = ";".join([f"{cookie.get('name')}={cookie.get('value')}" for cookie in cookies])
    cookie_dict = dict()
    for cookie in cookies:
        cookie_dict[cookie.get('name')] = cookie.get('value')
    return cookies_str, cookie_dict


async def convert_browser_context_cookies(
    browser_context: BrowserContext, urls: Optional[List[str]] = None
) -> Tuple[str, Dict]:
    cookies = (
        await browser_context.cookies(urls=urls)
        if urls
        else await browser_context.cookies()
    )
    return convert_cookies(cookies)


def convert_str_cookie_to_dict(cookie_str: str) -> Dict:
    cookie_dict: Dict[str, str] = dict()
    if not cookie_str:
        return cookie_dict
    for cookie in cookie_str.split(";"):
        cookie = cookie.strip()
        if not cookie:
            continue
        cookie_list = cookie.split("=")
        if len(cookie_list) != 2:
            continue
        cookie_value = cookie_list[1]
        if isinstance(cookie_value, list):
            cookie_value = "".join(cookie_value)
        cookie_dict[cookie_list[0]] = cookie_value
    return cookie_dict


def match_interact_info_count(count_str: str) -> int:
    if not count_str:
        return 0

    match = re.search(r'\d+', count_str)
    if match:
        number = match.group()
        return int(number)
    else:
        return 0


def format_proxy_info(ip_proxy_info) -> Tuple[Optional[Dict], Optional[str]]:
    """format proxy info for playwright and httpx"""
    # fix circular import issue
    from proxy.proxy_ip_pool import IpInfoModel
    ip_proxy_info = cast(IpInfoModel, ip_proxy_info)

    # Playwright proxy server should be in format "host:port" without protocol prefix
    server = f"{ip_proxy_info.ip}:{ip_proxy_info.port}"
    
    playwright_proxy = {
        "server": server,
    }
    
    # Only add username and password if they are not empty
    if ip_proxy_info.user and ip_proxy_info.password:
        playwright_proxy["username"] = ip_proxy_info.user
        playwright_proxy["password"] = ip_proxy_info.password
    
    # httpx 0.28.1 requires passing proxy URL string directly, not a dictionary
    if ip_proxy_info.user and ip_proxy_info.password:
        httpx_proxy = f"http://{ip_proxy_info.user}:{ip_proxy_info.password}@{ip_proxy_info.ip}:{ip_proxy_info.port}"
    else:
        httpx_proxy = f"http://{ip_proxy_info.ip}:{ip_proxy_info.port}"
    return playwright_proxy, httpx_proxy


def extract_text_from_html(html: str) -> str:
    """Extract text from HTML, removing all tags."""
    if not html:
        return ""

    # Remove script and style elements
    clean_html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL)
    # Remove all other tags
    clean_text = re.sub(r'<[^>]+>', '', clean_html).strip()
    return clean_text

def extract_url_params_to_dict(url: str) -> Dict:
    """Extract URL parameters to dict"""
    url_params_dict = dict()
    if not url:
        return url_params_dict
    parsed_url = urllib.parse.urlparse(url)
    url_params_dict = dict(urllib.parse.parse_qsl(parsed_url.query))
    return url_params_dict
