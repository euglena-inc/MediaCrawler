import asyncio
import contextlib
import os

import pytest

import mediacrawler_gui as gui
import mediacrawler_gui_app.results as results_mod
from mediacrawler_gui_app.lifecycle import CrawlerLifecycle


def test_app_state_running_tracks_status() -> None:
    state = gui.AppState()

    assert state.running is False

    state.status = "running"

    assert state.running is True


def test_decode_process_output_replaces_invalid_utf8() -> None:
    text = gui.decode_process_output(b"\xffcrawler output\n")

    assert text == "\ufffdcrawler output\n"


def test_classify_crawl_completion_keeps_unknown_exit_as_error() -> None:
    status, level, message = gui.classify_crawl_completion(None, "running")

    assert status == "error"
    assert level == "error"
    assert "exit status" in message


def test_scan_data_files_returns_newest_supported_files_first(tmp_path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    jsonl_dir = data_root / "xhs" / "jsonl"
    json_dir = data_root / "xhs" / "json"
    csv_dir = data_root / "xhs" / "csv"
    jsonl_dir.mkdir(parents=True)
    json_dir.mkdir(parents=True)
    csv_dir.mkdir(parents=True)

    old_jsonl = jsonl_dir / "old.jsonl"
    old_jsonl.write_text('{"id": 1}\n{"id": 2}\n', encoding="utf-8")
    newest_json = json_dir / "newest.json"
    newest_json.write_text('[{"id": 1}, {"id": 2}, {"id": 3}]', encoding="utf-8")
    middle_csv = csv_dir / "middle.csv"
    middle_csv.write_text("id\n1\n", encoding="utf-8")

    for path, mtime in ((old_jsonl, 100.0), (middle_csv, 200.0), (newest_json, 300.0)):
        os.utime(path, (mtime, mtime))

    monkeypatch.setattr(results_mod, "DATA_DIR", data_root)

    files = gui.scan_data_files("xhs")

    assert [item["name"] for item in files] == ["newest.json", "middle.csv", "old.jsonl"]
    assert files[0]["records"] == 3
    assert files[1]["records"] is None
    assert files[2]["records"] == 2


@pytest.mark.asyncio
async def test_stop_crawl_keeps_stopping_status_until_reader_finishes() -> None:
    class FakeProc:
        pid = 12345

        def poll(self):
            return None

    state = gui.AppState(proc=FakeProc())  # type: ignore[arg-type]
    reader_task = asyncio.create_task(asyncio.sleep(60))
    state.reader_task = reader_task
    logs: list[tuple[str, str]] = []

    lifecycle = CrawlerLifecycle(
        page=None,  # type: ignore[arg-type]
        state=state,
        cfg=gui.CrawlConfig(),
        log_view=None,  # type: ignore[arg-type]
        qr_image=None,  # type: ignore[arg-type]
        append_log_line=lambda level, text: logs.append((level, text)),
        set_status=lambda status: setattr(state, "status", status),
        safe_update=lambda reason: None,
        refresh_data=lambda: None,
    )

    async def terminate_immediately(proc) -> None:
        return None

    lifecycle._terminate_process_group = terminate_immediately  # type: ignore[method-assign]

    try:
        await lifecycle.stop_crawl()

        assert state.status == "stopping"
        assert state.proc is None
        assert any("正在停止" in text for _, text in logs)
    finally:
        reader_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reader_task
