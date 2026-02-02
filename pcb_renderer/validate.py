"""Board validation implementing required error codes."""

from __future__ import annotations

from typing import List

from .errors import ErrorCode, Severity, ValidationError
from .geometry import Point, Polygon
from .models import Board


def validate_board(board: Board) -> List[ValidationError]:
    errors: List[ValidationError] = []

    if not board.boundary or len(board.boundary.points) < 3:
        errors.append(
            ValidationError(
                code=ErrorCode.MISSING_BOUNDARY,
                severity=Severity.ERROR,
                message="Board has no boundary defined",
                json_path="$.boundary",
            )
        )

    net_names = {net.name for net in board.nets}
    layer_names = {layer.name for layer in board.stackup.get("layers", [])}

    for trace_id, trace in board.traces.items():
        if trace.path and len(trace.path.points) < 2:
            errors.append(
                ValidationError(
                    code=ErrorCode.MALFORMED_TRACE,
                    severity=Severity.ERROR,
                    message=f"Trace {trace_id} must contain at least 2 points",
                    json_path=f"$.traces.{trace_id}.path.coordinates",
                )
            )
        if trace.net_name not in net_names:
            errors.append(
                ValidationError(
                    code=ErrorCode.DANGLING_TRACE,
                    severity=Severity.ERROR,
                    message=f"Trace {trace_id} references unknown net {trace.net_name}",
                    json_path=f"$.traces.{trace_id}.net_name",
                )
            )
        if trace.layer_hash not in layer_names:
            errors.append(
                ValidationError(
                    code=ErrorCode.NONEXISTENT_LAYER,
                    severity=Severity.ERROR,
                    message=f"Trace {trace_id} references unknown layer {trace.layer_hash}",
                    json_path=f"$.traces.{trace_id}.layer_hash",
                )
            )
        if trace.width <= 0:
            errors.append(
                ValidationError(
                    code=ErrorCode.NEGATIVE_WIDTH,
                    severity=Severity.ERROR,
                    message=f"Trace {trace_id} width must be positive",
                    json_path=f"$.traces.{trace_id}.width",
                )
            )

    for via_id, via in board.vias.items():
        if via.net_name not in net_names:
            errors.append(
                ValidationError(
                    code=ErrorCode.NONEXISTENT_NET,
                    severity=Severity.ERROR,
                    message=f"Via {via_id} references unknown net {via.net_name}",
                    json_path=f"$.vias.{via_id}.net_name",
                )
            )
        if via.hole_size >= via.diameter:
            errors.append(
                ValidationError(
                    code=ErrorCode.INVALID_VIA_GEOMETRY,
                    severity=Severity.ERROR,
                    message=f"Via {via_id} hole_size must be smaller than diameter",
                    json_path=f"$.vias.{via_id}.hole_size",
                )
            )
        start = via.span.get("start_layer")
        end = via.span.get("end_layer")
        if start not in layer_names or end not in layer_names:
            errors.append(
                ValidationError(
                    code=ErrorCode.NONEXISTENT_LAYER,
                    severity=Severity.ERROR,
                    message=f"Via {via_id} references unknown layer",
                    json_path=f"$.vias.{via_id}.span",
                )
            )

    if not board.components and not board.traces:
        errors.append(
            ValidationError(
                code=ErrorCode.EMPTY_BOARD,
                severity=Severity.ERROR,
                message="Board has no components or traces",
                json_path="$",
            )
        )

    if board.boundary and is_self_intersecting(board.boundary):
        errors.append(
            ValidationError(
                code=ErrorCode.SELF_INTERSECTING_BOUNDARY,
                severity=Severity.ERROR,
                message="Board boundary self-intersects",
                json_path="$.boundary.coordinates",
            )
        )

    if board.boundary:
        for comp_name, comp in board.components.items():
            if not board.boundary.contains_point(comp.transform.position):
                errors.append(
                    ValidationError(
                        code=ErrorCode.COMPONENT_OUTSIDE_BOUNDARY,
                        severity=Severity.ERROR,
                        message=f"Component {comp_name} lies outside boundary",
                        json_path=f"$.components.{comp_name}.transform.position",
                    )
                )
            if not 0 <= comp.transform.rotation <= 360:
                errors.append(
                    ValidationError(
                        code=ErrorCode.INVALID_ROTATION,
                        severity=Severity.ERROR,
                        message=f"Component {comp_name} rotation must be 0-360",
                        json_path=f"$.components.{comp_name}.transform.rotation",
                    )
                )
            for pin_name, pin in comp.pins.items():
                if pin.comp_name != comp.name:
                    errors.append(
                        ValidationError(
                            code=ErrorCode.INVALID_PIN_REFERENCE,
                            severity=Severity.ERROR,
                            message=f"Pin {pin_name} references {pin.comp_name} not {comp.name}",
                            json_path=f"$.components.{comp_name}.pins.{pin_name}.comp_name",
                        )
                    )
                if pin.net_name not in net_names:
                    errors.append(
                        ValidationError(
                            code=ErrorCode.NONEXISTENT_NET,
                            severity=Severity.ERROR,
                            message=f"Pin {pin_name} references unknown net {pin.net_name}",
                            json_path=f"$.components.{comp_name}.pins.{pin_name}.net_name",
                        )
                    )

    if "layers" not in board.stackup or not board.stackup.get("layers"):
        errors.append(
            ValidationError(
                code=ErrorCode.MALFORMED_STACKUP,
                severity=Severity.ERROR,
                message="Stackup has no layers",
                json_path="$.stackup.layers",
            )
        )
    else:
        indices = sorted(layer.index for layer in board.stackup.get("layers", []))
        if indices != list(range(indices[0], indices[0] + len(indices))):
            errors.append(
                ValidationError(
                    code=ErrorCode.MALFORMED_STACKUP,
                    severity=Severity.ERROR,
                    message="Stackup layer indices are not contiguous",
                    json_path="$.stackup.layers",
                )
            )

    return errors


def is_self_intersecting(polygon: Polygon) -> bool:
    def segments_intersect(a1: Point, a2: Point, b1: Point, b2: Point) -> bool:
        def orient(p: Point, q: Point, r: Point) -> float:
            return (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y)

        def on_segment(p: Point, q: Point, r: Point) -> bool:
            return min(p.x, r.x) <= q.x <= max(p.x, r.x) and min(p.y, r.y) <= q.y <= max(p.y, r.y)

        o1 = orient(a1, a2, b1)
        o2 = orient(a1, a2, b2)
        o3 = orient(b1, b2, a1)
        o4 = orient(b1, b2, a2)

        if o1 * o2 < 0 and o3 * o4 < 0:
            return True
        if o1 == 0 and on_segment(a1, b1, a2):
            return True
        if o2 == 0 and on_segment(a1, b2, a2):
            return True
        if o3 == 0 and on_segment(b1, a1, b2):
            return True
        if o4 == 0 and on_segment(b1, a2, b2):
            return True
        return False

    edges = list(polygon.edges())
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            a1, a2 = edges[i]
            b1, b2 = edges[j]
            if a1 == b1 or a1 == b2 or a2 == b1 or a2 == b2:
                continue
            if segments_intersect(a1, a2, b1, b2):
                return True
    return False
