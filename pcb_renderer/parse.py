"""Parsing and unit normalization for board JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .errors import ErrorCode, Severity, ValidationError
from .geometry import Circle, Point, Polygon, Polyline
from .models import Board, Layer

MICRON_TO_MM = 0.001


def _scale_value(value: Any, scale: float) -> Any:
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
    if not raw:
        raise ValueError("Empty coordinate array")
    if all(isinstance(c, (int, float)) for c in raw):
        if len(raw) % 2 != 0:
            raise ValueError("Flat coordinate list must have even length")
        return [Point(x=raw[i], y=raw[i + 1]) for i in range(0, len(raw), 2)]
    if all(isinstance(c, (list, tuple)) and len(c) == 2 for c in raw):
        return [Point(x=c[0], y=c[1]) for c in raw]
    raise ValueError("Unrecognized coordinate format")


def _parse_board_objects(data: Dict[str, Any]) -> Dict[str, Any]:
    if "boundary" in data and isinstance(data["boundary"], dict):
        coords = data["boundary"].get("coordinates")
        if coords is not None:
            try:
                data["boundary"] = Polygon(points=parse_coordinates(coords))
            except ValueError:
                data["boundary"] = None

    if "stackup" in data and isinstance(data["stackup"], dict):
        layers = data["stackup"].get("layers", [])
        data["stackup"]["layers"] = [Layer(**layer) for layer in layers]

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

    for trace in data.get("traces", {}).values():
        if isinstance(trace, dict) and "path" in trace and "coordinates" in trace["path"]:
            coords = trace["path"]["coordinates"]
            trace["path"] = Polyline(points=parse_coordinates(coords))

    for via in data.get("vias", {}).values():
        if "center" in via:
            center = via["center"]
            via["center"] = Point(x=center[0], y=center[1])

    for keepout in data.get("keepouts", []):
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
                coords = shape_data["coordinates"]
                keepout["shape"] = Polygon(points=parse_coordinates(coords))

    return data


def read_board_file(path: Path) -> Tuple[str | None, List[ValidationError]]:
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
