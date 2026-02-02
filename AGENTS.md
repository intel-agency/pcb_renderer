# AGENTS.md - AI Agent Guide for PCB Renderer

## Project Overview

PCB Renderer is a CLI tool that parses ECAD JSON board files, validates them against 18 error rules, and renders them to SVG/PNG/PDF using Matplotlib. It includes an optional LLM plugin for natural-language error explanations and design analysis.

**Repository Structure:**
```
pcb_renderer/       # Core package
llm_plugin/         # Optional LLM plugin (Typer CLI)
tests/              # Test suite with fixtures and golden masters
boards/             # Sample board JSON files
docs/               # Architecture documentation
```

---

## Architecture Deep Dive

### Data Flow Pipeline

```
Input JSON → parse.py → normalize_units() → Pydantic models → validate.py → transform.py → render.py → Output
```

**Key Modules:**

| Module | Purpose | Key Functions/Classes |
|--------|---------|----------------------|
| `parse.py` | JSON loading, unit normalization | `load_board()`, `normalize_units()`, `parse_coordinates()` |
| `models.py` | Pydantic data models | `Board`, `Component`, `Trace`, `Via`, `Keepout`, `Net`, `Layer` |
| `validate.py` | 14 validation rules | `validate_board()`, `CHECKS_RUN` constant |
| `transform.py` | Coordinate transforms | `ecad_to_svg()`, `compute_component_transform()` |
| `render.py` | Matplotlib rendering | `render_board()`, deterministic z-order drawing |
| `errors.py` | Structured errors | `ErrorCode` enum, `ValidationError` dataclass |
| `geometry.py` | Math primitives | `Point`, `Polygon`, `Polyline`, `Circle` |
| `stats.py` | Board analytics | `compute_stats()` for export JSON |
| `cli.py` | Main entry point | `main()`, `_build_export_payload()`, plugin integration |

### Coordinate Systems

- **ECAD**: Y-up (0,0 at bottom-left, Y increases upward)
- **SVG**: Y-down (0,0 at top-left, Y increases downward)
- **Transform**: `ecad_to_svg(y) = board_height - y`

### Unit Handling

Only two units supported:
- `MICRON` → multiply by 0.001 to get mm
- `MILLIMETER` → multiply by 1.0 (no change)

The parser normalizes everything to millimeters internally.

---

## Error System

### ErrorCode Enum (18 codes)

**Boundary/Geometry:**
- `MISSING_BOUNDARY` - Board has no boundary polygon
- `SELF_INTERSECTING_BOUNDARY` - Boundary polygon crosses itself
- `MALFORMED_COORDINATES` - Invalid coordinate format
- `MALFORMED_TRACE` - Trace has < 2 points
- `INVALID_ROTATION` - Component rotation outside 0-360
- `INVALID_VIA_GEOMETRY` - hole_size >= diameter
- `COMPONENT_OUTSIDE_BOUNDARY` - Component center outside board bounds
- `NEGATIVE_WIDTH` - Trace width <= 0

**References:**
- `DANGLING_TRACE` - Trace references non-existent net
- `NONEXISTENT_NET` - Pin references unknown net
- `NONEXISTENT_LAYER` - Trace/via references unknown layer
- `INVALID_PIN_REFERENCE` - Pin's comp_name doesn't match its component

**Structure:**
- `EMPTY_BOARD` - No components, traces, or vias
- `MALFORMED_STACKUP` - Layer index gaps or duplicates
- `INVALID_UNIT_SPECIFICATION` - Unit not MICRON/MILLIMETER

**Parse Errors:**
- `MALFORMED_JSON` - Invalid JSON syntax
- `FILE_IO_ERROR` - File read failure
- `PARSE_ERROR` - General parse failure

### ValidationError Dataclass

```python
@dataclass
class ValidationError:
    code: ErrorCode           # Error type
    severity: Severity        # ERROR, WARNING, or INFO
    message: str              # Human-readable description
    json_path: str            # JSONPath to problematic field
    context: Dict[str, Any]   # Optional metadata (trace_id, available_nets, etc.)
```

**Context Fields Used:**
- `trace_id`, `point_count` - For trace errors
- `referenced_net`, `available_nets` - For net reference errors
- `referenced_layer`, `available_layers` - For layer errors
- `component`, `position` - For component placement errors
- `rotation` - For rotation errors
- `hole_size`, `diameter` - For via geometry errors
- `via_id`, `start_layer`, `end_layer` - For via span errors
- `pin` - For pin errors
- `indices` - For stackup errors

---

## Plugin System

### LLM Plugin Architecture

**Registration Flow:**
1. Core CLI imports `llm_plugin` dynamically via `_maybe_register_plugin()`
2. If present, calls `llm_plugin.register_cli(parser)` to add `--llm-*` flags
3. On execution, `_invoke_llm_plugin()` calls `llm_plugin.run_from_core(export_path, modes)`

**Backend Selection (via `LLM_BACKEND` env var):**
- `template` (default) - Returns formatted prompt for testing
- `local` - Placeholder stub for on-device models
- `http`/`openai` - OpenAI-compatible API (requires `OPENAI_API_KEY`)

**Environment Variables:**
- `LLM_BACKEND` - Backend selector
- `OPENAI_API_KEY` - Required for HTTP backend (fallback: `PCB_RENDERER_LLM_API_KEY`)
- `OPENAI_BASE_URL`/`LLM_API_BASE` - Optional API endpoint override (fallback: `PCB_RENDERER_LLM_BASE_URL`)
- `OPENAI_MODEL` - Default: `gpt-4o-mini`

**Note on prefixed variables:** Use `PCB_RENDERER_LLM_API_KEY` and `PCB_RENDERER_LLM_BASE_URL` to avoid environment variable collisions with other tools that use OpenAI APIs.

### Export JSON Schema

When `--export-json` or LLM flags are used, core CLI outputs:

```json
{
  "schema_version": "1.0",
  "input_file": "path/to/board.json",
  "parse_result": {
    "success": true,
    "errors": [...],
    "board": {...},  // Normalized board JSON
    "stats": {
      "board_dimensions_mm": [width, height],
      "board_area_mm2": area,
      "num_components": N,
      "num_traces": N,
      "num_vias": N,
      "num_nets": N,
      "layer_count": N,
      "component_density": N,
      "trace_length_total_mm": N,
      "total_thickness_um": N,
      "via_aspect_ratio": N
    }
  },
  "validation_result": {
    "valid": true,
    "error_count": 0,
    "warning_count": 0,
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

---

## Development Workflows

### Setup

```bash
# Core only
uv sync

# With dev tools
uv sync --extra dev

# With LLM plugin
uv sync --extra llm

# Everything
uv sync --all-extras
```

### Validation Commands (MUST RUN BEFORE COMPLETION)

```bash
# Run all tests with coverage
uv run pytest --cov

# Linting
uv run ruff check .

# Type checking
uv run basedpyright
```

### CLI Usage Patterns

```bash
# Basic render
uv run pcb-render boards/board.json -o out/board.svg

# With specific format
uv run pcb-render boards/board.json -o out/board.png --format png

# Permissive mode (render despite validation errors)
uv run pcb-render boards/board_theta.json -o out/theta.svg --permissive

# Export JSON for debugging
uv run pcb-render boards/board.json -o out/board.svg --export-json out/board.json

# LLM plugin (requires --extra llm)
uv run pcb-render boards/board.json -o out/board.svg --llm-explain
uv run pcb-render boards/board.json -o out/board.svg --llm-suggest-fixes --llm-analyze

# Standalone LLM plugin
uv run llm_plugin explain export.json
uv run llm_plugin suggest-fixes export.json
uv run llm_plugin analyze export.json
```

---

## Testing Strategy

### Test Organization

| Test File | Coverage |
|-----------|----------|
| `test_models.py` | Pydantic models, Point NaN rejection, rotation bounds |
| `test_parse.py` | Coordinate parsing, unit normalization, invalid units |
| `test_validate.py` | All validation rules, specific board fixtures |
| `test_transform.py` | ECAD↔SVG roundtrip, component rotation |
| `test_render.py` | Smoke test rendering |
| `test_golden_render.py` | Deterministic SVG comparison |
| `test_export_json.py` | Export payload structure, stats computation |
| `test_llm_plugin.py` | Plugin CLI with template backend |
| `test_cli_open.py` | Cross-platform file opening |
| `test_boards.py` | Integration tests over all sample boards |

### Golden Master Tests

Rendering tests use deterministic SVG output by setting:
```python
matplotlib.rcParams["svg.hashsalt"] = "pcb-renderer"
matplotlib.rcParams["svg.fonttype"] = "none"
```

Golden files are stored in `tests/golden/` and compared using normalized SVG strings.

---

## Common Patterns & Gotchas

### Headless Rendering

Matplotlib is forced to use `Agg` backend in `render.py`:
```python
import matplotlib
matplotlib.use("Agg")  # Must be before pyplot import
import matplotlib.pyplot as plt
```

This prevents Tkinter issues in CI/docker environments.

### Pydantic Model Configuration

All models use:
```python
model_config = {"extra": "ignore", "populate_by_name": True}
```

- `extra="ignore"` - Allows unknown fields (validation deferred to `validate.py`)
- `populate_by_name=True` - Supports field aliases like `class` → `net_class`

### Boolean Type Check in Scaling

In `normalize_units()`, there's a guard against bool→float conversion:
```python
if isinstance(value, bool):
    return value
```

This prevents `True` from becoming `1.0`.

### Optional Boundary

`Board.boundary` is `Optional[Polygon]` to allow validation to report `MISSING_BOUNDARY` instead of failing at parse time.

### Trace Polyline Flexibility

`Polyline` minimum length constraint is relaxed to allow parsing malformed traces; validation catches them later.

### Stackup Type

`Board.stackup` is `Dict[str, Any]` for flexibility, not a strict Pydantic model.

---

## CI/CD Pipeline

GitHub Actions (`.github/workflows/ci.yml`):
- Matrix: Windows, macOS, Linux × Python 3.11, 3.12
- Steps: checkout → setup uv → sync --all-extras → pytest → ruff → basedpyright

Docker support:
- `Dockerfile` based on `python:3.11-slim` with freetype
- Headless-safe (uses Agg backend)

---

## File Reference Quick Guide

| When you need to... | Look in... |
|---------------------|------------|
| Add new error code | `errors.py` → add to `ErrorCode`, use in `validate.py` |
| Add validation rule | `validate.py` → append to `validate_board()`, update `CHECKS_RUN` |
| Add board field | `models.py` → add to `Board`, handle in `parse.py` if needed |
| Change rendering | `render.py` → z-order is: boundary, pours, traces, vias, components, refdes, keepouts |
| Add CLI flag | `cli.py` → `create_parser()`, then use in `main()` |
| Add LLM feature | `llm_plugin/cli.py`, `prompts.py`, `client.py` |
| Add test fixture | `tests/conftest.py` or `boards/` for JSON samples |

---

## Performance Considerations

- Rendering large boards: Matplotlib may be slow for >10k traces
- Export JSON: Can be large for complex boards (context filtering in `llm_plugin/context.py` is a stub for future windowing)
- Via aspect ratio: Computed only if `total_thickness` present in stackup

---

## Future Extension Points

- **Gerber export**: Add `gerber.py` with CAM semantics
- **Interactive viewer**: WebGL-based renderer using export JSON
- **Additional LLM backends**: Extend `llm_plugin/client.py` with local ONNX/CoreML
- **More error context**: Add richer metadata to `ValidationError.context`
- **Incremental validation**: Cache validation results by board hash
