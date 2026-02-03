"""Geometric primitives with validation.

This module provides the fundamental geometric types used throughout the
PCB Renderer pipeline. All coordinates are in millimeters after parsing.

Primitive Types:
---------------
- Point:    2D coordinate (x, y) in millimeters
- Polygon:  Closed shape with ≥3 points (boundary, keepouts)
- Polyline: Open path with ≥2 points (traces)
- Circle:   Circle primitive for round keepouts and pads

Key Design Decisions:
--------------------
1. **Immutable Points**: Point uses `frozen=True` to prevent accidental mutation
   after creation. This ensures coordinates remain stable during transforms.

2. **NaN Rejection**: Point coordinates must be finite (no NaN or Inf).
   This catches malformed coordinate data early in the pipeline.
   Related: MALFORMED_COORDINATES error from challenge doc.

3. **Auto-closing Polygons**: If polygon points don't form a closed loop,
   the validator automatically appends the first point to close it.

4. **Relaxed Polyline**: Polyline doesn't strictly enforce min_length=2
   at model level; MALFORMED_TRACE is detected in validate.py.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Tuple

import numpy as np
from pydantic import BaseModel, Field, field_validator


class Point(BaseModel):
    """2D point in millimeters.

    All PCB coordinates are stored in millimeters after unit normalization.
    Points are immutable (frozen) to prevent accidental modifications.

    Attributes:
        x: X-coordinate in millimeters
        y: Y-coordinate in millimeters

    Validation:
        Rejects NaN and Infinity values to detect malformed coordinate data.
        Related: MALFORMED_COORDINATES error from challenge doc.

    Example:
        >>> p1 = Point(x=10.0, y=20.0)
        >>> p2 = Point(x=15.0, y=25.0)
        >>> p1.distance_to(p2)  # ~7.07 mm
    """

    x: float
    y: float

    model_config = {"frozen": True}  # Immutable after creation

    @field_validator("x", "y")
    @classmethod
    def validate_finite(cls, value: float) -> float:
        """Reject NaN and Infinity coordinates.

        Challenge Doc: Malformed coordinates should be detected and reported.
        """
        if not math.isfinite(value):
            raise ValueError(f"Coordinate must be finite, got {value}")
        return value

    def __add__(self, other: Point) -> Point:
        """Vector addition of two points."""
        return Point(x=self.x + other.x, y=self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        """Vector subtraction of two points."""
        return Point(x=self.x - other.x, y=self.y - other.y)

    def __mul__(self, scalar: float) -> Point:
        """Scalar multiplication of point coordinates."""
        return Point(x=self.x * scalar, y=self.y * scalar)

    def distance_to(self, other: Point) -> float:
        """Euclidean distance to another point in millimeters."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.hypot(dx, dy)

    def rotate(self, angle_deg: float, origin: Point | None = None) -> Point:
        """Rotate point around an origin by the given angle.

        Args:
            angle_deg: Rotation angle in degrees (counterclockwise positive)
            origin: Center of rotation (default: (0, 0))

        Returns:
            New Point at rotated position
        """
        origin = origin or Point(x=0, y=0)
        angle_rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        # Translate to origin, rotate, translate back
        px, py = self.x - origin.x, self.y - origin.y
        rx = px * cos_a - py * sin_a
        ry = px * sin_a + py * cos_a
        return Point(x=rx + origin.x, y=ry + origin.y)

    def mirror_x(self) -> Point:
        """Mirror point across Y-axis (negate X coordinate).

        Used for BACK side components that need horizontal mirroring.
        """
        return Point(x=-self.x, y=self.y)

    def to_array(self) -> np.ndarray:
        """Convert to numpy array [x, y] for matrix operations."""
        return np.array([self.x, self.y])


class Polygon(BaseModel):
    """Closed polygon with ≥3 points.

    Used for board boundaries, keepout regions, and component outlines.
    The polygon is automatically closed if the last point doesn't match the first.

    Attributes:
        points: List of vertices in order (first==last after validation)

    Validation:
        - MISSING_BOUNDARY: Board has no boundary polygon
        - SELF_INTERSECTING_BOUNDARY: Polygon edges cross each other
          (detected in validate.py using is_self_intersecting())

    Example:
        >>> boundary = Polygon(points=[Point(0,0), Point(100,0), Point(100,80), Point(0,80)])
        >>> boundary.bbox()  # (0.0, 0.0, 100.0, 80.0)
    """

    points: List[Point] = Field(..., min_length=3)

    @field_validator("points")
    @classmethod
    def validate_polygon(cls, value: List[Point]) -> List[Point]:
        """Validate polygon has ≥3 points and auto-close if needed."""
        if len(value) < 3:
            raise ValueError("Polygon must have at least 3 points")
        # Auto-close polygon if first != last
        if value[0] != value[-1]:
            value.append(value[0])
        return value

    def bbox(self) -> Tuple[float, float, float, float]:
        """Return bounding box as (min_x, min_y, max_x, max_y)."""
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)

    def contains_point(self, point: Point) -> bool:
        """Check if a point is inside the polygon using ray casting algorithm.

        Used for COMPONENT_OUTSIDE_BOUNDARY validation.
        """
        x, y = point.x, point.y
        n = len(self.points) - 1  # -1 because last point == first
        inside = False
        p1 = self.points[0]
        for i in range(1, n + 1):
            p2 = self.points[i]
            # Ray casting: count edge crossings
            if ((p1.y > y) != (p2.y > y)) and (
                x < (p2.x - p1.x) * (y - p1.y) / (p2.y - p1.y) + p1.x
            ):
                inside = not inside
            p1 = p2
        return inside

    def edges(self) -> Iterable[tuple[Point, Point]]:
        """Iterate over polygon edges as (start, end) point pairs.

        Used by is_self_intersecting() to check for crossing edges.
        """
        for i in range(len(self.points) - 1):
            yield self.points[i], self.points[i + 1]

    def to_xy_lists(self) -> Tuple[List[float], List[float]]:
        """Convert to separate X and Y coordinate lists for plotting."""
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return xs, ys


class Polyline(BaseModel):
    """Open path with ≥2 points.

    Used for trace paths in the PCB. Unlike Polygon, Polyline is not closed.

    Attributes:
        points: Ordered list of path vertices

    Validation:
        MALFORMED_TRACE error if path has < 2 points.
        Note: min_length is not strictly enforced at model level to support
        permissive parsing; validation happens in validate.py.

    Example:
        >>> trace_path = Polyline(points=[Point(0,0), Point(50,0), Point(50,50)])
        >>> trace_path.length()  # 100.0 mm
    """

    points: List[Point] = Field(default_factory=list)

    def length(self) -> float:
        """Calculate total path length in millimeters.

        Used by stats.py to compute trace_length_total_mm.
        """
        return sum(self.points[i].distance_to(self.points[i + 1]) for i in range(len(self.points) - 1))

    def bbox(self) -> Tuple[float, float, float, float]:
        """Return bounding box as (min_x, min_y, max_x, max_y)."""
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)


class Circle(BaseModel):
    """Circle primitive.

    Used for circular keepout regions and round pads.

    Attributes:
        center: Circle center point
        radius: Circle radius in millimeters (must be positive and finite)

    Validation:
        Radius must be positive and finite.
    """

    center: Point
    radius: float

    @field_validator("radius")
    @classmethod
    def validate_radius(cls, value: float) -> float:
        """Validate radius is positive and finite."""
        if value <= 0:
            raise ValueError("Radius must be positive")
        if not math.isfinite(value):
            raise ValueError("Radius must be finite")
        return value

    def contains_point(self, point: Point) -> bool:
        """Check if a point is inside or on the circle boundary."""
        return self.center.distance_to(point) <= self.radius

    def bbox(self) -> Tuple[float, float, float, float]:
        """Return bounding box as (min_x, min_y, max_x, max_y)."""
        return (
            self.center.x - self.radius,
            self.center.y - self.radius,
            self.center.x + self.radius,
            self.center.y + self.radius,
        )
