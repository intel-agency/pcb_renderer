# PCB Renderer

CLI tool that parses ECAD JSON boards, validates against 18 rules, and renders SVG/PNG/PDF via Matplotlib. Optional LLM plugin provides explanations and design analysis.

## Quickstart

```bash
uv sync --all-extras
uv run pcb-render boards/board.json -o out/board.svg
```

## Install & setup

```bash
uv sync
# dev tools
uv sync --extra dev
# LLM plugin
uv sync --extra llm
# everything
uv sync --all-extras
```

## Running

```bash
uv run pcb-render boards/board.json -o out/board.svg
uv run pcb-render boards/board.json -o out/board.png --format png
uv run pcb-render boards/board_theta.json -o out/theta.svg --permissive
uv run pcb-render boards/board.json -o out/board.svg --export-json out/board.export.json
```

## LLM plugin (optional) + quick setup

- Backend selection via `LLM_BACKEND` (`template` default, `http`/`openai` for API).
- API key precedence: `OPENAI_API_KEY` → `PCB_RENDERER_LLM_API_KEY`.
- Base URL precedence: `OPENAI_BASE_URL` → `LLM_API_BASE` → `PCB_RENDERER_LLM_BASE_URL`.

```bash
uv sync --extra llm
uv run pcb-render boards/board.json -o out/board.svg --llm-explain
uv run python -m llm_plugin explain out/board.export.json
```

## Rendering decisions/assumptions

- Headless rendering via `matplotlib.use("Agg")` before `pyplot` import.
- SVG determinism: `svg.hashsalt = "pcb-renderer"`, `svg.fonttype = "none"`.
- Internal units are millimeters; input supports `MICRON` or `MILLIMETER` only.
- Coordinate transform: ECAD Y-up to SVG Y-down ($y_{svg} = H_{board} - y$).
- Draw order: boundary → pours → traces → vias → components → refdes text → keepouts.

## Invalid board issues list

- `MISSING_BOUNDARY`
- `SELF_INTERSECTING_BOUNDARY`
- `MALFORMED_COORDINATES`
- `MALFORMED_TRACE`
- `INVALID_ROTATION`
- `INVALID_VIA_GEOMETRY`
- `COMPONENT_OUTSIDE_BOUNDARY`
- `NEGATIVE_WIDTH`
- `DANGLING_TRACE`
- `NONEXISTENT_NET`
- `NONEXISTENT_LAYER`
- `INVALID_PIN_REFERENCE`
- `EMPTY_BOARD`
- `MALFORMED_STACKUP`
- `INVALID_UNIT_SPECIFICATION`
- `MALFORMED_JSON`
- `FILE_IO_ERROR`
- `PARSE_ERROR`

## Testing

```bash
uv run pytest --cov
uv run ruff check .
uv run basedpyright
```

## Repo map

- `pcb_renderer/` core package (parse, validate, transform, render, stats, CLI)
- `llm_plugin/` optional LLM plugin (Typer CLI)
- `tests/` test suite + golden SVGs
- `boards/` sample board JSON fixtures
- `docs/` architecture and plans
