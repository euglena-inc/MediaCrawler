import mediacrawler_gui as gui


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
