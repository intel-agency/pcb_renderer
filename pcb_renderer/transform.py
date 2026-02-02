"""Coordinate transforms between ECAD and SVG spaces."""

from __future__ import annotations

import numpy as np

from .geometry import Point
from .models import Component, Side


def ecad_to_svg(point: Point, board_height: float) -> Point:
    return Point(x=point.x, y=board_height - point.y)


def svg_to_ecad(point: Point, board_height: float) -> Point:
    return Point(x=point.x, y=board_height - point.y)


def compute_component_transform(component: Component) -> np.ndarray:
    matrix = np.eye(3)
    tx, ty = component.transform.position.x, component.transform.position.y
    translation = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]])
    matrix = matrix @ translation

    angle_rad = np.deg2rad(component.transform.rotation)
    cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
    rotation = np.array([[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]])
    matrix = matrix @ rotation

    if component.transform.side == Side.BACK:
        mirror = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])
        matrix = matrix @ mirror
    return matrix


def transform_point(point: Point, matrix: np.ndarray) -> Point:
    vec = np.array([point.x, point.y, 1])
    res = matrix @ vec
    return Point(x=float(res[0]), y=float(res[1]))
