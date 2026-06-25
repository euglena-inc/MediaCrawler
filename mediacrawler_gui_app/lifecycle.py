# -*- coding: utf-8 -*-
"""Crawler subprocess lifecycle used by the desktop GUI."""

from __future__ import annotations

import asyncio
import base64
import os
import signal
import subprocess
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass

from .crawler_driver import build_command, classify_crawl_completion, decode_process_output, parse_log_level
from .flet_compat import ft
from .models import AppState, CrawlConfig
from .runtime import DATA_DIR, FROZEN, PW_BROWSERS, REPO_ROOT, flog


@dataclass
class CrawlerLifecycle:
    """Start, stop, stream, and background refresh behavior."""

    page: ft.Page
    state: AppState
    cfg: CrawlConfig
    log_view: ft.ListView
    qr_image: ft.Image
    append_log_line: Callable[[str, str], None]
    set_status: Callable[[str], None]
    safe_update: Callable[[str], None]
    refresh_data: Callable[[], None]

    async def read_output(self, proc: subprocess.Popen) -> None:
        loop = asyncio.get_event_loop()
        assert proc.stdout is not None
        try:
            while proc.poll() is None:
                raw_line = await loop.run_in_executor(None, proc.stdout.readline)
                if not raw_line:
                    break
                line = decode_process_output(raw_line).strip()
                if not line:
                    continue
                self.append_log_line(parse_log_level(line), line)
                flog("out: " + line)
                print(line, flush=True)
                now = time.time()
                if now - self.state.last_log_render > 0.06:
                    self.state.last_log_render = now
                    self.safe_update("read:throttle")
            await self._drain_remaining_output(loop, proc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            flog("reader EXCEPTION: " + str(exc))
            self.append_log_line("error", f"Log reader error: {exc}")
        finally:
            rc = await self._wait_for_process(loop, proc)
            flog("reader done rc=%s final_status=%s" % (rc, self.state.status))
            print(">>> CRAWL DONE  rc=%s  (results in data/%s/)" % (rc, self.cfg.platform), flush=True)
            next_status, level, message = classify_crawl_completion(rc, self.state.status)
            self.append_log_line(level, message)
            self.state.proc = None
            self.set_status(next_status)
            self.safe_update("read:finally")
            self.refresh_data()

    async def _drain_remaining_output(self, loop, proc: subprocess.Popen) -> None:
        remaining = await loop.run_in_executor(None, proc.stdout.read)
        if remaining:
            for raw in decode_process_output(remaining).splitlines():
                line = raw.strip()
                if line:
                    self.append_log_line(parse_log_level(line), line)

    async def _wait_for_process(self, loop, proc: subprocess.Popen):
        try:
            return await loop.run_in_executor(None, proc.wait)
        except Exception as exc:  # pragma: no cover - defensive
            flog("proc.wait EXCEPTION: " + str(exc))
            return proc.returncode

    async def start_crawl(self) -> None:
        if self.state.status in ("running", "stopping"):
            return
        if not self._validate_required_arg():
            return

        self.log_view.controls.clear()
        self.state.log_lines.clear()

        cmd = build_command(self.cfg, REPO_ROOT)
        flog("start_crawl type=%s kw=%r headless=%s" % (
            self.cfg.crawler_type,
            self.cfg.keywords,
            self.cfg.headless,
        ))
        flog("cmd: " + " ".join(cmd))
        print("\n>>> START  " + " ".join(cmd), flush=True)
        self.append_log_line("info", "$ " + " ".join(cmd))
        self.append_log_line(
            "info",
            f"cwd: {REPO_ROOT}  ·  platform={self.cfg.platform}  type={self.cfg.crawler_type}  login={self.cfg.login_type}",
        )
        self.set_status("running")
        self.safe_update("start:set-running")

        child_env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        if FROZEN and PW_BROWSERS is not None:
            child_env["PLAYWRIGHT_BROWSERS_PATH"] = str(PW_BROWSERS)
        self._kill_stale_browser_profile()

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                cwd=str(REPO_ROOT),
                env=child_env,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            self._handle_launch_error(f"Failed to launch subprocess (is `uv` on PATH?): {exc}", exc)
            return
        except Exception as exc:
            flog("Popen EXCEPTION: " + str(exc) + "\n" + traceback.format_exc())
            self._handle_launch_error(f"Failed to start crawler: {exc}", exc)
            return

        self.state.proc = proc
        try:
            flog("launched pid=%s pgid=%s" % (proc.pid, os.getpgid(proc.pid)))
        except Exception as exc:  # noqa
            flog("launched pid=%s (%s)" % (proc.pid, exc))
        self.state.reader_task = asyncio.create_task(self.read_output(proc))

    def _validate_required_arg(self) -> bool:
        required = {
            "search": (self.cfg.keywords.strip(), "Keywords are required for search mode  /  搜索模式需要关键词"),
            "detail": (self.cfg.specified_ids.strip(), "Note IDs are required for detail mode  /  详情模式需要笔记 ID"),
            "creator": (self.cfg.creator_ids.strip(), "Creator IDs are required for creator mode  /  创作者模式需要创作者 ID"),
        }
        value, message = required[self.cfg.crawler_type]
        if value:
            return True
        self.append_log_line("error", message)
        self.set_status("error")
        self.safe_update("start:validation")
        return False

    def _handle_launch_error(self, message: str, exc: Exception) -> None:
        flog("Popen launch error: " + str(exc))
        self.append_log_line("error", message)
        self.set_status("error")
        self.safe_update("start:launch-error")

    def _kill_stale_browser_profile(self) -> None:
        try:
            subprocess.run(
                ["pkill", "-9", "-f", "browser_data/xhs_user_data_dir"],
                check=False,
                capture_output=True,
            )
        except Exception:
            pass

    async def stop_crawl(self) -> None:
        proc = self.state.proc
        flog("stop_crawl: proc=%s poll=%s" % (proc, (proc.poll() if proc else None)))
        if proc is None or proc.poll() is not None:
            return
        self.set_status("stopping")
        self.append_log_line("warning", "Sending SIGTERM to crawler process  ·  正在停止...")
        self.safe_update("stop:term")
        try:
            await self._terminate_process_group(proc)
        except Exception as exc:  # pragma: no cover - defensive
            self.append_log_line("error", f"Error stopping crawler: {exc}")
        finally:
            if self.state.reader_task and not self.state.reader_task.done():
                self.state.reader_task.cancel()
            self.state.proc = None
            self.set_status("idle")

    async def _terminate_process_group(self, proc: subprocess.Popen) -> None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            proc.send_signal(signal.SIGTERM)
        for _ in range(30):
            if proc.poll() is not None:
                return
            await asyncio.sleep(0.5)
        self.append_log_line("warning", "Process not responding, sending SIGKILL  ·  强制结束")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    async def tick_timer(self, elapsed_chip: ft.Control) -> None:
        while True:
            await asyncio.sleep(1.0)
            if self.state.status == "running" and self.state.started_at:
                elapsed = int(time.time() - self.state.started_at)
                minutes, seconds = divmod(elapsed, 60)
                elapsed_chip.content.controls[1].value = f"{minutes:02d}:{seconds:02d}"
                self.safe_update("timer")

    async def qr_watcher(self) -> None:
        last_mtime = 0.0
        qr_path = DATA_DIR / "login_qrcode.png"
        while True:
            try:
                if self.state.running and qr_path.exists():
                    mtime = qr_path.stat().st_mtime
                    if mtime != last_mtime:
                        last_mtime = mtime
                        self.qr_image.src_base64 = base64.b64encode(qr_path.read_bytes()).decode()
                        self.qr_image.visible = True
                        self.page.update()
                elif not self.state.running and self.qr_image.visible:
                    self.qr_image.visible = False
                    self.page.update()
            except Exception:
                pass
            await asyncio.sleep(1.5)

    async def data_refresher(self) -> None:
        while True:
            try:
                if getattr(self.state, "running", False):
                    self.refresh_data()
            except Exception as exc:  # noqa
                flog("data_refresher exc: %s" % exc)
            await asyncio.sleep(4)
