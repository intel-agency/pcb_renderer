"""Structured validation errors and codes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum


class ErrorCode(str, Enum):
    MISSING_BOUNDARY = "MISSING_BOUNDARY"
    MALFORMED_COORDINATES = "MALFORMED_COORDINATES"
    INVALID_ROTATION = "INVALID_ROTATION"
    DANGLING_TRACE = "DANGLING_TRACE"
    NEGATIVE_WIDTH = "NEGATIVE_WIDTH"
    EMPTY_BOARD = "EMPTY_BOARD"
    INVALID_VIA_GEOMETRY = "INVALID_VIA_GEOMETRY"
    NONEXISTENT_LAYER = "NONEXISTENT_LAYER"
    NONEXISTENT_NET = "NONEXISTENT_NET"
    SELF_INTERSECTING_BOUNDARY = "SELF_INTERSECTING_BOUNDARY"
    COMPONENT_OUTSIDE_BOUNDARY = "COMPONENT_OUTSIDE_BOUNDARY"
    INVALID_PIN_REFERENCE = "INVALID_PIN_REFERENCE"
    MALFORMED_STACKUP = "MALFORMED_STACKUP"
    INVALID_UNIT_SPECIFICATION = "INVALID_UNIT_SPECIFICATION"
    MALFORMED_TRACE = "MALFORMED_TRACE"
    MALFORMED_JSON = "MALFORMED_JSON"
    FILE_IO_ERROR = "FILE_IO_ERROR"
    PARSE_ERROR = "PARSE_ERROR"


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationError:
    """Structured validation error."""

    code: ErrorCode
    severity: Severity
    message: str
    json_path: str
    context: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:  # pragma: no cover
        ctx = f" context={self.context}" if self.context else ""
        return f"[{self.severity}] {self.code}: {self.message} at {self.json_path}{ctx}"
