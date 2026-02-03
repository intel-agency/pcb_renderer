"""Structured validation errors and error codes for PCB board validation.

This module defines the error system used throughout PCB Renderer to report
validation issues in a structured, machine-readable format. The design philosophy
is to return structured errors rather than raise exceptions, enabling:

1. Collection of ALL validation issues in a single pass (not just the first error)
2. Rich context for error reporting (JSON paths, available options, etc.)
3. Integration with LLM plugin for natural-language explanations
4. Export to JSON for external tooling

Architecture Notes:
-------------------
- ErrorCode enum: 18 distinct error types covering the "14 invalid board errors"
  from the challenge specification, plus parse-time errors
- Severity enum: ERROR (blocks rendering), WARNING (informational), INFO
- ValidationError dataclass: Unified error structure with context

Error Categories (per Quilter Backend Engineer Code Challenge):
---------------------------------------------------------------
The challenge requires detecting 14 types of invalid boards through validation:

1. MISSING_BOUNDARY       - Board has no boundary defined
2. MALFORMED_COORDINATES  - Invalid coordinate format
3. SELF_INTERSECTING_BOUNDARY - Boundary polygon crosses itself
4. COMPONENT_OUTSIDE_BOUNDARY - Component center not within board bounds
5. INVALID_ROTATION       - Rotation not in 0-360 range
6. DANGLING_TRACE         - Trace references non-existent net
7. NONEXISTENT_NET        - Pin/via references unknown net
8. NONEXISTENT_LAYER      - Trace/via references unknown layer
9. INVALID_VIA_GEOMETRY   - Via hole_size >= diameter
10. MALFORMED_TRACE       - Trace with < 2 points
11. NEGATIVE_WIDTH        - Trace width <= 0
12. EMPTY_BOARD           - No components or traces
13. INVALID_PIN_REFERENCE - Pin's comp_name doesn't match parent component
14. MALFORMED_STACKUP     - Layer indices not contiguous or missing

Additional parse-time errors:
- INVALID_UNIT_SPECIFICATION - designUnits not MICRON/MILLIMETER
- MALFORMED_JSON             - Invalid JSON syntax
- FILE_IO_ERROR              - Cannot read input file
- PARSE_ERROR                - General parsing failure
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for board validation.

    These codes map to the 14 invalid board error types from the challenge spec,
    plus additional parse-time errors. Each code has a corresponding check in
    validate.py or parse.py.
    """

    # Boundary/geometry errors (Challenge items 1-4)
    MISSING_BOUNDARY = "MISSING_BOUNDARY"
    MALFORMED_COORDINATES = "MALFORMED_COORDINATES"
    SELF_INTERSECTING_BOUNDARY = "SELF_INTERSECTING_BOUNDARY"
    COMPONENT_OUTSIDE_BOUNDARY = "COMPONENT_OUTSIDE_BOUNDARY"

    # Component/rotation errors (Challenge item 5)
    INVALID_ROTATION = "INVALID_ROTATION"

    # Reference errors (Challenge items 6-8)
    DANGLING_TRACE = "DANGLING_TRACE"
    NONEXISTENT_NET = "NONEXISTENT_NET"
    NONEXISTENT_LAYER = "NONEXISTENT_LAYER"

    # Via errors (Challenge item 9)
    INVALID_VIA_GEOMETRY = "INVALID_VIA_GEOMETRY"

    # Trace errors (Challenge items 10-11)
    MALFORMED_TRACE = "MALFORMED_TRACE"
    NEGATIVE_WIDTH = "NEGATIVE_WIDTH"

    # Board structure errors (Challenge items 12-14)
    EMPTY_BOARD = "EMPTY_BOARD"
    INVALID_PIN_REFERENCE = "INVALID_PIN_REFERENCE"
    MALFORMED_STACKUP = "MALFORMED_STACKUP"

    # Unit/parse errors (additional)
    INVALID_UNIT_SPECIFICATION = "INVALID_UNIT_SPECIFICATION"
    MALFORMED_JSON = "MALFORMED_JSON"
    FILE_IO_ERROR = "FILE_IO_ERROR"
    PARSE_ERROR = "PARSE_ERROR"


class Severity(str, Enum):
    """Severity levels for validation errors.

    ERROR: Blocks rendering (unless --permissive mode)
    WARNING: Informational, doesn't block rendering
    INFO: Purely informational
    """

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationError:
    """Structured validation error with context for debugging and LLM integration.

    Attributes:
        code: Error type from ErrorCode enum
        severity: ERROR/WARNING/INFO
        message: Human-readable description
        json_path: JSONPath to the problematic field (e.g. "$.traces.T1.net_name")
        context: Optional dict with additional metadata for debugging:
                 - trace_id, point_count (for trace errors)
                 - referenced_net, available_nets (for net reference errors)
                 - component, position (for placement errors)

    The json_path follows JSONPath syntax for precise error location.
    Context is consumed by the LLM plugin for generating fix suggestions.
    """

    code: ErrorCode
    severity: Severity
    message: str
    json_path: str
    context: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:  # pragma: no cover
        ctx = f" context={self.context}" if self.context else ""
        return f"[{self.severity}] {self.code}: {self.message} at {self.json_path}{ctx}"
