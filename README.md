# PCB Renderer

> **Quilter Backend Engineer Code Challenge** — Parse ECAD JSON, validate board data, render to SVG/PNG/PDF.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-21%20passed-brightgreen.svg)](#testing)

A CLI tool that parses ECAD JSON board files, validates against **18 semantic rules**, and renders publication-quality SVG/PNG/PDF output using Matplotlib. Includes an optional **LLM plugin** for natural-language error explanations and design analysis.

---

## ⚡ Reviewer Quick Start (< 5 minutes)

Clone, install, render, and verify—ready for review (works on bash/zsh/PowerShell):

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

---

## 🎯 Quilter Challenge Requirements

This project was built to satisfy the **Quilter Backend Engineer Code Challenge**. Here's how it meets each requirement:

### ✅ Core Requirements Met

| Requirement | Implementation | Validation |
| --- | --- | --- |
| **Parse ECAD JSON** | `pcb_renderer/parse.py` normalizes units (MICRON/MILLIMETER → mm) and handles flexible coordinate formats | See [test_parse.py](tests/test_parse.py) |
| **Board Boundary** | Draws board outline from `boundary.coordinates` | Rendered in all example boards |
| **Components** | Draws component outlines, reference designators (R1, C1, U1), handles rotation | See [board_alpha.json](boards/board_alpha.json) rendering |
| **Traces** | Draws traces as paths with specified width, different colors per layer | Multi-layer boards like [board_6layer_hdi.json](boards/board_6layer_hdi.json) |
| **Vias** | Draws vias as circles at center positions with correct diameter | All valid boards include via rendering |
| **Keepout Regions** | Draws keepouts with distinct hatched pattern | See [test_circle_keepouts.py](tests/test_circle_keepouts.py) |
| **Error Detection** | **Returns validation errors for all 14+ invalid boards** (see table below) | [test_validate.py](tests/test_validate.py) validates all error codes |
| **Output Formats** | Renders as SVG (default), PNG, PDF | `--format` flag supports all three |
| **Code Quality** | 21 test files, ~76% coverage, type checking, linting | `uv run pytest --cov` |
| **Unit Testing** | Comprehensive test suite with golden master comparisons | [tests/](tests/) directory |
| **Code Comments** | Docstrings, inline comments, architecture docs | Throughout codebase + [AGENTS.md](AGENTS.md) |
| **LLM Usage** | Optional LLM plugin for natural-language error explanations | [llm_plugin/](llm_plugin/) with OpenAI integration |
| **Quick Review** | **< 5 minute setup**, clear docs, instant rendering | See "Reviewer Quick Start" above |

### 🔍 Invalid Board Detection (14+ Boards)

All **14 intentionally malformed boards** from the challenge are correctly detected:

| Board | Error Code | Detection |
| --- | --- | --- |
| `board_theta.json` | `NONEXISTENT_NET` | ✅ Via references non-existent net |
| `board_kappa.json` | `MALFORMED_TRACE` | ✅ Trace has < 2 points |
| `board_eta.json` | `NEGATIVE_WIDTH` | ✅ Negative trace width |
| `board_xi.json` | `MALFORMED_STACKUP` | ✅ Empty layer stackup |
| `board_lambda.json` | `INVALID_VIA_GEOMETRY` | ✅ Via hole ≥ diameter |
| `board_mu.json` | `DANGLING_TRACE` | ✅ Trace references non-existent net |
| `board_nu.json` | `SELF_INTERSECTING_BOUNDARY` | ✅ Self-intersecting boundary |
| `board_omicron.json` | `COMPONENT_OUTSIDE_BOUNDARY` | ✅ Component outside board |
| `board_pi.json` | `INVALID_ROTATION` | ✅ Component rotation > 360° |
| `board_rho.json` | `NONEXISTENT_LAYER` | ✅ Trace references invalid layer |
| `board_sigma.json` | `INVALID_PIN_REFERENCE` | ✅ Pin references wrong component |
| `board_tau.json` | `MISSING_BOUNDARY` | ✅ No boundary polygon |
| `board_zeta.json` | `EMPTY_BOARD` | ✅ No components/traces/vias |
| `board_iota.json` | `MALFORMED_COORDINATES` | ✅ Invalid coordinate format |

**Validation is comprehensive** (18 total error codes) — see [pcb_renderer/errors.py](pcb_renderer/errors.py) for all codes.

### 🚀 Reviewer Quick Validation

Verify the implementation in < 5 minutes:

```bash
# 1. Render a valid board
uv run pcb-render boards/board_alpha.json -o out/alpha.svg --open

# 2. Render an invalid board (permissive mode shows errors)
uv run pcb-render boards/board_theta.json -o out/theta.svg --permissive

# 3. Run validation tests (confirms all 14+ invalid boards detected)
uv run pytest tests/test_validate.py -v

# 4. View all test results
uv run pytest --cov
```

---

## 📦 Installation

### Option 1: Clone + uv (recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager.

**Install uv first:**

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip/pipx
pip install uv
```

**Then clone and setup:**

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
| --- | --- | --- |
| `dev` | pytest, ruff, basedpyright | `uv sync --extra dev` |
| `llm` | OpenAI client, Typer CLI | `uv sync --extra llm` |
| `full` | All of the above | `uv sync --extra full` |

Use `--all-extras` to install everything at once.

---

## 🚀 Running

### Basic rendering

```bash
# Works on bash/zsh/PowerShell (use forward slashes in PowerShell)
uv run pcb-render boards/board.json -o out/board.svg
uv run pcb-render boards/board.json -o out/board.png --format png
uv run pcb-render boards/board.json -o out/board.pdf --format pdf
```

### Key CLI flags

| Flag | Description |
| --- | --- |
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
# Project-specific (recommended):
export PCBR_OPENAI_API_KEY="sk-..."           # Linux/macOS
$env:PCBR_OPENAI_API_KEY = "sk-..."           # PowerShell

# Or standard OPENAI_* (picked up automatically):
export OPENAI_API_KEY="sk-..."                # Linux/macOS
$env:OPENAI_API_KEY = "sk-..."                # PowerShell
```

### Integrated CLI usage

```bash
uv run pcb-render boards/board_theta.json -o out/theta.svg --llm-explain --permissive
uv run pcb-render boards/board.json -o out/board.svg --llm-suggest-fixes
uv run pcb-render boards/board.json -o out/board.svg --llm-analyze
```

### Environment variables

Create a `.env` file in the `llm_plugin/` directory using the provided `.env.example` template:

```bash
# Copy the example file
cp llm_plugin/.env.example llm_plugin/.env

# Edit with your API credentials
# For ChatGPT/OpenAI:
PCBR_LLM_BACKEND=http
PCBR_OPENAI_API_KEY=sk-your-actual-key-here

# For Z.AI GLM (Zhipu AI):
PCBR_LLM_BACKEND=http
PCBR_OPENAI_API_KEY=your-zhipu-api-key
PCBR_OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
PCBR_OPENAI_MODEL=glm-4
```

Alternatively, set environment variables directly:

| Variable | Purpose | Precedence |
| --- | --- | --- |
| `PCBR_LLM_BACKEND` / `LLM_BACKEND` | Backend: `template` (default), `http`, `openai`, `local` | PCBR_* overrides |
| `PCBR_OPENAI_API_KEY` / `OPENAI_API_KEY` | API key for OpenAI-compatible endpoints | PCBR_* overrides |
| `PCBR_OPENAI_BASE_URL` / `OPENAI_BASE_URL` | Custom API endpoint (e.g., Azure OpenAI, Z.AI GLM) | PCBR_* overrides |
| `PCBR_OPENAI_MODEL` / `OPENAI_MODEL` | Model name (default: `gpt-4o-mini`) | PCBR_* overrides |

See [llm_plugin/README.md](llm_plugin/README.md) for full details.

---

## � Additional Validation Details

### Full validation coverage (18 rules)

**Geometry checks:** `MISSING_BOUNDARY`, `SELF_INTERSECTING_BOUNDARY`, `MALFORMED_COORDINATES`, `MALFORMED_TRACE`, `INVALID_ROTATION`, `INVALID_VIA_GEOMETRY`, `COMPONENT_OUTSIDE_BOUNDARY`, `NEGATIVE_WIDTH`

**Reference checks:** `DANGLING_TRACE`, `NONEXISTENT_NET`, `NONEXISTENT_LAYER`, `INVALID_PIN_REFERENCE`

**Structure checks:** `EMPTY_BOARD`, `MALFORMED_STACKUP`, `INVALID_UNIT_SPECIFICATION`

**Parse errors:** `MALFORMED_JSON`, `FILE_IO_ERROR`, `PARSE_ERROR`

---

## 🎨 Rendering Pipeline

### Design decisions

| Decision | Rationale |
| --- | --- |
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

## Testing

```bash
# Run all tests with coverage
uv run pytest --cov

# Linting
uv run ruff check .

# Type checking
uv run basedpyright
```

### Platform Smoke Tests

Platform smoke tests validate the application across different environments:

```bash
# Linux (Alpine) - Docker
docker build -t pcb-renderer-test:linux-alpine -f Dockerfile.test.linux .
docker run --rm pcb-renderer-test:linux-alpine

# Linux (Debian/Ubuntu) - Docker
docker build -t pcb-renderer-test:linux-debian -f Dockerfile.test.debian .
docker run --rm pcb-renderer-test:linux-debian

# Windows - Docker (requires Docker Desktop with Windows containers)
docker build -t pcb-renderer-test:windows -f Dockerfile.test.windows .
docker run --rm pcb-renderer-test:windows

# macOS - Native (no Docker support)
# Follow the Quick Start steps at the top of this README
```

See [docs/DOCKER_TESTS.md](docs/DOCKER_TESTS.md) for details.

## Build

```bash
# Build a wheel and sdist with uv
# Note: Project uses Hatchling backend with flat layout
# Copy .env.example to .env (sets UV_NO_BUILD_OPTIMIZATION=true)
# or use --force-pep517 flag to bypass uv's internal build optimization
cp .env.example .env  # Optional: configure uv build backend
uv build --force-pep517
```

**Test coverage:** 21 tests, ~76% line coverage

| Test File | Coverage |
| --- | --- |
| `test_models.py` | Pydantic models, NaN rejection, rotation bounds |
| `test_parse.py` | Coordinate parsing, unit normalization |
| `test_validate.py` | All 18 validation rules |
| `test_transform.py` | ECAD↔SVG roundtrip, component rotation |
| `test_render.py` | Smoke test rendering |
| `test_golden_render.py` | Deterministic SVG comparison |
| `test_export_json.py` | Export payload structure |
| `test_llm_plugin.py` | Plugin CLI with template backend |
| `test_cli_open.py` | Cross-platform file opening |
| `test_boards.py` | Integration tests across sample boards |

---

## 📁 Repository Structure

```text
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

AGPL-3.0 License. See [LICENSE](LICENSE) for details.
