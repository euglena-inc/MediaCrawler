# MediaCrawler API/WebUI 镜像（k8s headless 部署版）
# - 基础镜像自带 Playwright + Chromium 及系统依赖
# - 额外装 Node.js（execjs 跑小红书签名 JS）和 libzbar0（pyzbar 解码登录二维码）
# - 默认 headless、关闭 CDP、不抓评论；API 触发的爬虫也强制 headless（k8s 无 X server）
# - 登录二维码：保存 PNG + 打印 ASCII 到控制台 + /api/qrcode 端点供浏览器扫码
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends git curl xz-utils ca-certificates libzbar0; \
    rm -rf /var/lib/apt/lists/*; \
    pip install --no-cache-dir uv

# Node.js：MediaCrawler 用 execjs 执行小红书签名 JS，playwright/python 基础镜像不带 node
ARG NODE_VERSION=20.18.1
RUN set -eux; \
    curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" -o /tmp/node.tar.xz; \
    tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1; \
    rm /tmp/node.tar.xz; \
    node --version; npm --version

COPY . /app/

# k8s 运行态配置（config 默认值 + API 强制 headless）
RUN set -eux; \
    sed -i 's/ENABLE_CDP_MODE = True/ENABLE_CDP_MODE = False/' config/base_config.py; \
    sed -i 's/CDP_CONNECT_EXISTING = True/CDP_CONNECT_EXISTING = False/' config/base_config.py; \
    sed -i 's/^HEADLESS = False/HEADLESS = True/' config/base_config.py; \
    sed -i 's/ENABLE_GET_COMMENTS = True/ENABLE_GET_COMMENTS = False/' config/base_config.py; \
    sed -i 's#"true" if config.headless else "false"#"true"#' api/services/crawler_manager.py; \
    sed -i 's/headless: bool = False/headless: bool = True/' api/schemas/crawler.py; \
    uv sync

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
