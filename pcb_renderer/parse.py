"""Parsing and unit normalization for ECAD JSON board files.

This module handles the first stage of the PCB Renderer pipeline:

    Input JSON → parse.py → normalize_units() → Pydantic models

Design Philosophy:
------------------
**Parsing is permissive; validation is authoritative.**

The parser is intentionally lenient - it tries to create a Board object from
the input JSON even if some fields are malformed. Semantic validation happens
later in validate.py, which can report ALL issues rather than failing on the
first error.

This approach enables:
1. Better error reporting (all issues found, not just the first)
2. Graceful degradation with --permissive mode
3. Partial board data for LLM analysis even when invalid

Unit Handling (per challenge requirements):
-------------------------------------------
Only two units are accepted:
- MICRON: Scaled by 0.001 to convert to millimeters
- MILLIMETER: No scaling (multiply by 1.0)

Any other unit value triggers INVALID_UNIT_SPECIFICATION error.
Internally, everything is stored in millimeters after parsing.

Coordinate Formats:
-------------------
The parser accepts two coordinate formats:
1. Flat array: [x1, y1, x2, y2, ...] - common in some ECAD exports
2. Nested pairs: [[x1, y1], [x2, y2], ...] - more readable format

Both are normalized to List[Point] during parsing.

Error Handling:
---------------
All functions return (result, List[ValidationError]) tuples rather than
raising exceptions. This allows the caller to decide how to handle errors
(stop immediately, collect all errors, use --permissive mode, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .errors import ErrorCode, Severity, ValidationError
from .geometry import Circle, Point, Polygon, Polyline
from .models import Board, Layer

# Conversion factor: 1 micron = 0.001 millimeters
MICRON_TO_MM = 0.001


def _scale_value(value: Any, scale: float) -> Any:
    """Recursively scale numeric values in a nested data structure.

    Used by normalize_units() to convert all spatial coordinates from
    the input unit (MICRON or MILLIMETER) to internal millimeters.

    Args:
        value: Any JSON-compatible value (dict, list, number, string, bool)
        scale: Multiplication factor (0.001 for microns, 1.0 for mm)

    Returns:
        The value with all numeric fields scaled.

    Note:
        Booleans are explicitly checked first because in Python,
        bool is a subclass of int, so isinstance(True, int) is True.
        Without this check, True would become 1.0 * scale.
    """
    # Guard: bool must be checked before int/float (bool is subclass of int)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value * scale
    if isinstance(value, list):
        return [_scale_value(v, scale) for v in value]
    if isinstance(value, dict):
        return {k: _scale_value(v, scale) for k, v in value.items()}
    return value


def normalize_units(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[ValidationError]]:
    """Normalize all spatial values to millimeters.

    This function reads the designUnits from metadata and scales all
    spatial sections (boundary, components, traces, vias, pours, keepouts)
    to internal millimeter representation.

    Args:
        data: Raw parsed JSON dictionary

    Returns:
        Tuple of (normalized_data, errors). If designUnits is invalid,
        returns the original data unchanged with an error.

    Supported Units:
        - MICRON: Multiplied by 0.001 to convert to mm
        - MILLIMETER: No change (scale = 1.0)

    Challenge Requirement:
        This addresses the INVALID_UNIT_SPECIFICATION error code.
        Only MICRON and MILLIMETER are valid input units.
    """
    errors: List[ValidationError] = []
    units = data.get("metadata", {}).get("designUnits", "MICRON")
    if units == "MICRON":
        scale = MICRON_TO_MM
    elif units == "MILLIMETER":
        scale = 1.0
    else:
        errors.append(
            ValidationError(
                code=ErrorCode.INVALID_UNIT_SPECIFICATION,
                severity=Severity.ERROR,
                message=f"Unknown designUnits: {units}",
                json_path="$.metadata.designUnits",
            )
        )
        return data, errors

    spatial_sections = ["boundary", "components", "traces", "vias", "pours", "keepouts"]
    for section in spatial_sections:
        if section in data:
            data[section] = _scale_value(data[section], scale)

    if "metadata" in data:
        data["metadata"]["designUnits"] = "MILLIMETER"
    return data, errors


def parse_coordinates(raw: Any) -> List[Point]:
    """Parse coordinate data into a list of Point objects.

    Accepts two formats commonly found in ECAD JSON exports:
    1. Flat array: [x1, y1, x2, y2, x3, y3, ...]
    2. Nested pairs: [[x1, y1], [x2, y2], [x3, y3], ...]

    Args:
        raw: Coordinate data in either format

    Returns:
        List of Point objects

    Raises:
        ValueError: If the format is unrecognized or data is empty/malformed

    Challenge Requirement:
        Proper coordinate parsing is essential for drawing the board boundary
        (Task 1) and traces (Task 3). Malformed coordinates trigger
        MALFORMED_COORDINATES error during validation.
    """
    if not raw:
        raise ValueError("Empty coordinate array")
    # Check for flat array format: [x1, y1, x2, y2, ...]
    if all(isinstance(c, (int, float)) for c in raw):
        if len(raw) % 2 != 0:
            raise ValueError("Flat coordinate list must have even length")
        return [Point(x=raw[i], y=raw[i + 1]) for i in range(0, len(raw), 2)]
    # Check for nested pair format: [[x1, y1], [x2, y2], ...]
    if all(isinstance(c, (list, tuple)) and len(c) == 2 for c in raw):
        return [Point(x=c[0], y=c[1]) for c in raw]
    raise ValueError("Unrecognized coordinate format")


def _parse_board_objects(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert raw JSON structures into typed geometry objects.

    This function transforms the normalized JSON data into proper Pydantic
    model instances for geometry objects. It's the second stage of parsing:

        Raw JSON → normalize_units() → _parse_board_objects() → Board model

    Permissive Parsing:
        This function is intentionally lenient. If a structure can't be parsed
        (e.g., malformed boundary coordinates), it sets the field to None
        rather than raising an exception. This allows validate.py to report
        a structured error (e.g., MISSING_BOUNDARY) instead of a parse failure.

    Objects Parsed:
        - boundary: Polygon (or None if malformed)
        - stackup.layers: List[Layer]
        - components.*.transform.position: Point
        - components.*.pins.*.position: Point
        - traces.*.path: Polyline
        - vias.*.center: Point
        - keepouts.*.shape: Circle or Polygon (or None if malformed)

    Args:
        data: Normalized JSON dictionary (units already in mm)

    Returns:
        Dictionary with geometry objects ready for Board model instantiation

    Challenge Requirements:
        - Task 1: Board Boundary - boundary.coordinates
        - Task 2: Components - transform positions
        - Task 3: Traces - path coordinates with width
        - Task 4: Vias - center positions
        - Task 5: Keepout Regions - shape coordinates
    """
    # Parse boundary polygon (Task 1: Board Boundary)
    # Board.boundary is Optional[Polygon] to allow validation to report
    # MISSING_BOUNDARY instead of failing at parse time
    if "boundary" in data and isinstance(data["boundary"], dict):
        coords = data["boundary"].get("coordinates")
        if coords is not None:
            try:
                data["boundary"] = Polygon(points=parse_coordinates(coords))
            except ValueError:
                # Malformed boundary - set to None for permissive parsing
                data["boundary"] = None

    # Parse stackup layers
    if "stackup" in data and isinstance(data["stackup"], dict):
        layers = data["stackup"].get("layers", [])
        data["stackup"]["layers"] = [Layer(**layer) for layer in layers]

    # Parse component transforms and pin positions (Task 2: Components)
    for comp_data in data.get("components", {}).values():
        if "transform" in comp_data:
            pos = comp_data["transform"].get("position", [0, 0])
            comp_data["transform"] = {
                "position": Point(x=pos[0], y=pos[1]),
                "rotation": comp_data["transform"].get("rotation", 0.0),
                "side": comp_data["transform"].get("side", "FRONT"),
            }
        for pin in comp_data.get("pins", {}).values():
            pos = pin.get("position", [0, 0])
            pin["position"] = Point(x=pos[0], y=pos[1])

    # Parse trace paths (Task 3: Traces)
    # Polyline minimum length constraint is relaxed during parsing;
    # validation catches MALFORMED_TRACE (< 2 points) later
    for trace in data.get("traces", {}).values():
        if isinstance(trace, dict) and "path" in trace and "coordinates" in trace["path"]:
            coords = trace["path"]["coordinates"]
            trace["path"] = Polyline(points=parse_coordinates(coords))

    # Parse via centers (Task 4: Vias)
    for via in data.get("vias", {}).values():
        if "center" in via:
            center = via["center"]
            via["center"] = Point(x=center[0], y=center[1])

    # Parse keepout shapes (Task 5: Keepout Regions)
    # Supports both circle and polygon shapes
    for keepout in data.get("keepouts", []):
        # Guard: only process if shape is a dict (not None, string, etc.)
        if "shape" in keepout and isinstance(keepout["shape"], dict):
            shape_data = keepout["shape"]
            shape_type = shape_data.get("type", "").lower()
            if shape_type == "circle":
                center = shape_data.get("center")
                radius = shape_data.get("radius")
                # Validate circle structure to avoid parse-time errors on malformed keepouts
                if (
                    isinstance(center, (list, tuple))
                    and len(center) == 2
                    and isinstance(radius, (int, float))
                ):
                    try:
                        keepout["shape"] = Circle(
                            center=Point(x=center[0], y=center[1]),
                            radius=radius,
                        )
                    except (TypeError, ValueError, IndexError):
                        # Malformed circle keepout; drop the shape for permissive parsing
                        keepout["shape"] = None
                else:
                    # Missing or invalid center/radius; drop the shape to stay permissive
                    keepout["shape"] = None
            elif "coordinates" in shape_data:
                # Polygon keepout
                coords = shape_data["coordinates"]
                keepout["shape"] = Polygon(points=parse_coordinates(coords))

    return data


def read_board_file(path: Path) -> Tuple[str | None, List[ValidationError]]:
    """Read board JSON file from disk.

    Args:
        path: Path to the input JSON file

    Returns:
        Tuple of (file_contents, errors). If file cannot be read,
        returns (None, [FILE_IO_ERROR]).

    Challenge Requirement:
        Task 6 states "Return an error if the board cannot be parsed."
        FILE_IO_ERROR handles the case where the file cannot be read.
    """
    errors: List[ValidationError] = []
    try:
        raw_text = path.read_text()
        return raw_text, errors
    except OSError as exc:
        errors.append(
            ValidationError(
                code=ErrorCode.FILE_IO_ERROR,
                severity=Severity.ERROR,
                message=f"Cannot read file: {exc}",
                json_path="$",
            )
        )
        return None, errors


def parse_board_json(raw_text: str) -> Tuple[Dict[str, Any] | None, List[ValidationError]]:
    """Parse raw JSON text into a dictionary.

    Args:
        raw_text: JSON string content

    Returns:
        Tuple of (parsed_dict, errors). If JSON is invalid,
        returns (None, [MALFORMED_JSON]).

    Challenge Requirement:
        Task 6 states "Return an error if the board cannot be parsed."
        All input files are stated to be "valid JSON files" but we handle
        malformed JSON gracefully with MALFORMED_JSON error.
    """
    errors: List[ValidationError] = []
    try:
        data = json.loads(raw_text)
        return data, errors
    except json.JSONDecodeError as exc:
        errors.append(
            ValidationError(
                code=ErrorCode.MALFORMED_JSON,
                severity=Severity.ERROR,
                message=f"Invalid JSON: {exc}",
                json_path="$",
            )
        )
        return None, errors


def parse_board_data(data: Dict[str, Any]) -> Tuple[Board | None, List[ValidationError]]:
    """Parse JSON dictionary into a Board model.

    This is the main parsing entry point that orchestrates:
    1. Unit normalization (MICRON/MILLIMETER → mm)
    2. Object parsing (raw dicts → typed geometry objects)
    3. Pydantic model instantiation

    Args:
        data: Raw parsed JSON dictionary

    Returns:
        Tuple of (Board, errors). If parsing fails completely,
        returns (None, errors).

    Note:
        Pydantic models use extra="ignore" to allow unknown fields.
        This makes parsing permissive - semantic validation happens in validate.py.
    """
    errors: List[ValidationError] = []
    data, unit_errors = normalize_units(data)
    errors.extend(unit_errors)
    if unit_errors:
        return None, errors

    try:
        parsed = _parse_board_objects(data)
        board = Board(**parsed)
        return board, errors
    except Exception as exc:  # pragma: no cover - converted to structured error
        errors.append(
            ValidationError(
                code=ErrorCode.PARSE_ERROR,
                severity=Severity.ERROR,
                message=f"Failed to parse board: {exc}",
                json_path="$",
            )
        )
        return None, errors


def load_board(path: Path) -> Tuple[Board | None, List[ValidationError]]:
    """Load and parse a board from a JSON file.

    This is the top-level entry point for loading boards. It chains together:
    1. read_board_file() - Read file from disk
    2. parse_board_json() - Parse JSON text
    3. parse_board_data() - Normalize units and create Board model

    Args:
        path: Path to the input JSON board file

    Returns:
        Tuple of (Board, errors). If any stage fails, returns (None, errors)
        with accumulated errors from all stages.

    Usage:
        board, errors = load_board(Path("board.json"))
        if errors:
            for err in errors:
                print(err)
        if board:
            # proceed with validation/rendering
    """
    errors: List[ValidationError] = []
    raw_text, file_errors = read_board_file(path)
    errors.extend(file_errors)
    if file_errors or raw_text is None:
        return None, errors

    data, json_errors = parse_board_json(raw_text)
    errors.extend(json_errors)
    if json_errors or data is None:
        return None, errors

    board, parse_errors = parse_board_data(data)
    errors.extend(parse_errors)
    return board, errors
