# PCB Renderer

CLI tool to parse, validate, and render ECAD JSON boards to SVG/PNG/PDF with structured errors.

## Installation

```bash
uv sync
```

## Usage

```bash
uv run pcb-render boards/board.json -o out/board.svg
uv run pcb-render boards/board_beta.json -o out/beta.png --format png --quiet
uv run pcb-render boards/board_theta.json -o out/theta.svg --permissive
uv run pcb-render boards/board_alpha.json -o out/alpha.svg --llm-explain --export-json out/alpha.json
```

## Plugins

- LLM plugin (optional): install extras with `uv sync --extra llm`, then use `--llm-explain`, `--llm-suggest-fixes`, or `--llm-analyze` flags. The core CLI auto-detects the plugin and forwards the export JSON to it. See `README.plugins` and `llm_plugin/README.md` for details.

## Error Codes

- MISSING_BOUNDARY, MALFORMED_COORDINATES, INVALID_ROTATION, DANGLING_TRACE, NEGATIVE_WIDTH,
  EMPTY_BOARD, INVALID_VIA_GEOMETRY, NONEXISTENT_LAYER, NONEXISTENT_NET,
  SELF_INTERSECTING_BOUNDARY, COMPONENT_OUTSIDE_BOUNDARY, INVALID_PIN_REFERENCE,
  MALFORMED_STACKUP, INVALID_UNIT_SPECIFICATION, MALFORMED_TRACE

## Testing

```bash
uv run pytest --cov
uv run ruff check .
uv run pyright
```

## Future Work

- Gerber export, interactive viewer, performance tuning.
