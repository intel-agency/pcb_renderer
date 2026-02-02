"""Geometric primitives with validation."""

from __future__ import annotations

import math
from typing import Iterable, List, Tuple

import numpy as np
from pydantic import BaseModel, Field, field_validator


class Point(BaseModel):
    """2D point in millimeters."""

    x: float
    y: float

    model_config = {"frozen": True}

    @field_validator("x", "y")
    @classmethod
    def validate_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError(f"Coordinate must be finite, got {value}")
        return value

    def __add__(self, other: Point) -> Point:
        return Point(x=self.x + other.x, y=self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(x=self.x - other.x, y=self.y - other.y)

    def __mul__(self, scalar: float) -> Point:
        return Point(x=self.x * scalar, y=self.y * scalar)

    def distance_to(self, other: Point) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.hypot(dx, dy)

    def rotate(self, angle_deg: float, origin: Point | None = None) -> Point:
        origin = origin or Point(x=0, y=0)
        angle_rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
        px, py = self.x - origin.x, self.y - origin.y
        rx = px * cos_a - py * sin_a
        ry = px * sin_a + py * cos_a
        return Point(x=rx + origin.x, y=ry + origin.y)

    def mirror_x(self) -> Point:
        return Point(x=-self.x, y=self.y)

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y])


class Polygon(BaseModel):
    """Closed polygon with ≥3 points."""

    points: List[Point] = Field(..., min_length=3)

    @field_validator("points")
    @classmethod
    def validate_polygon(cls, value: List[Point]) -> List[Point]:
        if len(value) < 3:
            raise ValueError("Polygon must have at least 3 points")
        if value[0] != value[-1]:
            value.append(value[0])
        return value

    def bbox(self) -> Tuple[float, float, float, float]:
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)

    def contains_point(self, point: Point) -> bool:
        x, y = point.x, point.y
        n = len(self.points) - 1
        inside = False
        p1 = self.points[0]
        for i in range(1, n + 1):
            p2 = self.points[i]
            if ((p1.y > y) != (p2.y > y)) and (
                x < (p2.x - p1.x) * (y - p1.y) / (p2.y - p1.y) + p1.x
            ):
                inside = not inside
            p1 = p2
        return inside

    def edges(self) -> Iterable[tuple[Point, Point]]:
        for i in range(len(self.points) - 1):
            yield self.points[i], self.points[i + 1]

    def to_xy_lists(self) -> Tuple[List[float], List[float]]:
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return xs, ys


class Polyline(BaseModel):
    """Open path with ≥2 points."""

    points: List[Point] = Field(default_factory=list)

    def length(self) -> float:
        return sum(self.points[i].distance_to(self.points[i + 1]) for i in range(len(self.points) - 1))

    def bbox(self) -> Tuple[float, float, float, float]:
        xs = [p.x for p in self.points]
        ys = [p.y for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)


class Circle(BaseModel):
    """Circle primitive."""

    center: Point
    radius: float

    @field_validator("radius")
    @classmethod
    def validate_radius(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Radius must be positive")
        if not math.isfinite(value):
            raise ValueError("Radius must be finite")
        return value

    def contains_point(self, point: Point) -> bool:
        return self.center.distance_to(point) <= self.radius

    def bbox(self) -> Tuple[float, float, float, float]:
        return (
            self.center.x - self.radius,
            self.center.y - self.radius,
            self.center.x + self.radius,
            self.center.y + self.radius,
        )
