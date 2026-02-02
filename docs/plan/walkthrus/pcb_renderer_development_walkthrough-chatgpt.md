# PCB Renderer: End-to-End Development Walkthrough (Follow-Along Guide)

This is a **development walkthrough you can follow from an empty repo to a finished submission**, aligned to the **8 phases** and acceptance criteria in the v2 docs, plus the optional LLM-plugin export contract. The intended core pipeline is:

**Parse → Validate → Transform → Render → Export (SVG/PNG/PDF) → CLI exit codes**【71:7†architecture_guide_v2.md†L16-L47】【67:3†Application Implementation Specification_ PCB Renderer.md†L59-L61】.

---

## 0) Repo bootstrap (project skeleton + tooling)

### 0.1 Create the repo layout
**Goal:** match a conventional, reviewable Python package structure and keep key modules small.

**Do:**
1. Create directories:
   - `pcb_renderer/`
   - `tests/`
   - `boards/` (copy the provided board JSON files here)
   - `.github/workflows/` (later in Phase 7)

2. Create empty module files:
   - `pcb_renderer/__init__.py`
   - `pcb_renderer/cli.py`
   - `pcb_renderer/models.py`
   - `pcb_renderer/geometry.py`
   - `pcb_renderer/parse.py`
   - `pcb_renderer/errors.py`
   - `pcb_renderer/validate.py`
   - `pcb_renderer/transform.py`
   - `pcb_renderer/render.py`
   - `pcb_renderer/colors.py` (optional constants)

**Results:**
- You have the module boundaries expected by the architecture and plan docs【71:2†architecture_guide_v2.md†L15-L33】【71:2†architecture_guide_v2.md†L74-L109】.

**Sources:**
- [architecture_guide_v2.md — Module responsibilities](./architecture_guide_v2.md)
- [development_plan_v2.md — Deliverables per phase](./development_plan_v2.md)

---

### 0.2 Add `pyproject.toml` and lock dependencies (uv)
**Goal:** reproducible installs (`uv.lock` committed) and fast CI runs.

**Do:**
1. Create `pyproject.toml` with:
   - Python `>=3.11`
   - runtime deps: `pydantic`, `numpy`, `matplotlib`
   - dev deps: `pytest`, `pytest-cov`, `ruff`, `pyright`

2. Create lockfile:
```bash
uv sync
```

**Acceptance Criteria (cross-cutting):**
- `uv.lock` is committed (reproducible installs)
- New checkout can run: `uv sync; pytest` without manual tweaks【67:0†acceptance_criteria_summary.md†L39-L44】.

**Results:**
- You can run tests immediately and CI can be deterministic.

**Sources:**
- [development_plan_v2.md — stack + CI expectations](./development_plan_v2.md)【67:1†development_plan_v2.md†L59-L63】
- [acceptance_criteria_summary.md — fresh environment test expectations](./acceptance_criteria_summary.md)【67:0†acceptance_criteria_summary.md†L39-L44】

---

## Phase 1 (Models + Parsing + Geometry) — “Load every board without crashing”
Phase 1 deliverables are explicitly: **`models.py`, `parse.py`, `geometry.py`**【67:1†development_plan_v2.md†L70-L74】.

---

## 1) Implement geometry primitives (`geometry.py`)

### 1.1 Implement `Point`, `Polyline`, `Polygon`
**Goal:** canonical geometry types that enforce “no impossible geometry” early.

**Do (minimum):**
- `Point(x: float, y: float)` with finite validation (no NaN/Inf)
- `Polyline(points: list[Point])` with ≥2 points
- `Polygon(points: list[Point])` with ≥3 points, helper `bbox()` and `is_closed()`

**AC (Phase 1 / geometry):**
- Point supports add/sub
- Polygon validates ≥3 unique points
- Polyline validates ≥2 points
- Reject non-finite coordinates immediately【67:1†development_plan_v2.md†L70-L74】 (and Phase 1 criteria in the plan)

**Implementation snippet (style + validators):**
```python
# pcb_renderer/geometry.py
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Iterable

@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.x) and math.isfinite(self.y)):
            raise ValueError("Point coordinates must be finite")

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x - other.x, self.y - other.y)


@dataclass(frozen=True)
class Polyline:
    points: tuple[Point, ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("Polyline must have at least 2 points")


@dataclass(frozen=True)
class Polygon:
    points: tuple[Point, ...]

    def __post_init__(self) -> None:
        if len(self.points) < 3:
            raise ValueError("Polygon must have at least 3 points")

    def bbox(self) -> tuple[float, float, float, float]:
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)

    def is_closed(self) -> bool:
        return self.points[0] == self.points[-1]
```

**Results:**
- A solid, testable foundation for parsing, transforms, and rendering.

**Sources:**
- [architecture_guide_v2.md — key models](./architecture_guide_v2.md)【71:2†architecture_guide_v2.md†L1-L9】
- [development_plan_v2.md — geometry expectations](./development_plan_v2.md)

---

## 2) Implement data models (`models.py`) with Pydantic validation

### 2.1 Define the “key models” set
**Goal:** represent PCB entities with type hints everywhere and enforce constraints with validators.

Key model list (from architecture): `Point/Polygon/Polyline`, `Transform`, `Component`, `Trace`, `Via`, `Board`【71:2†architecture_guide_v2.md†L1-L9】.

**Do:**
- Use Pydantic v2 models for:
  - `Transform(position: Point, rotation_deg: float, side: Literal["FRONT","BACK"])`
  - `Pin` / pad geometry (minimal fields needed for validations you implement)
  - `Component(refdes, footprint, transform, outline, pins)`
  - `Trace(uid, net, layer, path, width)`
  - `Via(uid, net, center, diameter, hole_diameter, span)`
  - `Board(metadata, boundary, stackup, nets, components, traces, vias, pours?, keepouts?)`

### 2.2 Implement validators that catch “impossible geometry”
**AC examples (Phase 1):**
- Reject NaN/Inf coordinates
- Reject negative widths/diameters
- Reject via hole ≥ diameter
- Reject polygons with <3 points【67:1†development_plan_v2.md†L70-L74】

**Implementation pattern:** use `@field_validator` and `@model_validator(mode="after")`【71:2†architecture_guide_v2.md†L11-L14】.

**Results:**
- Loading JSON into models becomes the first correctness gate.

**Sources:**
- [development_plan_v2.md — Phase 1 validation built-in](./development_plan_v2.md)
- [architecture_guide_v2.md — validator strategy](./architecture_guide_v2.md)【71:2†architecture_guide_v2.md†L11-L14】
- [Application Implementation Specification — correctness-first parsing](./Application Implementation Specification_ PCB Renderer.md)【67:9†Application Implementation Specification_ PCB Renderer.md†L9-L16】

---

## 3) Implement parsing + normalization (`parse.py`)

### 3.1 Parse JSON, then normalize all spatial values to mm
**Goal:** every downstream module assumes **millimeters** always.

**Requirements:**
- Detect `designUnits`
- Support at least MICRON + MILLIMETER (spec mentions also MILS/INCH as required; implement if time allows)
- Normalize “all spatial coordinates (points, widths, diameters, bounds)” immediately【67:9†Application Implementation Specification_ PCB Renderer.md†L28-L33】.

**Reference implementation pattern (from implementation guide v2):**
- Determine scale (`0.001` for MICRON, `1.0` for MILLIMETER)
- Recursively scale numeric values in spatial sections (`boundary/components/traces/vias/pours/keepouts`)【71:13†implementation_guide_v2.md†L13-L49】.

### 3.2 Parse coordinates in multiple formats
**Requirement:**
- Support both:
  - flat `[x1,y1,x2,y2,...]`
  - nested `[[x1,y1],[x2,y2],...]`【71:2†architecture_guide_v2.md†L29-L33】【71:13†implementation_guide_v2.md†L52-L71】.

### 3.3 Return structured parse errors (not raw exceptions)
Even parse-time failures should be reportable like validation errors (machine code + message + json_path).

**Implementation snippet (core pieces):**
```python
# pcb_renderer/parse.py
import json
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .geometry import Point
from .models import Board

def parse_coordinates(coords: Any) -> list[Point]:
    # Flat: [x1, y1, x2, y2, ...]
    if all(isinstance(c, (int, float)) for c in coords):
        if len(coords) % 2:
            raise ValueError("Flat coordinate list must have even length")
        return [Point(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
    # Nested: [[x, y], ...]
    if all(isinstance(c, (list, tuple)) and len(c) == 2 for c in coords):
        return [Point(c[0], c[1]) for c in coords]
    raise ValueError("Unrecognized coordinate format")

def normalize_units(data: dict[str, Any]) -> dict[str, Any]:
    units = data.get("metadata", {}).get("designUnits", "MICRON")
    if units == "MICRON":
        scale = 0.001
    elif units == "MILLIMETER":
        scale = 1.0
    else:
        raise ValueError(f"Unknown designUnits: {units}")
    # recursive scaling (see implementation_guide_v2)【71:13†implementation_guide_v2.md†L24-L49】
    ...
    return data

def load_board(path: Path) -> tuple[Board | None, list[ValidationError]]:
    try:
        raw = json.loads(path.read_text())
    except Exception as e:
        return None, [ValidationError(code="MALFORMED_JSON", severity="ERROR", message=str(e), json_path="$")]
    ...
```

**AC (Phase 1 parsing):**
- `parse_board(path)` loads boards
- MICRON → mm exact (1 micron = 0.001 mm)
- Unknown `designUnits` returns `INVALID_UNIT_SPECIFICATION` (Phase 2 code list includes this)【71:0†development_plan_v2.md†L14-L15】

**Results:**
- You can now load all provided boards into an internal mm-normalized model.

**Sources:**
- [architecture_guide_v2.md — parse responsibilities](./architecture_guide_v2.md)【71:2†architecture_guide_v2.md†L15-L33】
- [implementation_guide_v2.md — normalize_units + parse_coordinates](./implementation_guide_v2.md)【71:13†implementation_guide_v2.md†L13-L71】
- [Application Implementation Specification — normalization requirements](./Application Implementation Specification_ PCB Renderer.md)【67:9†Application Implementation Specification_ PCB Renderer.md†L28-L33】

---

## Phase 2 (Validation Layer) — 14 deterministic error checks

Validation must:
- run before rendering
- return structured errors: `code, severity, message, json_path`
- collect all errors (not fail-fast)【71:0†development_plan_v2.md†L18-L24】【71:7†architecture_guide_v2.md†L94-L107】.

---

## 4) Define structured errors (`errors.py`)

### 4.1 Create `ValidationError` + `ErrorCode` enum
**AC:**
- `ValidationError` is JSON-serializable
- codes are type-safe (Enum)
- include human-readable templates【71:0†development_plan_v2.md†L41-L46】.

**Reference structure:**
```python
@dataclass
class ValidationError:
    code: str
    severity: str
    message: str
    json_path: str
```【71:12†architecture_guide_v2.md†L43-L51】

**Results:**
- One error type flows through parse/validate/CLI/export.

**Sources:**
- [architecture_guide_v2.md — structured errors](./architecture_guide_v2.md)【71:12†architecture_guide_v2.md†L41-L51】

---

## 5) Implement `validate.py` with all 14 checks

### 5.1 Add the 14 error codes as named functions
The plan’s list of 14 codes is the authoritative checklist【71:0†development_plan_v2.md†L1-L15】:

1. `MISSING_BOUNDARY`
2. `MALFORMED_COORDINATES`
3. `INVALID_ROTATION`
4. `DANGLING_TRACE`
5. `NEGATIVE_WIDTH`
6. `EMPTY_BOARD`
7. `INVALID_VIA_GEOMETRY`
8. `NONEXISTENT_LAYER`
9. `NONEXISTENT_NET`
10. `SELF_INTERSECTING_BOUNDARY`
11. `COMPONENT_OUTSIDE_BOUNDARY`
12. `INVALID_PIN_REFERENCE`
13. `MALFORMED_STACKUP`
14. `INVALID_UNIT_SPECIFICATION`【71:0†development_plan_v2.md†L1-L15】

### 5.2 Enforce deterministic ordering
Validation must return errors in a stable sequence every run【71:0†development_plan_v2.md†L22-L23】.

**Implementation approach:**
- `validate_board(board)` calls checkers in a fixed order and extends a list【71:7†architecture_guide_v2.md†L94-L107】.

### 5.3 Add board-to-error mapping doc (for reviewer clarity)
Plan expects you to document which board triggers which error【71:0†development_plan_v2.md†L25-L39】.

**Results:**
- Invalid boards produce the expected codes; valid boards produce empty list.

**Sources:**
- [development_plan_v2.md — error codes + coverage requirements](./development_plan_v2.md)【71:0†development_plan_v2.md†L1-L50】
- [architecture_guide_v2.md — error collection pattern](./architecture_guide_v2.md)【71:7†architecture_guide_v2.md†L94-L107】

---

## Phase 3 (Transforms) — ECAD→SVG + rotation + x-ray mirroring

Coordinate definitions:
- ECAD: origin bottom-left, +Y up
- SVG: origin top-left, +Y down
- Apply Y-flip at render time【71:7†architecture_guide_v2.md†L51-L68】【71:10†development_plan_v2.md†L8-L12】.

Back-side “X-ray view”:
- mirror bottom geometry horizontally so it appears viewed from top【71:7†architecture_guide_v2.md†L70-L78】.

---

## 6) Implement `transform.py`

### 6.1 Implement `ecad_to_svg` + `svg_to_ecad`
**AC:**
- round-trip property holds
- board height computed from boundary bbox maxY【71:10†development_plan_v2.md†L25-L29】.

**Reference snippet:**
```python
def ecad_to_svg(point: Point, board_height: float) -> Point:
    return Point(x=point.x, y=board_height - point.y)
```【71:7†architecture_guide_v2.md†L63-L68】

### 6.2 Implement component transform pipeline (translate → rotate → mirror)
Pipeline definition【71:10†development_plan_v2.md†L13-L18】:
1. translate to position
2. rotate around centroid
3. mirror if back-side (x-ray)
4. convert ECAD→SVG

**AC highlights:**
- rotation uses centroid as origin
- back-side mirrored
- deterministic floating point comparisons (`np.isclose`, atol ~ 1e-6)【71:10†development_plan_v2.md†L31-L48】.

**Results:**
- You can compute “render-space” geometry for components and pins reliably.

**Sources:**
- [architecture_guide_v2.md — transforms + x-ray view](./architecture_guide_v2.md)【71:7†architecture_guide_v2.md†L70-L78】
- [development_plan_v2.md — transform acceptance criteria](./development_plan_v2.md)【71:10†development_plan_v2.md†L23-L48】

---

## Phase 4 (Rendering) — Matplotlib patches + strict z-order + 3 output formats

Rendering pipeline and z-order are explicitly defined【71:2†architecture_guide_v2.md†L74-L97】 and repeated in the plan【71:8†development_plan_v2.md†L31-L44】:

1. boundary (z=1)
2. pours (z=2)
3. traces (z=3)
4. vias (z=4)
5. components (z=5)
6. reference designators (z=6, halo)
7. keepouts (z=7, hatch `///`)【71:2†architecture_guide_v2.md†L84-L92】.

---

## 7) Implement `colors.py` (optional constants)
**Do:**
Create a single expert-editable dict:

```python
LAYER_COLORS = {
    "TOP": "#CC0000",
    "BOTTOM": "#0000CC",
    "MID": "#00CC00",
}
```
as described【71:2†architecture_guide_v2.md†L98-L108】 and in the plan【71:8†development_plan_v2.md†L46-L54】.

**Results:**
- consistent, professional defaults (red top, blue bottom).

**Sources:**
- [development_plan_v2.md — color defaults](./development_plan_v2.md)【71:8†development_plan_v2.md†L40-L54】

---

## 8) Implement the renderer (`render.py`)

### 8.1 Create figure/axes in a deterministic way
**Do:**
- `fig, ax = plt.subplots()`
- `ax.set_aspect("equal")`
- invert Y to match SVG coordinate direction (or apply Y-flip to points and keep axis normal; pick one and test thoroughly)

### 8.2 Compute viewbox/padding from boundary bbox
Reference function for viewbox computation【71:12†architecture_guide_v2.md†L3-L17】.

### 8.3 Draw primitives in z-order
Implement one function per element type:
- `draw_boundary`
- `draw_pours`
- `draw_traces`
- `draw_vias`
- `draw_components`
- `draw_refdes`
- `draw_keepouts`

### 8.4 Add refdes halo using path effects
Reference halo implementation snippet【71:12†architecture_guide_v2.md†L19-L26】.

### 8.5 Keepout hatch styling
Reference keepout styling snippet includes `hatch='///'`, alpha, zorder=7【71:12†architecture_guide_v2.md†L28-L39】.

### 8.6 Save SVG/PNG/PDF from the same pipeline
The spec requires all three formats from one render pipeline and parity across formats【67:9†Application Implementation Specification_ PCB Renderer.md†L32-L38】.

**Phase 4 “complete when” checklist (from plan):**
- render `board.json` to SVG/PNG/PDF
- all required elements appear
- keepouts overlay everything
- refdes legible with halo
- top/bottom colors correct
- viewbox fits with padding【71:4†development_plan_v2.md†L1-L8】.

**Results:**
- `render_board(board, output_path, fmt)` produces correct outputs.

**Sources:**
- [architecture_guide_v2.md — render pipeline + z-order](./architecture_guide_v2.md)【71:2†architecture_guide_v2.md†L74-L92】
- [architecture_guide_v2.md — viewbox + halo + keepouts](./architecture_guide_v2.md)【71:12†architecture_guide_v2.md†L3-L39】
- [development_plan_v2.md — Phase 4 completion checklist](./development_plan_v2.md)【71:4†development_plan_v2.md†L1-L8】

---

## Phase 5 (CLI) — orchestration + strict/permissive + export JSON

CLI flow (architecture) is:

1. parse args
2. load board (`parse.py`)
3. validate (`validate.py`)
4. if invalid and strict: exit 1
5. if valid: render
6. output result【71:7†architecture_guide_v2.md†L4-L11】.

Also: verbose progress vs quiet mode【71:7†architecture_guide_v2.md†L12-L15】.

---

## 9) Implement the CLI (`cli.py`)

### 9.1 Argparse flags (minimum)
From the plan (v2) the CLI includes:
- positional input
- `-o/--output`
- `--format` override
- `--verbose`
- `--quiet`
- `--help`【71:8†development_plan_v2.md†L60-L79】.

From the spec:
- stdout reserved for progress; suppressed by `--quiet`
- stderr reserved for validation errors
- `--export-json` dumps normalized board + errors for plugin usage【71:6†Application Implementation Specification_ PCB Renderer.md†L1-L10】.

> Note: architecture_guide_v2 mentions a `--permissive` flag as optional behavior【71:7†architecture_guide_v2.md†L87-L93】. If you include it, keep default strict.

### 9.2 Standard output vs standard error format
Follow spec:
- **stdout**: “Loading… Normalizing… Validating… Rendering…” (verbose)
- **stderr**: `[SEVERITY] CODE: Message (Location)`【71:6†Application Implementation Specification_ PCB Renderer.md†L1-L9】.

### 9.3 Implement `--export-json` data contract
When enabled, write a JSON file containing:
- parse result
- normalized board
- validation results
- render result
This is the plugin interface contract【71:9†llm_plugin_architecture.md†L25-L84】.

**Results:**
- `pcb-render board.json -o out.svg` works with correct exit codes and logs.

**Sources:**
- [architecture_guide_v2.md — CLI orchestration flow](./architecture_guide_v2.md)【71:7†architecture_guide_v2.md†L4-L15】
- [Application Implementation Specification — stdout/stderr + export-json](./Application Implementation Specification_ PCB Renderer.md)【71:6†Application Implementation Specification_ PCB Renderer.md†L1-L10】
- [llm_plugin_architecture.md — export contract](./llm_plugin_architecture.md)【71:9†llm_plugin_architecture.md†L25-L84】

---

## Phase 6 (Testing) — unit + integration over all boards

Testing expectations:
- unit tests: geometry, transforms, unit normalization, Pydantic triggers
- integration: load all boards; invalid boards produce expected codes; valid boards render without exceptions【71:8†development_plan_v2.md†L85-L97】【71:12†architecture_guide_v2.md†L71-L83】.
- no snapshot testing required (manual visual checks acceptable)【71:8†development_plan_v2.md†L109-L110】.

---

## 10) Write tests (pytest)

### 10.1 Unit tests
- `test_parse.py`: normalization + coordinate parsing
- `test_transform.py`: ecad↔svg roundtrip, rotation, mirroring
- `test_geometry.py`: bbox, is_closed, min point counts
- `test_models.py`: negative width, NaN coordinates rejected

### 10.2 Integration test: `test_boards.py`
- iterate `boards/*.json`
- load + validate
- assert “known invalid boards” produce expected codes (your mapping table)
- for valid boards: run render to a temp path and assert file exists

**AC (Phase 6 completion):**
- ≥80% coverage
- tests finish <30s
- deterministic, no flakiness【71:4†development_plan_v2.md†L17-L24】.

**Sources:**
- [development_plan_v2.md — Phase 6](./development_plan_v2.md)【71:8†development_plan_v2.md†L85-L110】
- [architecture_guide_v2.md — testing approach](./architecture_guide_v2.md)【71:12†architecture_guide_v2.md†L71-L83】

---

## Phase 7 (CI) — GitHub Actions matrix (3 OS × 2 Python)

Plan requirement:
- matrix: Windows/macOS/Linux × Python 3.11/3.12
- run: `uv sync`, `pytest`, `ruff`, `pyright`
- job time <5 minutes【67:1†development_plan_v2.md†L59-L63】【71:4†development_plan_v2.md†L25-L31】.

---

## 11) Add `.github/workflows/ci.yml`

**Do:**
- Use actions/setup-python
- install uv
- `uv sync --frozen`
- `ruff check .`
- `pyright`
- `pytest --cov ...` enforce ≥80%

**Results:**
- Cross-platform confidence and easier reviewer trust.

**Sources:**
- [development_plan_v2.md — CI requirements](./development_plan_v2.md)【67:1†development_plan_v2.md†L59-L63】【71:4†development_plan_v2.md†L25-L31】

---

## Phase 8 (Docs + polish) — “20-minute reviewable”

Plan’s “Definition of Done” includes:
- all 14 invalid boards detected
- all valid boards render to SVG/PNG/PDF
- keepouts hatched, refdes readable
- ruff + pyright clean
- README includes installation/usage/error codes/testing
- code reviewable in ~20 minutes【71:4†development_plan_v2.md†L45-L79】.

---

## 12) Write `README.md` + `ARCHITECTURE.md`

### 12.1 README required sections
Spec requires:
- Installation (uv sync)
- Quick start examples
- Error code table
- Testing section
- Future Work placeholder (empty outline)【71:6†Application Implementation Specification_ PCB Renderer.md†L47-L55】.

### 12.2 Architecture doc
Include the pipeline and “Correctness > Performance” rationale【71:6†Application Implementation Specification_ PCB Renderer.md†L55-L55】.

**Results:**
- Reviewer can run 2–3 commands and verify everything fast.

**Sources:**
- [development_plan_v2.md — Phase 8 completion list](./development_plan_v2.md)【71:4†development_plan_v2.md†L33-L40】
- [Application Implementation Specification — documentation requirements](./Application Implementation Specification_ PCB Renderer.md)【71:6†Application Implementation Specification_ PCB Renderer.md†L45-L55】

---

# Optional Extension: LLM Plugin Contract (core exports only)

Even if you don’t ship the plugin, you should implement **the export JSON** that enables it.

## 13) Implement `--export-json` output schema
The plugin architecture is explicitly **decoupled**: core renderer exports JSON; plugin consumes it later【71:9†llm_plugin_architecture.md†L5-L16】【71:1†llm_plugin_architecture.md†L34-L45】.

### 13.1 Export structure (recommended)
Write a JSON file containing:
- `input_file`
- `parse_result` (success + normalized board)
- `validation_result` (valid, errors, warnings, checks_run)
- `render_result` (success, output_file, format)

The document includes an example schema and `--export-json` usage【71:9†llm_plugin_architecture.md†L25-L84】.

### 13.2 Ensure errors include `context`
The plugin expects “actionable context” per error type (trace_id, referenced_net, etc.)【71:1†llm_plugin_architecture.md†L66-L84】.

**Results:**
- You can run:
```bash
pcb-render boards/board_kappa.json -o out/kappa.svg --export-json out/kappa.json
```
and later feed `out/kappa.json` to a separate tool.

**Sources:**
- [llm_plugin_architecture.md — contract + examples](./llm_plugin_architecture.md)【71:9†llm_plugin_architecture.md†L25-L84】【71:1†llm_plugin_architecture.md†L66-L84】
- [Application Implementation Specification — export-json is plugin input](./Application Implementation Specification_ PCB Renderer.md)【71:6†Application Implementation Specification_ PCB Renderer.md†L9-L10】

---

# Final “Run This Before Submission” Checklist (copy/paste)

This mirrors the plan’s acceptance testing procedure and definition-of-done expectations【71:4†development_plan_v2.md†L41-L79】.

1. **Fresh environment:**
```bash
uv sync
pytest
```
2. **Lint + typecheck:**
```bash
ruff check .
pyright
```
3. **Render a known-valid board to each format:**
```bash
pcb-render boards/board_simple_2layer.json -o out/simple.svg
pcb-render boards/board_simple_2layer.json -o out/simple.png --format png
pcb-render boards/board_simple_2layer.json -o out/simple.pdf --format pdf
```
4. **Validate known-invalid boards (expect exit code 1 in strict):**
```bash
pcb-render boards/board_eta.json -o out/eta.svg
echo $?
```
5. **Manual visual check (no snapshot tests required):**
- verify z-order, refdes halo, keepout hatching, colors【71:2†architecture_guide_v2.md†L84-L97】【71:12†architecture_guide_v2.md†L19-L39】
