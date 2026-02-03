"""Board validation implementing the 14 required error codes.

This module handles the second stage of the PCB Renderer pipeline:

    Board model → validate.py → List[ValidationError]

Design Philosophy:
------------------
**Validation is authoritative; parsing is permissive.**

While parsing (parse.py) tries to create a Board object even from malformed
input, validation enforces all semantic rules and reports ALL violations.
This separation enables:

1. Complete error reporting (all issues found in one pass)
2. Rich context for debugging (JSON paths, available options)
3. --permissive mode (render despite validation errors)
4. LLM integration (explain errors, suggest fixes)

Challenge Requirements:
-----------------------
From the Quilter Backend Engineer Code Challenge:

"14 of the invalid boards should be detected through validation of the data
content (missing fields, invalid references, bad geometry, etc.)"

This module implements checks for all 14 error types:

| Error Code                    | Check Description                           |
|-------------------------------|---------------------------------------------|
| MISSING_BOUNDARY              | Board has no boundary polygon               |
| SELF_INTERSECTING_BOUNDARY    | Boundary polygon crosses itself             |
| COMPONENT_OUTSIDE_BOUNDARY    | Component center outside board bounds       |
| INVALID_ROTATION              | Component rotation not in 0-360 range       |
| DANGLING_TRACE                | Trace references non-existent net           |
| NONEXISTENT_NET               | Pin/via references unknown net              |
| NONEXISTENT_LAYER             | Trace/via references unknown layer          |
| INVALID_VIA_GEOMETRY          | Via hole_size >= diameter                   |
| MALFORMED_TRACE               | Trace with < 2 points                       |
| NEGATIVE_WIDTH                | Trace width <= 0                            |
| EMPTY_BOARD                   | No components or traces                     |
| INVALID_PIN_REFERENCE         | Pin's comp_name doesn't match component     |
| MALFORMED_STACKUP             | Layer indices not contiguous                |
| MALFORMED_COORDINATES         | (Handled in parse.py)                       |

Validation Order:
-----------------
Checks are organized by category (CHECKS_RUN constant):
1. boundary   - Boundary existence and self-intersection
2. references - Net and layer reference validity
3. geometry   - Trace paths, via dimensions, component placement
4. stackup    - Layer index contiguity
5. rotation   - Component rotation bounds
6. pins       - Pin reference validity
"""

from __future__ import annotations

from typing import List

from .errors import ErrorCode, Severity, ValidationError
from .geometry import Point, Polygon
from .models import Board


# Categories of validation checks run (used in export JSON)
CHECKS_RUN = [
    "boundary",  # MISSING_BOUNDARY, SELF_INTERSECTING_BOUNDARY
    "references",  # DANGLING_TRACE, NONEXISTENT_NET, NONEXISTENT_LAYER
    "geometry",  # MALFORMED_TRACE, NEGATIVE_WIDTH, INVALID_VIA_GEOMETRY, COMPONENT_OUTSIDE_BOUNDARY
    "stackup",  # MALFORMED_STACKUP
    "rotation",  # INVALID_ROTATION
    "pins",  # INVALID_PIN_REFERENCE, NONEXISTENT_NET (pins)
]


def validate_board(board: Board) -> List[ValidationError]:
    """Validate a parsed board and return all validation errors.

    This function runs all semantic validation checks on a Board object
    and returns a list of ValidationError instances. Unlike exceptions,
    this approach allows collecting ALL errors in a single pass.

    Args:
        board: Parsed Board model from parse.py

    Returns:
        List of ValidationError objects. Empty list means board is valid.

    Challenge Requirements:
        Implements the "14 invalid board errors" from the challenge spec.
        Each check corresponds to one of the ErrorCode enum values.

    Validation Flow:
        1. Check boundary existence (Task 1: Board Boundary)
        2. Build reference sets (nets, layers) for cross-validation
        3. Validate traces (Task 3: Traces) - net refs, layer refs, geometry
        4. Validate vias (Task 4: Vias) - net refs, geometry, layer spans
        5. Check for empty board
        6. Check boundary self-intersection
        7. Validate components (Task 2: Components) - positions, rotations, pins
        8. Validate stackup layer indices
    """
    errors: List[ValidationError] = []

    # === BOUNDARY CHECKS ===
    # Task 1: Board Boundary - verify boundary exists and is valid
    if not board.boundary or len(board.boundary.points) < 3:
        errors.append(
            ValidationError(
                code=ErrorCode.MISSING_BOUNDARY,
                severity=Severity.ERROR,
                message="Board has no boundary defined",
                json_path="$.boundary",
            )
        )

    # === BUILD REFERENCE SETS ===
    # Used for cross-referencing traces, vias, and pins against defined nets/layers
    net_names = {net.name for net in board.nets}
    layer_names = {layer.name for layer in board.stackup.get("layers", [])}

    # === TRACE VALIDATION ===
    # Task 3: Traces - validate paths, net refs, layer refs, widths
    for trace_id, trace in board.traces.items():
        # Check for malformed trace (< 2 points)
        if trace.path and len(trace.path.points) < 2:
            errors.append(
                ValidationError(
                    code=ErrorCode.MALFORMED_TRACE,
                    severity=Severity.ERROR,
                    message=f"Trace {trace_id} must contain at least 2 points",
                    json_path=f"$.traces.{trace_id}.path.coordinates",
                    context={"trace_id": trace_id, "point_count": len(trace.path.points) if trace.path else 0},
                )
            )
        # Check for dangling trace (references non-existent net)
        if trace.net_name not in net_names:
            errors.append(
                ValidationError(
                    code=ErrorCode.DANGLING_TRACE,
                    severity=Severity.ERROR,
                    message=f"Trace {trace_id} references unknown net {trace.net_name}",
                    json_path=f"$.traces.{trace_id}.net_name",
                    context={"trace_id": trace_id, "referenced_net": trace.net_name, "available_nets": sorted(net_names)},
                )
            )
        # Check for non-existent layer reference
        if trace.layer_hash not in layer_names:
            errors.append(
                ValidationError(
                    code=ErrorCode.NONEXISTENT_LAYER,
                    severity=Severity.ERROR,
                    message=f"Trace {trace_id} references unknown layer {trace.layer_hash}",
                    json_path=f"$.traces.{trace_id}.layer_hash",
                    context={"trace_id": trace_id, "referenced_layer": trace.layer_hash, "available_layers": sorted(layer_names)},
                )
            )
        # Check for negative/zero width
        if trace.width <= 0:
            errors.append(
                ValidationError(
                    code=ErrorCode.NEGATIVE_WIDTH,
                    severity=Severity.ERROR,
                    message=f"Trace {trace_id} width must be positive",
                    json_path=f"$.traces.{trace_id}.width",
                    context={"trace_id": trace_id, "width": trace.width},
                )
            )

    # === VIA VALIDATION ===
    # Task 4: Vias - validate net refs, geometry, layer spans
    for via_id, via in board.vias.items():
        # Check for non-existent net reference
        if via.net_name not in net_names:
            errors.append(
                ValidationError(
                    code=ErrorCode.NONEXISTENT_NET,
                    severity=Severity.ERROR,
                    message=f"Via {via_id} references unknown net {via.net_name}",
                    json_path=f"$.vias.{via_id}.net_name",
                    context={"via_id": via_id, "referenced_net": via.net_name, "available_nets": sorted(net_names)},
                )
            )
        # Check for invalid geometry (hole >= diameter)
        if via.hole_size >= via.diameter:
            errors.append(
                ValidationError(
                    code=ErrorCode.INVALID_VIA_GEOMETRY,
                    severity=Severity.ERROR,
                    message=f"Via {via_id} hole_size must be smaller than diameter",
                    json_path=f"$.vias.{via_id}.hole_size",
                    context={"via_id": via_id, "hole_size": via.hole_size, "diameter": via.diameter},
                )
            )
        # Check for non-existent layer in span
        start = via.span.get("start_layer")
        end = via.span.get("end_layer")
        if start not in layer_names or end not in layer_names:
            errors.append(
                ValidationError(
                    code=ErrorCode.NONEXISTENT_LAYER,
                    severity=Severity.ERROR,
                    message=f"Via {via_id} references unknown layer",
                    json_path=f"$.vias.{via_id}.span",
                    context={"via_id": via_id, "start_layer": start, "end_layer": end, "available_layers": sorted(layer_names)},
                )
            )

    # === EMPTY BOARD CHECK ===
    if not board.components and not board.traces:
        errors.append(
            ValidationError(
                code=ErrorCode.EMPTY_BOARD,
                severity=Severity.ERROR,
                message="Board has no components or traces",
                json_path="$",
            )
        )

    # === SELF-INTERSECTION CHECK ===
    if board.boundary and is_self_intersecting(board.boundary):
        errors.append(
            ValidationError(
                code=ErrorCode.SELF_INTERSECTING_BOUNDARY,
                severity=Severity.ERROR,
                message="Board boundary self-intersects",
                json_path="$.boundary.coordinates",
            )
        )

    # === COMPONENT VALIDATION ===
    # Task 2: Components - validate positions, rotations, and pin references
    if board.boundary:
        for comp_name, comp in board.components.items():
            # Check if component center is outside boundary
            if not board.boundary.contains_point(comp.transform.position):
                errors.append(
                    ValidationError(
                        code=ErrorCode.COMPONENT_OUTSIDE_BOUNDARY,
                        severity=Severity.ERROR,
                        message=f"Component {comp_name} lies outside boundary",
                        json_path=f"$.components.{comp_name}.transform.position",
                        context={"component": comp_name, "position": [comp.transform.position.x, comp.transform.position.y]},
                    )
                )
            # Check for invalid rotation (must be 0-360)
            if not 0 <= comp.transform.rotation <= 360:
                errors.append(
                    ValidationError(
                        code=ErrorCode.INVALID_ROTATION,
                        severity=Severity.ERROR,
                        message=f"Component {comp_name} rotation must be 0-360",
                        json_path=f"$.components.{comp_name}.transform.rotation",
                        context={"component": comp_name, "rotation": comp.transform.rotation},
                    )
                )
            # Validate pin references
            for pin_name, pin in comp.pins.items():
                # Check if pin's comp_name matches parent component
                if pin.comp_name != comp.name:
                    errors.append(
                        ValidationError(
                            code=ErrorCode.INVALID_PIN_REFERENCE,
                            severity=Severity.ERROR,
                            message=f"Pin {pin_name} references {pin.comp_name} not {comp.name}",
                            json_path=f"$.components.{comp_name}.pins.{pin_name}.comp_name",
                            context={"component": comp_name, "pin": pin_name, "comp_name": pin.comp_name},
                        )
                    )
                # Check if pin references non-existent net
                if pin.net_name not in net_names:
                    errors.append(
                        ValidationError(
                            code=ErrorCode.NONEXISTENT_NET,
                            severity=Severity.ERROR,
                            message=f"Pin {pin_name} references unknown net {pin.net_name}",
                            json_path=f"$.components.{comp_name}.pins.{pin_name}.net_name",
                            context={"component": comp_name, "pin": pin_name, "referenced_net": pin.net_name, "available_nets": sorted(net_names)},
                        )
                    )

    # === STACKUP VALIDATION ===
    # Check for contiguous layer indices
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
        # Layer indices must be contiguous (no gaps)
        if indices != list(range(indices[0], indices[0] + len(indices))):
            errors.append(
                ValidationError(
                    code=ErrorCode.MALFORMED_STACKUP,
                    severity=Severity.ERROR,
                    message="Stackup layer indices are not contiguous",
                    json_path="$.stackup.layers",
                    context={"indices": indices},
                )
            )

    return errors


def is_self_intersecting(polygon: Polygon) -> bool:
    """Check if a polygon's edges intersect (excluding shared vertices).

    Uses the orientation method to detect line segment intersections.
    Two non-adjacent edges intersecting indicates a self-intersecting boundary,
    which triggers SELF_INTERSECTING_BOUNDARY error.

    Args:
        polygon: Polygon to check

    Returns:
        True if polygon self-intersects, False otherwise

    Algorithm:
        For each pair of non-adjacent edges, check if they intersect using
        the cross-product orientation test. Adjacent edges (sharing a vertex)
        are skipped since they intersect at their common endpoint by definition.
    """

    def segments_intersect(a1: Point, a2: Point, b1: Point, b2: Point) -> bool:
        """Check if line segment (a1, a2) intersects segment (b1, b2).

        Uses the orientation method: if two endpoints of one segment lie on
        opposite sides of the other segment's line (and vice versa), they intersect.
        """

        def orient(p: Point, q: Point, r: Point) -> float:
            """Compute orientation of triplet (p, q, r).

            Returns:
                > 0 if counterclockwise
                < 0 if clockwise
                = 0 if collinear
            """
            return (q.y - p.y) * (r.x - q.x) - (q.x - p.x) * (r.y - q.y)

        def on_segment(p: Point, q: Point, r: Point) -> bool:
            """Check if point q lies on segment (p, r) when collinear."""
            return min(p.x, r.x) <= q.x <= max(p.x, r.x) and min(p.y, r.y) <= q.y <= max(p.y, r.y)

        # Compute orientations for intersection test
        o1 = orient(a1, a2, b1)
        o2 = orient(a1, a2, b2)
        o3 = orient(b1, b2, a1)
        o4 = orient(b1, b2, a2)

        # General case: segments straddle each other
        if o1 * o2 < 0 and o3 * o4 < 0:
            return True

        # Collinear special cases
        if o1 == 0 and on_segment(a1, b1, a2):
            return True
        if o2 == 0 and on_segment(a1, b2, a2):
            return True
        if o3 == 0 and on_segment(b1, a1, b2):
            return True
        if o4 == 0 and on_segment(b1, a2, b2):
            return True
        return False

    # Get all edges of the polygon
    edges = list(polygon.edges())

    # Check every pair of edges for intersection
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            a1, a2 = edges[i]
            b1, b2 = edges[j]
            # Skip adjacent edges (they share a vertex)
            if a1 == b1 or a1 == b2 or a2 == b1 or a2 == b2:
                continue
            if segments_intersect(a1, a2, b1, b2):
                return True
    return False
