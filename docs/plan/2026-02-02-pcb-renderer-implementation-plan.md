# Plan

## Scope
Build the core PCB renderer (parse/validate/transform/render/CLI/tests) plus CI/CD, Docker, and documentation deliverables, aligned to `development_plan_v2`, `architecture_guide_v2`, `implementation_guide_v2`, the Application Implementation Specification, and the code‑challenge PDF export.

## Implementation Steps
1. **Repo audit & layout alignment**
   - Verify/establish `pcb_renderer/` package, `tests/`, and dependency/tooling in `pyproject.toml` (pydantic, numpy, matplotlib, pytest, ruff, pyright, uv).
   - Ensure board fixtures are in `boards/` and used by tests.

2. **Geometry + Models (Phase 1)**
   - Implement `geometry.py` primitives (`Point`, `Polygon`, `Polyline`, optional `Circle`) with finite‑value validation and basic ops.
   - Implement `models.py` Pydantic models (`Board`, `Component`, `Trace`, `Via`, `Keepout`, `Layer`, `Net`, `Transform`) with validators for widths/diameters/rotation/pin references and cross‑references.

3. **Parsing + Unit Normalization (Phase 1)**
   - Implement `parse.py` to load JSON, normalize units (**MICRON → mm**, **MILLIMETER → mm**), parse flat/nested coordinates, and build models.
   - Return structured parse errors for malformed JSON, I/O errors, and parse failures.

4. **Validation Layer (Phase 2)**
   - Implement `errors.py` with `ErrorCode` enum + `ValidationError` model.
   - Implement `validate.py` with 14 deterministic checks (boundary, malformed trace, invalid rotation, dangling trace, negative width, empty board, via geometry, nonexistent layer/net, self‑intersection, component outside, invalid pin ref, malformed stackup, invalid unit spec).
   - Map tests to the provided invalid boards.

5. **Transforms (Phase 3)**
   - Implement `transform.py` for ECAD↔SVG Y‑flip, component rotation (about centroid), translation, and back‑side mirroring (X‑axis for X‑ray view).
   - Use NumPy matrices and tolerance‑safe comparisons.

6. **Rendering Engine (Phase 4)**
   - Implement `render.py` with Matplotlib drawing in deterministic z‑order (boundary → pours → traces → vias → components → refdes → keepouts).
   - Implement `colors.py` for layer palette, text halo via `patheffects`, keepout hatching, and viewbox padding.
   - Support SVG/PNG/PDF with consistent output.

7. **CLI Orchestration (Phase 5)**
   - Implement `cli.py` + `__main__.py` with strict/permissive mode, verbose/quiet logging, `--format` inference, output dir creation, and `--export-json`.
   - **Compatibility**: accept both positional `input` and `--input` (alias) to satisfy differing docs.

8. **Testing (Phase 6)**
   - Unit tests for geometry, parsing, validators, transforms, and render smoke tests.
   - Integration tests loading all boards and asserting error codes for invalid boards; ensure valid boards render.
   - Add coverage target (~80%) in pytest config.

9. **CI/CD + Docker (Phase 7)**
   - Add GitHub Actions matrix (Win/macOS/Linux × Py3.11/3.12) with `uv sync`, `pytest --cov`, `ruff`, `pyright`.
   - Add Dockerfile per spec (python:3.11‑slim + freetype) and entrypoint to `pcb-render`.

10. **Docs (Phase 8)**
   - Update README with install/usage/error codes/testing and include “Future Work”.
   - Add ARCHITECTURE.md summary aligned to `architecture_guide_v2`.

## Validation & Test Commands
- `uv sync`
- `pytest --cov`
- `ruff check`
- `pyright`

## Assumptions (confirm before coding)
- Unit support is **MICRON + MILLIMETER only**; MILS/INCH will be treated as invalid units.
- CLI will support both positional `input` and `--input` flag to reconcile spec differences.

If this plan looks good, I’ll proceed with implementation in the repo.