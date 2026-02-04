# Copilot Instructions for PCB Renderer

PCB Renderer is a CLI tool that parses ECAD JSON board files, validates them against 18 semantic rules, and renders them to SVG/PNG/PDF using Matplotlib. It includes an optional LLM plugin for natural-language error explanations.

## Build, Test, and Lint Commands

### Setup

```bash
# Install all dependencies (Python 3.11+ required)
uv sync --all-extras

# Core only (no dev tools or LLM plugin)
uv sync

# With specific extras
uv sync --extra dev    # pytest, ruff, basedpyright
uv sync --extra llm    # OpenAI client, Typer CLI
```

### Run the CLI

```bash
# Basic render
uv run pcb-render boards/board.json -o out/board.svg

# Open output after rendering
uv run pcb-render boards/board_alpha.json -o out/alpha.svg --open

# Permissive mode (render despite validation errors)
uv run pcb-render boards/board_theta.json -o out/theta.svg --permissive

# Export structured JSON
uv run pcb-render boards/board.json -o out/board.svg --export-json out/board.export.json

# With LLM features (requires --extra llm and API key)
uv run pcb-render boards/board.json -o out/board.svg --llm-explain
```

### Testing

```bash
# Run all tests with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_validate.py

# Run specific test function
uv run pytest tests/test_validate.py::test_board_theta_reports_nonexistent_net

# Run with verbose output
uv run pytest -v

# Generate coverage report
uv run pytest --cov --cov-report=html
```

### Linting and Type Checking

```bash
# Lint with ruff
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Type check with basedpyright
uv run basedpyright
```

### Build

```bash
# Build wheel and sdist (.env configured for PEP 517)
uv build --force-pep517
```

### Dependency Management

```bash
# After editing pyproject.toml dependencies
uv lock                    # Regenerate uv.lock
uv sync --all-extras       # Resync environment
```

## Architecture Overview

### Data Flow Pipeline

```
Input JSON → parse.py → normalize_units() → Pydantic models → validate.py → transform.py → render.py → Output
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `cli.py` | Main entry point, argument parsing, plugin integration |
| `parse.py` | JSON loading, unit normalization (MICRON/MILLIMETER → mm) |
| `models.py` | Pydantic data models (Board, Component, Trace, Via, etc.) |
| `validate.py` | 18 validation rules, returns list of ValidationError |
| `transform.py` | Coordinate transforms (ECAD Y-up ↔ SVG Y-down) |
| `render.py` | Matplotlib rendering with deterministic SVG output |
| `errors.py` | ErrorCode enum (18 codes), ValidationError dataclass |
| `geometry.py` | Math primitives (Point, Polygon, Polyline, Circle) |
| `stats.py` | Board analytics for export JSON |

### Coordinate Systems

- **ECAD**: Y-up (0,0 at bottom-left, Y increases upward)
- **SVG**: Y-down (0,0 at top-left, Y increases downward)
- **Transform**: `ecad_to_svg(y) = board_height - y`

### Unit Handling

- Only `MICRON` and `MILLIMETER` are accepted at input
- Parser normalizes everything to millimeters internally via `normalize_units()`
- MICRON → multiply by 0.001 to get mm
- MILLIMETER → multiply by 1.0 (no change)

### Rendering Z-Order

Draw order (bottom to top):
1. Boundary (z=1)
2. Pours (z=2)
3. Traces (z=3)
4. Vias - outer ring (z=4)
5. Vias - hole / Components (z=5)
6. Reference designators (z=6)
7. Keepouts (z=7)

## Key Conventions

### Project Invariants (Must Preserve)

1. **Everything internal is millimeters**: Only `MICRON` and `MILLIMETER` accepted at input; parsing normalizes to mm
2. **Parsing is permissive; validation is authoritative**: Pydantic models use `extra="ignore"`; semantic checks live in `validate.py`
3. **Rendering must stay headless + deterministic**: 
   - Call `matplotlib.use("Agg")` **before** importing `matplotlib.pyplot`
   - Set `matplotlib.rcParams["svg.hashsalt"] = "pcb-renderer"`
   - Set `matplotlib.rcParams["svg.fonttype"] = "none"`
4. **Export JSON is a public contract**: The LLM plugin and tests consume `_build_export_payload()`
5. **Plugin is optional**: Core CLI must work without `llm_plugin` installed

### Error System (18 Validation Rules)

**Geometry checks:**
- `MISSING_BOUNDARY`, `SELF_INTERSECTING_BOUNDARY`, `MALFORMED_COORDINATES`, `MALFORMED_TRACE`, `INVALID_ROTATION`, `INVALID_VIA_GEOMETRY`, `COMPONENT_OUTSIDE_BOUNDARY`, `NEGATIVE_WIDTH`

**Reference checks:**
- `DANGLING_TRACE`, `NONEXISTENT_NET`, `NONEXISTENT_LAYER`, `INVALID_PIN_REFERENCE`

**Structure checks:**
- `EMPTY_BOARD`, `MALFORMED_STACKUP`, `INVALID_UNIT_SPECIFICATION`

**Parse errors:**
- `MALFORMED_JSON`, `FILE_IO_ERROR`, `PARSE_ERROR`

### ValidationError Structure

```python
@dataclass
class ValidationError:
    code: ErrorCode
    severity: Severity        # ERROR, WARNING, INFO
    message: str
    json_path: str            # JSONPath to problematic field
    context: Optional[Dict]   # Metadata (trace_id, available_nets, etc.)
```

### Adding New Validation Rules

1. Add/extend an `ErrorCode` in `pcb_renderer/errors.py`
2. Implement the rule in `pcb_renderer/validate.py` (return `ValidationError`, don't raise)
3. Include a stable `json_path` and small `context` payload
4. Add tests in `tests/test_validate.py`

### Golden Master Tests

Rendering tests use deterministic SVG output. If you intentionally change rendering:

1. Keep `svg.hashsalt = "pcb-renderer"` stable
2. Regenerate golden SVGs in `tests/golden/` in a deliberate step
3. Update `tests/test_golden_render.py` expectations

### Pydantic Model Configuration

All models use:
```python
model_config = {"extra": "ignore", "populate_by_name": True}
```

- `extra="ignore"` - Allows unknown fields (validation deferred to `validate.py`)
- `populate_by_name=True` - Supports field aliases (e.g., `class` → `net_class`)

### LLM Plugin Architecture

**Registration Flow:**
1. Core CLI imports `llm_plugin` dynamically via `_maybe_register_plugin()`
2. If present, calls `llm_plugin.register_cli(parser)` to add `--llm-*` flags
3. On execution, `_invoke_llm_plugin()` calls `llm_plugin.run_from_core(export_path, modes)`

**Backend Selection (via `LLM_BACKEND` env var):**
- `template` (default) - Returns formatted prompt for testing
- `http`/`openai` - OpenAI-compatible API (requires `OPENAI_API_KEY`)
- `local` - Placeholder for on-device models

**Environment Variable Precedence:**
- API key: `OPENAI_API_KEY` → `PCBR_OPENAI_API_KEY`
- Base URL: `OPENAI_BASE_URL` → `LLM_API_BASE` → `PCBR_OPENAI_BASE_URL`
- Backend: `LLM_BACKEND` → `PCBR_LLM_BACKEND`

Use `PCBR_*` prefixed variables to avoid collisions with other tools.

### Windows/PowerShell Notes

- PowerShell doesn't support `&&` chaining like bash; run commands separately or use `;`
- Always use `uv run ...` to ensure tools resolve from project environment
- Use Windows-style paths with backslashes in code: `D:\src\project\file.py`

## Common Patterns

### Headless Rendering

Always use Agg backend in `render.py`:
```python
import matplotlib
matplotlib.use("Agg")  # MUST be before pyplot import
import matplotlib.pyplot as plt
```

### Boolean Type Check in Scaling

In `normalize_units()`, guard against bool→float conversion:
```python
if isinstance(value, bool):
    return value  # Prevents True from becoming 1.0
```

### Optional Boundary

`Board.boundary` is `Optional[Polygon]` to allow validation to report `MISSING_BOUNDARY` instead of failing at parse time.

### Trace Polyline Flexibility

`Polyline` minimum length constraint is relaxed to allow parsing malformed traces; validation catches them later with `MALFORMED_TRACE`.

### Export JSON Schema

When `--export-json` is used, core CLI outputs:
```json
{
  "schema_version": "1.0",
  "input_file": "path/to/board.json",
  "parse_result": {
    "success": true,
    "errors": [...],
    "board": {...},
    "stats": {...}
  },
  "validation_result": {
    "valid": true,
    "errors": [...],
    "warnings": [],
    "checks_run": ["boundary", "references", "geometry", "stackup", "rotation", "pins"]
  },
  "render_result": {
    "success": true,
    "output_file": "out/board.svg",
    "format": "svg"
  }
}
```

## CI/CD

GitHub Actions runs on Windows, macOS, Linux with Python 3.11 and 3.12:
- Syncs with `uv sync --all-extras`
- Builds with `uv build --force-pep517`
- Tests with `uv run pytest --cov`
- Lints with `uv run ruff check .`
- Type checks with `uv run basedpyright`

## Quick File Reference

| Need to... | Look in... |
|------------|------------|
| Add error code | `errors.py` → add to `ErrorCode`, use in `validate.py` |
| Add validation rule | `validate.py` → append to `validate_board()`, update `CHECKS_RUN` |
| Add board field | `models.py` → add to `Board`, handle in `parse.py` if needed |
| Change rendering | `render.py` → z-order is fixed, adjust drawing functions |
| Add CLI flag | `cli.py` → `create_parser()`, use in `main()` |
| Add LLM feature | `llm_plugin/cli.py`, `prompts.py`, `client.py` |
| Add test fixture | `tests/conftest.py` or `boards/` for JSON samples |
