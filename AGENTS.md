# Repository Agent Rules

## GUI structure
- Keep `mediacrawler_gui.py` as a compatibility entry point only. Target: 80 lines or fewer.
- Put desktop GUI implementation under `mediacrawler_gui_app/`.
- Keep Python files focused on one concern and target 300 lines or fewer. App/page assembly may reach 400 lines only when splitting would make control flow harder to follow.
- Keep functions around 50 lines or fewer. Extract helpers once validation, rendering, and process lifecycle logic start mixing.

## GUI boundaries
- The desktop GUI must not import crawler internals such as `config`, `media_platform.*`, or `cmd_arg.parse_cmd`.
- Launch the crawler through `main.py` as a subprocess, preserving the CLI contract used by the existing crawler.
- Keep `uv run python mediacrawler_gui.py` and `./run.sh` working as stable launch paths.

## Verification
- For GUI changes, run:
  - `uv run pytest tests/test_mediacrawler_gui.py -q`
  - `uv run python -m py_compile mediacrawler_gui.py mediacrawler_gui_app/*.py`
- For interaction-sensitive GUI changes, also smoke test with `./run.sh`.
- Keep `requirements.txt`, `pyproject.toml`, and `uv.lock` aligned for GUI/runtime dependencies.
