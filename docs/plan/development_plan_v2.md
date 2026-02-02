# PCB Renderer Development Plan (Final)

## Timeline: 2 Calendar Days

Heavy AI assistance for implementation and testing.

## Technology Stack

- **Python 3.11+**: Fast implementation, easy review
- **Pydantic v2**: Schema validation with automatic error generation
- **NumPy**: Coordinate transforms
- **Matplotlib**: All output formats (SVG/PNG/PDF) via single `savefig()` API
- **pytest**: Testing framework
- **uv**: Package manager with lockfile

## Phase 1: Core Models & Parsing (4 hours)

### Objectives
- Define Pydantic models for all PCB elements
- Implement unit normalization (microns â†’ mm)
- Parse coordinates from multiple formats
- Handle component transforms

### Deliverables
- `models.py`: Board, Component, Trace, Via, Keepout models
- `parse.py`: JSON loading with unit normalization
- `geometry.py`: Point, Polygon, Polyline primitives

### Validation Built-In
Pydantic validators catch:
- Non-finite coordinates (NaN, Inf)
- Negative widths/diameters
- Via holes â‰¥ outer diameter
- Polygons with <3 points

### Acceptance Criteria
**Models (`models.py`):**
- [ ] `Board` model validates with all ~20 provided JSON files
- [ ] `Component` model correctly parses pins dict with variable pin counts
- [ ] `Trace` model accepts both flat `[x1,y1,x2,y2,...]` and nested `[[x1,y1],[x2,y2],...]` coordinate formats
- [ ] `Via` model rejects invalid geometry (hole â‰¥ diameter) with ValidationError
- [ ] All models have explicit type hints for every field
- [ ] Pydantic validators catch NaN/Inf coordinates and raise descriptive errors

**Parsing (`parse.py`):**
- [ ] `parse_board(path)` successfully loads `board.json` (main example board)
- [ ] Unit normalization: MICRON â†' mm conversion is exact (1 MICRON = 0.001 mm)
- [ ] Unit normalization: MILLIMETER boards pass through unchanged
- [ ] Unknown `designUnits` raises `INVALID_UNIT_SPECIFICATION` error
- [ ] Coordinate parsing handles both array formats without manual pre-processing
- [ ] JSON parse errors return structured error (not raw exception)

**Geometry (`geometry.py`):**
- [ ] `Point` class supports equality, addition, subtraction operations
- [ ] `Polygon` validates â‰¥3 unique points
- [ ] `Polygon.is_closed()` correctly identifies if first == last point
- [ ] `Polyline` accepts â‰¥2 points
- [ ] All geometry primitives reject non-finite coordinates in constructor

**Cross-cutting:**
- [ ] All modules have docstrings (Google style)
- [ ] Type hints present on all functions and class methods
- [ ] Can parse and normalize `board_alpha.json`, `board_beta.json`, `board_gamma.json` without errors

## Phase 2: Validation Layer (3 hours)

### Objectives
- Implement 14 error detection rules
- Use provided board files to map errors
- Return structured error objects

### Deliverables
- `validate.py`: All validation rules
- `errors.py`: Error codes and messages

### Error Mapping to Provided Boards
Test each of ~20 boards and document which demonstrates which error:
- `board_kappa.json` â†’ trace with single point
- `board_theta.json` â†’ via references nonexistent net
- `board_eta.json` â†’ negative trace width
- etc.

### Error Codes
1. `MISSING_BOUNDARY` - No boundary defined
2. `MALFORMED_COORDINATES` - Invalid coordinate data
3. `INVALID_ROTATION` - Rotation outside 0-360Â°
4. `DANGLING_TRACE` - Trace references nonexistent net/layer
5. `NEGATIVE_WIDTH` - Trace/via has â‰¤0 dimension
6. `EMPTY_BOARD` - No components or traces
7. `INVALID_VIA_GEOMETRY` - Hole â‰¥ diameter
8. `NONEXISTENT_LAYER` - Feature on undefined layer
9. `NONEXISTENT_NET` - Feature on undeclared net
10. `SELF_INTERSECTING_BOUNDARY` - Board outline crosses itself
11. `COMPONENT_OUTSIDE_BOUNDARY` - Component placed beyond edge
12. `INVALID_PIN_REFERENCE` - Pin references wrong component
13. `MALFORMED_STACKUP` - Layer stack incomplete
14. `INVALID_UNIT_SPECIFICATION` - Unknown designUnits

### Acceptance Criteria
**Error Detection (`validate.py`):**
- [ ] All 14 error codes have dedicated validation functions
- [ ] `validate_board(board)` returns `List[ValidationError]` (empty if valid)
- [ ] Each `ValidationError` contains: `code`, `severity`, `message`, `json_path`
- [ ] Validation runs in deterministic order (same errors always appear in same sequence)
- [ ] Multiple errors on single board are all captured (not fail-fast)

**Error Code Coverage (using provided boards):**
- [ ] `MISSING_BOUNDARY`: Detected in at least 1 board (e.g., `board_xi.json` with empty stackup)
- [ ] `MALFORMED_COORDINATES`: Detected in `board_theta.json` (trace with loop/duplicate point)
- [ ] `INVALID_ROTATION`: Detected when component rotation >360° or negative
- [ ] `DANGLING_TRACE`: Detected in `board_iota.json` (trace on nonexistent layer)
- [ ] `NEGATIVE_WIDTH`: Detected in `board_eta.json` (trace width = -100)
- [ ] `EMPTY_BOARD`: Detected when board has boundary but no features
- [ ] `INVALID_VIA_GEOMETRY`: Detected in `board_lambda.json` (hole_size > diameter)
- [ ] `NONEXISTENT_LAYER`: Detected when trace references undefined layer
- [ ] `NONEXISTENT_NET`: Detected in `board_theta.json` (via_bad_net)
- [ ] `SELF_INTERSECTING_BOUNDARY`: Detected when boundary polygon crosses itself
- [ ] `COMPONENT_OUTSIDE_BOUNDARY`: Detected when component center beyond board edge
- [ ] `INVALID_PIN_REFERENCE`: Detected in `board_nu.json` (pin comp_name mismatch)
- [ ] `MALFORMED_STACKUP`: Detected when stackup has layer index gaps or missing TOP/BOTTOM
- [ ] `INVALID_UNIT_SPECIFICATION`: Detected when `designUnits` is not MICRON/MILLIMETER

**Structured Errors (`errors.py`):**
- [ ] `ValidationError` class is a dataclass/Pydantic model
- [ ] Error codes are defined as Enum (type-safe)
- [ ] Each error has human-readable message template
- [ ] JSON path correctly identifies problematic field (e.g., `traces.trace_vcc.width`)

**Integration:**
- [ ] All ~20 provided boards run through validation
- [ ] Exactly 14 boards produce errors (rest validate successfully)
- [ ] Error output is JSON-serializable for CLI consumption

## Phase 3: Coordinate System & Transforms (2 hours)

### Objectives
- Define ECAD coordinate system (origin bottom-left, +Y up)
- Implement Y-axis inversion for SVG output
- Handle component rotation and back-side mirroring

### Coordinate System Spec
- **ECAD**: Origin (0,0) at bottom-left, +X right, +Y up
- **SVG**: Origin top-left, +X right, +Y down
- **Conversion**: Apply Y-flip at render time only

### Transform Pipeline
For each component:
1. Translate to position
2. Rotate around centroid
3. Mirror if back-side (X-axis mirror for X-ray view)
4. Convert ECAD â†’ SVG coordinates

### Deliverables
- `transform.py`: Coordinate conversions and transforms

### Acceptance Criteria
**Coordinate System (`transform.py`):**
- [ ] `ecad_to_svg(point, board_height)` correctly inverts Y-axis
- [ ] Round-trip test: `svg_to_ecad(ecad_to_svg(p, h), h) == p` for any point
- [ ] Board height calculation uses boundary bbox max Y value
- [ ] Coordinate conversion handles edge case: point at origin (0,0)
- [ ] Coordinate conversion handles edge case: point at board top-right corner

**Component Transforms:**
- [ ] `apply_transform(geometry, component)` applies translation first, then rotation
- [ ] Rotation uses component centroid as origin (not global origin)
- [ ] Back-side components are mirrored across X-axis (for X-ray view)
- [ ] Rotation angle is in degrees (0-360)
- [ ] Transform preserves relative geometry (shapes don't distort)

**Test Cases:**
- [ ] Component at (10, 10) with 0° rotation renders at correct SVG position
- [ ] Component at (10, 10) with 90° rotation has correct orientation
- [ ] Component at (10, 10) with 180° rotation is upside-down relative to 0°
- [ ] Back-side component is horizontally flipped relative to front-side equivalent
- [ ] Multi-point polygon transforms all vertices consistently

**Numeric Stability:**
- [ ] Rotation matrix calculations use `np.cos`/`np.sin` (not manual float math)
- [ ] Floating-point comparison uses tolerance (e.g., `np.isclose` with `atol=1e-6`)
- [ ] Transform results are deterministic (same input always produces same output)

## Phase 4: Rendering Engine (5 hours)

### Objectives
- Render all required elements with Matplotlib
- Support SVG/PNG/PDF output
- Implement professional ECAD styling defaults
- Ensure reference designators are readable (halo effect)

### Render Order (Deterministic)
1. Board boundary (black outline, no fill)
2. Copper pours (low opacity)
3. Traces (layer colors, proper width)
4. Vias (filled circles)
5. Component outlines
6. Reference designators (with halo)
7. Keepouts (hatched overlay)

### Layer Colors (Hardcoded Defaults)
- TOP: `#CC0000` (red)
- BOTTOM: `#0000CC` (blue)
- Inner layers: greens/purples
- Keepouts: red with `hatch='///'`

### Optional Color Config
Single file `colors.py` with dict:
```python
LAYER_COLORS = {
    'TOP': '#CC0000',
    'BOTTOM': '#0000CC',
    # ... expert users can edit
}
```

### Deliverables
- `render.py`: Main rendering logic
- `colors.py`: Optional color constants

### Acceptance Criteria
**Rendering Output (`render.py`):**
- [ ] `render_board(board, output_path, format)` produces valid SVG/PNG/PDF
- [ ] SVG output is valid XML (parseable by standard XML parser)
- [ ] PNG output has correct dimensions (board bbox + padding)
- [ ] PDF output is single-page, landscape orientation if board aspect ratio >1.5
- [ ] All three formats render identically (visual parity)

**Element Rendering:**
- [ ] Board boundary draws as closed path with no fill
- [ ] Traces render with correct width in mm (scaled to output resolution)
- [ ] Vias render as circles with correct diameter
- [ ] Component outlines render at transformed positions
- [ ] Reference designators appear at component centroids
- [ ] Keepouts render with diagonal hatch pattern at 45°

**Layer Colors:**
- [ ] TOP layer uses red (`#CC0000` or close)
- [ ] BOTTOM layer uses blue (`#0000CC` or close)
- [ ] Inner layers use distinct muted colors
- [ ] Keepouts use red with high transparency (alpha ~0.3)
- [ ] Copper pours render with low opacity (alpha ~0.2)

**Readability:**
- [ ] Reference designators have white halo/stroke (via `patheffects.withStroke`)
- [ ] Halo stroke width is 2-3 pixels
- [ ] Text is upright even if component is rotated (rotation clamped to ±90°)
- [ ] Font size scales with board dimensions (larger boards = larger text)
- [ ] Minimum font size is 8pt (legible at standard viewing distance)

**Draw Order (Z-order):**
- [ ] Board boundary has lowest z-order (drawn first)
- [ ] Copper pours are above boundary
- [ ] Traces are above pours
- [ ] Vias are above traces
- [ ] Component outlines are above vias
- [ ] Reference designators are above components
- [ ] Keepouts have highest z-order (drawn last, visible overlay)

**ViewBox Calculation:**
- [ ] ViewBox includes all board geometry (no clipping)
- [ ] ViewBox has 5-10% padding on all sides
- [ ] ViewBox preserves board aspect ratio
- [ ] ViewBox origin is at (0, 0) in SVG space (after Y-inversion)

**Integration:**
- [ ] Rendering `board.json` produces output with all required elements visible
- [ ] Rendering `board_6layer_hdi.json` correctly handles 6-layer stackup
- [ ] Rendering `board_complex_boundary.json` handles non-rectangular outline
- [ ] Rendering `board_through_hole.json` shows through-hole pins distinctly

**Performance:**
- [ ] Rendering `board.json` completes in <5 seconds on standard hardware
- [ ] Memory usage stays <500MB for largest provided board

## Phase 5: CLI (2 hours)

### Command Structure
```bash
python render.py input.json -o output.svg [--format svg] [--verbose] [--quiet]
```

### Arguments
- Positional: `input.json` (required)
- `-o, --output`: Output path (required)
- `--format`: svg|png|pdf (auto-detect from extension if omitted)
- `--verbose`: Progress messages (default: on)
- `--quiet`: Non-interactive mode, exit code only
- `--help`: Usage

### Behavior
- **Valid board**: Render, exit 0
- **Invalid board**: Print errors, exit 1
- **Verbose**: "Loading...", "Validating...", "Rendering..."
- **Quiet**: Only "Success" or error summary

### Deliverables
- `cli.py`: Argument parsing and orchestration
- `__main__.py`: Entry point

### Acceptance Criteria
**Argument Parsing:**
- [ ] `--help` displays usage, all options, and examples
- [ ] Missing required args (input or `-o`) prints error and exits 1
- [ ] Invalid `--format` value prints error and exits 1
- [ ] File extension auto-detection works for `.svg`, `.png`, `.pdf`
- [ ] Conflicting args (e.g., `--verbose` + `--quiet`) prints warning

**Valid Board Behavior:**
- [ ] `python render.py board.json -o out.svg` exits with code 0
- [ ] Output file is created at specified path
- [ ] Verbose mode prints: "Loading...", "Validating...", "Rendering...", "Done"
- [ ] Quiet mode prints nothing on success
- [ ] Non-existent input file prints "File not found" and exits 1

**Invalid Board Behavior:**
- [ ] Invalid board exits with code 1
- [ ] Error message includes error code (e.g., `NEGATIVE_WIDTH`)
- [ ] Error message includes JSON path to problem (e.g., `traces.trace_vcc.width`)
- [ ] Multiple errors are all listed (not just first error)
- [ ] Invalid board does NOT produce output file

**Output Format Handling:**
- [ ] `--format svg` produces SVG regardless of output extension
- [ ] `--format png` produces PNG with 300 DPI default
- [ ] `--format pdf` produces single-page PDF
- [ ] Auto-detection from extension: `out.svg` â†' SVG, `out.png` â†' PNG

**Edge Cases:**
- [ ] Output path with non-existent directory creates directory
- [ ] Output path to existing file overwrites without warning
- [ ] Input path with spaces/special chars is handled correctly
- [ ] Ctrl+C during render exits gracefully (no partial output file)

**User Experience:**
- [ ] Error messages are actionable (suggest fix if possible)
- [ ] Progress output flushes immediately (not buffered)
- [ ] Verbose output includes timestamps or step duration
- [ ] Exit code is always 0 for success, 1 for failure (never other values)

**Integration:**
- [ ] Can render all valid boards from `boards/` directory
- [ ] Can validate all invalid boards and report correct errors
- [ ] Works on both absolute and relative file paths

## Phase 6: Testing (4 hours)

### Unit Tests
- Geometry primitives (Point, Polygon)
- Coordinate transforms
- Unit normalization
- Pydantic validation triggers

### Integration Tests
- Load all ~20 provided boards
- Assert invalid boards produce correct error codes
- Assert valid boards render without errors

### Test Structure
```
tests/
  test_models.py      # Pydantic validation
  test_parse.py       # Unit normalization, coord parsing
  test_validate.py    # 14 error conditions
  test_transform.py   # Coordinate conversions
  test_render.py      # Rendering doesn't crash
  test_boards.py      # All provided boards
```

### No Snapshot Testing
Manual visual verification of rendered outputs is acceptable.

### Acceptance Criteria
**Unit Tests (per module):**
- [ ] `test_models.py`: â‰¥20 test cases covering all Pydantic validators
- [ ] `test_parse.py`: â‰¥15 test cases for unit conversion and coordinate formats
- [ ] `test_validate.py`: â‰¥14 test cases (one per error code)
- [ ] `test_transform.py`: â‰¥10 test cases for coordinate/rotation transforms
- [ ] `test_render.py`: â‰¥8 test cases ensuring render doesn't crash

**Integration Tests:**
- [ ] `test_boards.py`: Loads all ~20 provided boards
- [ ] Invalid boards (14 expected) all produce validation errors
- [ ] Valid boards (remaining ~6) all render without errors
- [ ] Each invalid board triggers expected error code(s)

**Test Quality:**
- [ ] All tests pass on fresh checkout (no manual setup required)
- [ ] Tests are deterministic (no flaky failures)
- [ ] Each test has descriptive docstring explaining what it validates
- [ ] Tests use pytest fixtures for common setup (e.g., sample board data)
- [ ] No tests depend on external state (files, network, etc.)

**Coverage Targets:**
- [ ] `models.py`: â‰¥90% line coverage
- [ ] `parse.py`: â‰¥85% line coverage
- [ ] `validate.py`: â‰¥95% line coverage (all error paths exercised)
- [ ] `transform.py`: â‰¥90% line coverage
- [ ] `render.py`: â‰¥70% line coverage (rendering internals are complex)
- [ ] Overall project: â‰¥80% line coverage

**Error Path Testing:**
- [ ] Test that NaN coordinates raise ValidationError with correct message
- [ ] Test that via with hole > diameter raises ValidationError
- [ ] Test that trace with zero width raises ValidationError
- [ ] Test that component outside boundary triggers validation error
- [ ] Test that missing boundary prevents rendering

**Parameterized Tests:**
- [ ] Coordinate parsing tests are parameterized over both array formats
- [ ] Unit conversion tests are parameterized over MICRON/MILLIMETER inputs
- [ ] Transform tests are parameterized over rotation angles (0, 90, 180, 270)

**Performance Tests:**
- [ ] Rendering largest board completes in <10 seconds
- [ ] Memory usage for largest board stays <1GB
- [ ] Validation of all boards completes in <2 seconds total

**Test Execution:**
- [ ] `pytest` runs all tests with verbose output
- [ ] `pytest --cov` generates coverage report
- [ ] No test warnings or deprecations in output
- [ ] Test suite completes in <30 seconds on standard hardware

## Phase 7: CI/CD (1 hour)

### GitHub Actions Workflow
- Matrix: Windows, macOS, Linux Ã— Python 3.11, 3.12
- Steps: checkout, setup Python, `uv sync`, `pytest`, `ruff`, `pyright`
- Coverage: `pytest-cov` with 80% minimum

### Local Development
- `uv sync` to install deps
- `pytest` to run tests
- `ruff check` for linting
- `pyright` for type checking

### Acceptance Criteria
**GitHub Actions Workflow:**
- [ ] Workflow file is named `.github/workflows/ci.yml`
- [ ] Matrix includes: `[ubuntu-latest, macos-latest, windows-latest]`
- [ ] Matrix includes: `[python-3.11, python-3.12]`
- [ ] Workflow runs on: push to main, pull requests, manual dispatch
- [ ] All steps have descriptive names

**CI Steps:**
- [ ] Checkout repository (actions/checkout@v4)
- [ ] Setup Python with specified version (actions/setup-python@v5)
- [ ] Install uv package manager
- [ ] Run `uv sync` to install dependencies
- [ ] Run `pytest` with coverage (`pytest --cov --cov-report=xml`)
- [ ] Run `ruff check` (exits 1 on lint errors)
- [ ] Run `pyright` (exits 1 on type errors)
- [ ] Upload coverage report to GitHub (actions/upload-artifact@v4)

**Pass Criteria:**
- [ ] All test runs pass on all OS/Python combinations (6 total)
- [ ] Coverage meets 80% minimum threshold (fails if below)
- [ ] No lint errors from ruff
- [ ] No type errors from pyright
- [ ] Workflow completes in <5 minutes per matrix job

**Coverage Reporting:**
- [ ] Coverage XML uploaded as artifact
- [ ] Coverage summary displayed in workflow output
- [ ] Coverage fails if <80% (configured in pytest.ini or workflow)

**Local Development Tools:**
- [ ] `pyproject.toml` has ruff configuration
- [ ] `pyproject.toml` has pyright configuration
- [ ] `pytest.ini` or `pyproject.toml` has pytest settings
- [ ] `uv.lock` is committed (reproducible builds)

**Developer Experience:**
- [ ] New contributor can clone, `uv sync`, `pytest` without errors
- [ ] Pre-commit hooks (optional) can run ruff and pyright locally
- [ ] README has "Development" section with setup instructions
- [ ] CI failures have actionable error messages (not just "failed")

**Platform-Specific Handling:**
- [ ] Windows path separators work correctly in all file operations
- [ ] macOS (case-insensitive filesystem) doesn't break tests
- [ ] Linux (case-sensitive filesystem) handles all test files

## Phase 8: Documentation (2 hours)

### README Structure
- Purpose and scope
- Installation (`uv sync`)
- Usage examples
- Error codes reference
- Testing (`pytest`)
- **Future Work** (empty outline section)

### Docstrings
- Google style for all public functions
- Type hints mandatory

### Acceptance Criteria
**README.md:**
- [ ] Includes project title and one-sentence description
- [ ] "Installation" section with `uv sync` command
- [ ] "Usage" section with CLI examples (at least 3)
- [ ] "Error Codes" section listing all 14 codes with descriptions
- [ ] "Testing" section with `pytest` and coverage commands
- [ ] "Future Work" section (may be empty outline)
- [ ] All code blocks use proper markdown syntax highlighting
- [ ] Links to related docs (if any) work correctly

**Code Documentation:**
- [ ] All public functions have docstrings (Google style)
- [ ] All public classes have class-level docstrings
- [ ] All modules have module-level docstrings
- [ ] Docstrings include: description, Args, Returns, Raises sections
- [ ] Complex algorithms have inline comments explaining key steps

**Type Hints:**
- [ ] All function signatures have complete type hints
- [ ] Return types are explicit (not inferred)
- [ ] Complex types use proper generics (e.g., `List[Point]` not `list`)
- [ ] Optional parameters use `Optional[T]` or `T | None`
- [ ] No `Any` types except where truly necessary

**Examples:**
- [ ] README includes example of rendering valid board
- [ ] README includes example of validating invalid board
- [ ] README includes example of different output formats
- [ ] README shows expected output for each example

**Error Documentation:**
- [ ] Each error code has description in README
- [ ] Error descriptions include example of what triggers them
- [ ] Error descriptions suggest how to fix the issue
- [ ] Error codes are in consistent format (SCREAMING_SNAKE_CASE)

**Installation Instructions:**
- [ ] Prerequisites section lists Python 3.11+ requirement
- [ ] Installation commands work on fresh system
- [ ] Troubleshooting section addresses common issues
- [ ] Platform-specific notes (if any) are clearly marked

**Code Review Readiness:**
- [ ] README explains project structure/architecture briefly
- [ ] README has "Design Decisions" section explaining key choices
- [ ] README mentions review time target (20 minutes)
- [ ] All example commands in README are copy-paste ready

**Professional Polish:**
- [ ] No spelling errors in documentation
- [ ] Consistent terminology throughout
- [ ] Code examples are runnable (not pseudocode)
- [ ] LICENSE file present (if appropriate)

## Total Timeline

- Phase 1: 4 hours
- Phase 2: 3 hours
- Phase 3: 2 hours
- Phase 4: 5 hours
- Phase 5: 2 hours
- Phase 6: 4 hours
- Phase 7: 1 hour
- Phase 8: 2 hours

**Total: 23 hours over 2 calendar days**

## Risk Mitigation

**Geometric edge cases**: Use Pydantic validators to catch early
**Platform differences**: CI matrix catches issues
**Time pressure**: AI assists with test generation and boilerplate

## Success Criteria

1. All 14 invalid boards detected correctly
2. Valid boards render with readable output
3. Code reviewable in 20 minutes:
   - Clear structure
   - Well-commented
   - Example outputs included
4. Tests pass on all platforms
5. Exit codes communicate success/failure

## Comprehensive Phase Completion Checklist

### Phase 1 Complete When:
✓ All 3 deliverable files (`models.py`, `parse.py`, `geometry.py`) exist and have docstrings
✓ Can parse and normalize all test boards without crashes
✓ Unit tests for models, parsing, and geometry pass
✓ Pydantic validation catches all specified edge cases

### Phase 2 Complete When:
✓ All 14 error codes are implemented as validation functions
✓ Mapping document exists showing which board triggers which error
✓ `validate_board()` returns structured errors with JSON paths
✓ Test suite verifies all 14 error codes trigger correctly
✓ Invalid boards do not render (fail validation step)

### Phase 3 Complete When:
✓ `transform.py` implements all coordinate conversion functions
✓ ECAD â†" SVG round-trip tests pass
✓ Component rotation and mirroring work correctly
✓ Transform tests pass for all rotation angles (0, 90, 180, 270)
✓ Back-side components render mirrored relative to front-side

### Phase 4 Complete When:
✓ Can render `board.json` to SVG/PNG/PDF without errors
✓ All required elements appear in output (boundary, traces, vias, components, refdes, keepouts)
✓ Z-order is correct (keepouts overlay everything else)
✓ Reference designators are legible with halo effect
✓ Layer colors match specification (red TOP, blue BOTTOM)
✓ ViewBox correctly fits all geometry with padding

### Phase 5 Complete When:
✓ CLI accepts all required arguments and flags
✓ `--help` output is complete and accurate
✓ Valid boards render and exit 0
✓ Invalid boards print errors and exit 1
✓ Verbose/quiet modes work as specified
✓ All file path edge cases handled (spaces, relative, absolute)

### Phase 6 Complete When:
✓ Test suite has â‰¥80% overall coverage
✓ All ~20 provided boards are tested
✓ All tests pass on fresh checkout
✓ No flaky tests (deterministic results)
✓ Test suite completes in <30 seconds
✓ Coverage report is generated and checked

### Phase 7 Complete When:
✓ GitHub Actions workflow file exists and is valid
✓ All matrix jobs (6 combinations) pass
✓ Coverage is uploaded as artifact
✓ Ruff and pyright checks pass
✓ Workflow completes in <5 minutes per job
✓ Local dev setup instructions in README work

### Phase 8 Complete When:
✓ README has all required sections
✓ All code has docstrings and type hints
✓ Error codes documented with examples
✓ Installation instructions tested on fresh system
✓ Example commands are copy-paste ready
✓ No spelling/grammar errors in documentation

## Definition of Done (Entire Project)

The project is complete when **all** of the following are true:

**Functional:**
- [ ] All 14 invalid boards are detected and reported with correct error codes
- [ ] All valid boards render to SVG/PNG/PDF without errors
- [ ] Reference designators are readable on all rendered outputs
- [ ] Keepouts are visually distinct with hatch pattern

**Quality:**
- [ ] Test suite has â‰¥80% coverage and all tests pass
- [ ] Code passes ruff linting with zero errors
- [ ] Code passes pyright type checking with zero errors
- [ ] No warnings in test output

**Portability:**
- [ ] Works on Windows, macOS, and Linux
- [ ] Works with Python 3.11 and 3.12
- [ ] Fresh checkout runs with just `uv sync; pytest`
- [ ] CI passes on all platform/Python combinations

**Documentation:**
- [ ] README contains installation, usage, error codes, testing sections
- [ ] All functions have Google-style docstrings
- [ ] All functions have complete type hints
- [ ] Design decisions are explained in README or docs/

**Usability:**
- [ ] CLI is intuitive (`--help` is sufficient to use tool)
- [ ] Error messages are actionable
- [ ] Exit codes are correct (0=success, 1=failure)
- [ ] Rendering completes in reasonable time (<10s for largest board)

**Reviewability:**
- [ ] Code can be understood in 20 minutes
- [ ] Project structure is clear and conventional
- [ ] Example outputs are included in repository
- [ ] Key files are <500 lines each (except tests)

## Acceptance Testing Procedure

Before submitting, run this checklist:

1. **Fresh Environment Test:**
   ```bash
   git clone <repo>
   cd <repo>
   uv sync
   pytest
   ```
   → Must complete without manual intervention

2. **CLI Smoke Test:**
   ```bash
   python render.py boards/board.json -o test.svg
   python render.py boards/board_theta.json -o test2.svg
   ```
   → First succeeds (exit 0), second fails with error (exit 1)

3. **All Boards Test:**
   ```bash
   for board in boards/*.json; do
     python render.py "$board" -o "out/$(basename $board .json).svg" || true
   done
   ```
   → Exactly 14 failures (invalid boards), rest succeed

4. **Cross-Platform Test:**
   - Push to GitHub
   - Wait for CI to run
   → All 6 matrix jobs pass

5. **Documentation Test:**
   - Follow README from scratch on fresh VM
   → Can render example board without issues

6. **Visual Inspection:**
   - Open rendered SVG of `board.json`
   → Refdes legible, keepouts visible, layers colored correctly

