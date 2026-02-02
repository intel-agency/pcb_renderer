# PCB Renderer Architecture Guide (Final)

## Design Principles

1. **Correctness over performance**: Strict validation, explicit coordinate handling
2. **Reviewability**: Clear structure, minimal complexity
3. **Determinism**: Stable output for version control and testing
4. **Simplicity**: Standard libraries, no clever optimizations

## System Architecture

```
┌─────────────────────────────────────┐
│           CLI Layer                 │
│  - Argument parsing                 │
│  - Progress reporting               │
│  - Error formatting                 │
└────────────┬────────────────────────┘
             │
┌────────────▼────────────────────────┐
│       Application Layer             │
│  - Orchestrates pipeline            │
│  - Handles strict/permissive modes  │
└────────────┬────────────────────────┘
             │
     ┌───────┴───────┐
     │               │
┌────▼─────┐   ┌────▼──────┐
│  Parse   │   │ Validate  │
│          │   │           │
│ - Load   │   │ - 14      │
│ - Norm   │   │   checks  │
└────┬─────┘   └────┬──────┘
     │              │
     └──────┬───────┘
            │
     ┌──────▼────────┐
     │   Transform   │
     │               │
     │ - Coords      │
     │ - Rotations   │
     └───────┬───────┘
             │
     ┌───────▼────────┐
     │    Render      │
     │                │
     │ - Matplotlib   │
     │ - SVG/PNG/PDF  │
     └────────────────┘
```

## Module Organization

### models.py
Pydantic data models for all PCB elements.

**Key Models:**
- `Point`: 2D coordinate with finite validation
- `Polygon`: Closed shape with ≥3 points
- `Polyline`: Open path with ≥2 points
- `Transform`: Position, rotation, side
- `Component`: Refdes, footprint, pins, outline
- `Trace`: Path, width, net, layer
- `Via`: Center, diameters, net, span
- `Board`: Root container

**Validation Strategy:**
- `@field_validator`: Field-level constraints
- `@model_validator(mode='after')`: Cross-field constraints

### parse.py
JSON loading and normalization.

**Responsibilities:**
- Load JSON file
- Normalize units to millimeters
- Parse coordinates from multiple formats
- Convert to Pydantic models

**Unit Normalization:**
- Detect `designUnits` field
- Apply scale factor (0.001 for MICRON, 1.0 for MILLIMETER)
- Recursively scale all spatial values

**Coordinate Parsing:**
- Flat lists: `[x1, y1, x2, y2, ...]`
- Nested pairs: `[[x1, y1], [x2, y2], ...]`
- Auto-detect format and convert to `List[Point]`

### validate.py
Validation rules and error detection.

**Error Model:**
```python
class ValidationError:
    code: str        # Error identifier
    severity: str    # ERROR, WARNING, INFO
    message: str     # Human-readable
    json_path: str   # Location in JSON
```

**Validation Layers:**
1. **Pydantic**: Type and range checks (automatic)
2. **Geometric**: Self-intersection, containment
3. **Reference**: Net/layer existence
4. **Topological**: Components within boundary

**14 Error Types:**
See development plan for complete list.

### transform.py
Coordinate system conversions and geometric transforms.

**Coordinate Systems:**
- **ECAD**: Origin bottom-left, +Y up (input)
- **SVG**: Origin top-left, +Y down (output)
- **Conversion**: Single Y-flip at render time

**Component Transform Pipeline:**
1. Position translation
2. Rotation around centroid
3. Back-side mirroring (X-axis for X-ray view)
4. ECAD → SVG conversion

**Matrix Operations:**
- Use NumPy for efficiency
- Cache trigonometric values
- Vectorize when processing multiple points

### render.py
Matplotlib-based rendering engine.

**Render Pipeline:**
1. Create figure and axes
2. Set coordinate system and aspect ratio
3. Draw elements in deterministic order
4. Apply styling
5. Save to requested format

**Drawing Order (Z-order):**
1. Boundary (zorder=1)
2. Pours (zorder=2, alpha=0.3)
3. Traces (zorder=3)
4. Vias (zorder=4)
5. Components (zorder=5)
6. Reference designators (zorder=6)
7. Keepouts (zorder=7, hatch='///')

**Styling:**
- Layer colors from `colors.py`
- Reference designator halo: `patheffects.withStroke()`
- Keepout hatching: `hatch='///'`, `alpha=0.5`

### colors.py (Optional)
Single constants file for expert customization.

```python
LAYER_COLORS = {
    'TOP': '#CC0000',
    'BOTTOM': '#0000CC',
    'MID': '#00CC00',
    # ... users can edit if desired
}
```

### cli.py
Command-line interface and orchestration.

**Flow:**
1. Parse arguments
2. Load board (`parse.py`)
3. Validate board (`validate.py`)
4. If invalid and strict: exit 1
5. If valid: render (`render.py`)
6. Output result

**Progress Reporting:**
- Verbose (default): "Loading...", "Validating...", "Rendering..."
- Quiet: Only exit code and error summary

## Data Flow

```
JSON file
    │
    ├─→ Load (parse.py)
    │       │
    │       ├─→ Normalize units
    │       ├─→ Parse coordinates
    │       └─→ Construct Pydantic models
    │
    ├─→ Validate (validate.py)
    │       │
    │       ├─→ Pydantic validators (automatic)
    │       ├─→ Geometric checks
    │       ├─→ Reference checks
    │       └─→ Return errors or None
    │
    ├─→ Transform (transform.py)
    │       │
    │       ├─→ Component placement
    │       ├─→ Rotation matrices
    │       ├─→ Back-side mirroring
    │       └─→ ECAD → SVG conversion
    │
    └─→ Render (render.py)
            │
            ├─→ Setup Matplotlib figure
            ├─→ Draw in order (boundary → keepouts)
            ├─→ Apply styling
            └─→ Save SVG/PNG/PDF
```

## Coordinate System Details

### ECAD Coordinates (Input)
- Origin: `(0, 0)` at **bottom-left** of board
- X-axis: **Right** (+X increases to the right)
- Y-axis: **Up** (+Y increases upward)
- Rotation: Counter-clockwise from +X axis

### SVG Coordinates (Output)
- Origin: `(0, 0)` at **top-left** of viewport
- X-axis: **Right** (same as ECAD)
- Y-axis: **Down** (+Y increases downward)
- Rotation: Clockwise from +X axis

### Y-Axis Inversion
Applied once at render time:
```python
def ecad_to_svg(point: Point, board_height: float) -> Point:
    return Point(x=point.x, y=board_height - point.y)
```

### X-Ray View for Back Side
Bottom-layer components are mirrored horizontally (X-axis) so they appear as if viewed through the board from the top.

**Transform:**
```python
if component.side == "BACK":
    # Mirror across X-axis
    point = Point(x=-point.x, y=point.y)
```

## Validation Architecture

### Strict Mode (Default)
- Invalid boards do not render
- Exit code 1
- Print all validation errors

### Permissive Mode (Optional)
- Enabled via `--permissive` flag
- Skip invalid elements
- Render valid elements only
- Print warnings for skipped items
- Exit code 0

### Error Collection
Collect all errors before failing (not fail-fast):
```python
def validate_board(board: Board) -> List[ValidationError]:
    errors = []
    
    # Run all checks
    errors.extend(check_boundary(board))
    errors.extend(check_traces(board))
    errors.extend(check_vias(board))
    # ... all 14 checks
    
    return errors
```

## Rendering Details

### ViewBox Calculation
SVG viewBox computed from board boundary with padding:
```python
def compute_viewbox(boundary: Polygon, padding: float = 0.1):
    min_x, min_y, max_x, max_y = boundary.bbox()
    width = max_x - min_x
    height = max_y - min_y
    
    vb_x = min_x - width * padding
    vb_y = min_y - height * padding
    vb_width = width * (1 + 2 * padding)
    vb_height = height * (1 + 2 * padding)
    
    return f"{vb_x} {vb_y} {vb_width} {vb_height}"
```

### Reference Designator Halo
For readability across all backgrounds:
```python
text = ax.text(x, y, refdes, ...)
text.set_path_effects([
    patheffects.withStroke(linewidth=3, foreground='black')
])
```

### Keepout Rendering
Distinctive visual treatment:
```python
patch = Polygon(xy, 
    facecolor='red',
    edgecolor='red',
    alpha=0.3,
    hatch='///',
    linewidth=2,
    zorder=7
)
```

## Error Reporting

### Structured Errors
```python
@dataclass
class ValidationError:
    code: str           # e.g., "MISSING_BOUNDARY"
    severity: str       # "ERROR", "WARNING", "INFO"
    message: str        # Human-readable description
    json_path: str      # Location: "$.components.R1.transform"
```

### CLI Output
**Verbose:**
```
Loading board from board_kappa.json...
Validating geometry...
ERROR: Trace trace_single_point has only 1 point (minimum 2)
  Location: $.traces.trace_single_point.path.coordinates
ERROR: Via via_bad_net references nonexistent net NONEXISTENT_NET_XYZ
  Location: $.vias.via_bad_net.net_name

Validation failed with 2 errors.
```

**Quiet:**
```
FAILED: 2 errors
```

## Testing Strategy

### Unit Tests
- `test_models.py`: Pydantic validation triggers
- `test_parse.py`: Unit normalization, coordinate parsing
- `test_validate.py`: All 14 error conditions
- `test_transform.py`: Coordinate conversions, rotations

### Integration Tests
- `test_boards.py`: Load all ~20 provided boards
- Assert invalid boards produce expected error codes
- Assert valid boards render without exceptions

### Test Data
Use provided boards directly:
```python
def test_board_kappa_trace_error():
    board, errors = load_board("boards/board_kappa.json")
    assert any(e.code == "MALFORMED_TRACE" for e in errors)
```

## LLM Plugin Interface

### Decoupling
- Core renderer is **standalone**
- LLM plugin is **optional add-on**
- No runtime dependency on LLM

### Data Contract
Core app exports:
```python
{
    "board": {
        "metadata": {...},
        "boundary": [...],
        "components": {...},
        # ... full normalized board
    },
    "errors": [
        {
            "code": "MISSING_BOUNDARY",
            "severity": "ERROR",
            "message": "...",
            "json_path": "..."
        }
    ],
    "rendered": true/false
}
```

### Plugin Consumes
- Structured errors for natural-language explanations
- Board metadata for context
- Validation results for suggestions

**See separate LLM Plugin Architecture document for details.**

## Performance Considerations

### Not a Priority
Correctness > speed for this challenge.

### Simple Optimizations
- Cache coordinate transforms per component
- Use NumPy vectorization for point arrays
- Reuse Matplotlib figure objects

### Profiling
- Profile with `cProfile` only if rendering is slow (>5s)
- Optimize hot paths identified by profiling

## Future Work (README Outline Only)

Empty section in README for potential additions:
- Multi-threaded rendering for large boards
- Interactive web viewer
- Gerber export
- Design rule checking (DRC)
- 3D visualization

This section remains empty in submission but provides structure for later expansion.
