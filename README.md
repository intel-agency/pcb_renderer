# PCB Renderer

> **Quilter Backend Engineer Code Challenge** — Parse ECAD JSON, validate board data, render to SVG/PNG/PDF.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-20%20passed-brightgreen.svg)](#testing)

A CLI tool that parses ECAD JSON board files, validates against **18 semantic rules**, and renders publication-quality SVG/PNG/PDF output using Matplotlib. Includes an optional **LLM plugin** for natural-language error explanations and design analysis.

---

## ⚡ Reviewer Quick Start (< 5 minutes)

Clone, install, render, and verify—ready for review:

```bash
# Clone the repository
git clone https://github.com/intel-agency/pcb-renderer.git
cd pcb-renderer

# Install all dependencies (Python 3.11+ required)
uv sync --all-extras

# Render a sample board and open it
uv run pcb-render boards/board_alpha.json -o out/board.svg --open

# Run the test suite
uv run pytest --cov
```

**Windows PowerShell:**
```powershell
git clone https://github.com/intel-agency/pcb-renderer.git
cd pcb-renderer
uv sync --all-extras
uv run pcb-render boards/board_alpha.json -o out/board.svg --open
uv run pytest --cov
```

---

## 📦 Installation

### Option 1: Clone + uv (recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. Install it first, then:

```bash
git clone https://github.com/intel-agency/pcb-renderer.git
cd pcb-renderer
uv sync --all-extras   # installs core + dev tools + LLM plugin
```

### Option 2: pip install from GitHub

```bash
pip install git+https://github.com/intel-agency/pcb-renderer.git
```

### Extras

| Extra | Contents | Command |
|-------|----------|---------|
| `dev` | pytest, ruff, basedpyright | `uv sync --extra dev` |
| `llm` | OpenAI client, Typer CLI | `uv sync --extra llm` |
| `full` | All of the above | `uv sync --extra full` |

Use `--all-extras` to install everything at once.

---

## 🚀 Running

### Basic rendering

```bash
# Linux/macOS (bash/zsh)
uv run pcb-render boards/board.json -o out/board.svg
uv run pcb-render boards/board.json -o out/board.png --format png
uv run pcb-render boards/board.json -o out/board.pdf --format pdf

# Windows PowerShell
uv run pcb-render boards\board.json -o out\board.svg
```

### Key CLI flags

| Flag | Description |
|------|-------------|
| `--open` | Opens the rendered output in your default viewer after rendering |
| `--permissive` | Renders the board even if validation errors are found (useful for debugging malformed boards) |
| `--export-json PATH` | Exports structured JSON with parse results, validation errors, and stats |
| `--format FORMAT` | Output format: `svg` (default), `png`, or `pdf` |

### Examples with flags

```bash
# Render an invalid board anyway (permissive mode)
uv run pcb-render boards/board_theta.json -o out/theta.svg --permissive

# Render and immediately view the result
uv run pcb-render boards/board_alpha.json -o out/alpha.svg --open

# Export machine-readable JSON for further analysis
uv run pcb-render boards/board.json -o out/board.svg --export-json out/board.export.json
```

---

## 🤖 LLM Plugin (Optional)

*"Usage of LLMs is encouraged"* — Per the challenge requirements, an LLM plugin provides natural-language explanations of validation errors and design suggestions.

### Quick setup

```bash
# Install with LLM support
uv sync --extra llm

# Set your API key (one of these)
export OPENAI_API_KEY="sk-..."           # Linux/macOS
$env:OPENAI_API_KEY = "sk-..."           # PowerShell
```

### Integrated CLI usage

```bash
uv run pcb-render boards/board_theta.json -o out/theta.svg --llm-explain --permissive
uv run pcb-render boards/board.json -o out/board.svg --llm-suggest-fixes
uv run pcb-render boards/board.json -o out/board.svg --llm-analyze
```

### Standalone plugin

```bash
uv run python -m llm_plugin explain out/board.export.json
uv run python -m llm_plugin suggest-fixes out/board.export.json
uv run python -m llm_plugin analyze out/board.export.json
```

### Environment variables

| Variable | Purpose |
|----------|---------|
| `LLM_BACKEND` | Backend: `template` (default), `http`, `openai`, `local` |
| `OPENAI_API_KEY` | API key for OpenAI-compatible endpoints |
| `OPENAI_BASE_URL` | Custom API endpoint (e.g., Azure OpenAI) |

See [llm_plugin/README.md](llm_plugin/README.md) for full details.

---

## 🔍 Invalid Boards & Detected Issues

The challenge includes 14+ intentionally malformed boards. The validator detects all of them:

| Board | Error | What's Wrong |
|-------|-------|--------------|
| `board_theta.json` | `NONEXISTENT_NET` | Via references net `NONEXISTENT_NET_XYZ` which doesn't exist |
| `board_kappa.json` | `MALFORMED_TRACE` | Trace has only 1 point (minimum 2 required) |
| `board_eta.json` | `NEGATIVE_WIDTH` | Trace width is `-100` (must be positive) |
| `board_xi.json` | `MALFORMED_STACKUP` | Layer stackup has empty `layers` array |
| `board_lambda.json` | `INVALID_VIA_GEOMETRY` | Via hole size (500) ≥ diameter (400) |

### Full validation coverage (18 rules)

**Geometry checks:** `MISSING_BOUNDARY`, `SELF_INTERSECTING_BOUNDARY`, `MALFORMED_COORDINATES`, `MALFORMED_TRACE`, `INVALID_ROTATION`, `INVALID_VIA_GEOMETRY`, `COMPONENT_OUTSIDE_BOUNDARY`, `NEGATIVE_WIDTH`

**Reference checks:** `DANGLING_TRACE`, `NONEXISTENT_NET`, `NONEXISTENT_LAYER`, `INVALID_PIN_REFERENCE`

**Structure checks:** `EMPTY_BOARD`, `MALFORMED_STACKUP`, `INVALID_UNIT_SPECIFICATION`

**Parse errors:** `MALFORMED_JSON`, `FILE_IO_ERROR`, `PARSE_ERROR`

---

## 🎨 Rendering Pipeline

### Design decisions

| Decision | Rationale |
|----------|-----------|
| **Headless Matplotlib** | `matplotlib.use("Agg")` before pyplot import ensures CI/Docker compatibility |
| **Deterministic SVG** | `svg.hashsalt = "pcb-renderer"` + `svg.fonttype = "none"` for reproducible golden tests |
| **Millimeters internally** | All coordinates normalized to mm; input accepts `MICRON` or `MILLIMETER` only |
| **Y-axis flip** | ECAD uses Y-up; SVG uses Y-down. Transform: $y_{svg} = H_{board} - y$ |

### Draw order (z-index)

1. **Boundary** — Board outline
2. **Pours** — Copper fill regions
3. **Traces** — Signal routing paths
4. **Vias** — Layer interconnects (outer ring + hole)
5. **Components** — Footprint outlines
6. **Reference designators** — Component labels (R1, C1, U1)
7. **Keepouts** — Restricted areas (hatched pattern)

---

## ✅ Testing

```bash
# Run all tests with coverage
uv run pytest --cov

# Linting
uv run ruff check .

# Type checking
uv run basedpyright
```

**Test coverage:** 20 tests, ~76% line coverage

| Test File | Coverage |
|-----------|----------|
| `test_models.py` | Pydantic models, NaN rejection, rotation bounds |
| `test_parse.py` | Coordinate parsing, unit normalization |
| `test_validate.py` | All 18 validation rules |
| `test_transform.py` | ECAD↔SVG roundtrip, component rotation |
| `test_render.py` | Smoke test rendering |
| `test_golden_render.py` | Deterministic SVG comparison |
| `test_export_json.py` | Export payload structure |
| `test_llm_plugin.py` | Plugin CLI with template backend |
| `test_boards.py` | Integration tests across sample boards |

---

## 📁 Repository Structure

```
pcb_renderer/       # Core package
├── cli.py          # Main entry point, argument parsing
├── parse.py        # JSON loading, unit normalization
├── validate.py     # 18 validation rules
├── transform.py    # Coordinate transforms (ECAD → SVG)
├── render.py       # Matplotlib rendering engine
├── models.py       # Pydantic data models
├── errors.py       # ErrorCode enum, ValidationError dataclass
├── geometry.py     # Point, Polygon, Polyline, Circle
└── stats.py        # Board analytics for export JSON

llm_plugin/         # Optional LLM integration
├── cli.py          # Typer CLI (explain, suggest-fixes, analyze)
├── client.py       # Backend selection (template/http/local)
├── prompts.py      # LLM prompt templates
└── context.py      # Context windowing (stub for large boards)

tests/              # Test suite
├── golden/         # Golden master SVGs for determinism tests
└── *.py            # Unit and integration tests

boards/             # Sample ECAD JSON files (valid + invalid)
docs/               # Architecture documentation
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
