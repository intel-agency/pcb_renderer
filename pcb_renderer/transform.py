"""Coordinate transforms between ECAD and SVG spaces.

This module handles the coordinate system differences between ECAD (Electronic
Computer-Aided Design) data and SVG/Matplotlib rendering output.

Coordinate Systems:
------------------
- **ECAD**: Y-up (origin at bottom-left, Y increases upward)
  This is standard for PCB design tools.

- **SVG/Screen**: Y-down (origin at top-left, Y increases downward)
  This is standard for graphics and web rendering.

Transform Mathematics:
---------------------
The ECAD to SVG Y-axis flip is simply:
    svg_y = board_height - ecad_y

This is its own inverse, so the same formula converts back.

Component Transforms:
--------------------
Components have a 2D affine transform applied:
1. Translate to position (x, y)
2. Rotate by angle (degrees, counterclockwise)
3. Mirror horizontally if on BACK side

The transform is represented as a 3x3 homogeneous matrix:
    [cosθ  -sinθ  tx]     [x]     [x']
    [sinθ   cosθ  ty]  ×  [y]  =  [y']
    [0      0      1]     [1]     [1 ]
"""

from __future__ import annotations

import numpy as np

from .geometry import Point
from .models import Component, Side


def ecad_to_svg(point: Point, board_height: float) -> Point:
    """Convert ECAD coordinates to SVG coordinates.

    ECAD uses Y-up (origin at bottom-left), while SVG uses Y-down
    (origin at top-left). This function flips the Y-axis.

    Args:
        point: Point in ECAD coordinates (millimeters)
        board_height: Total board height for Y-axis flip

    Returns:
        Point in SVG coordinates (millimeters)

    Example:
        >>> # Board is 80mm tall, point at ECAD (10, 20)
        >>> ecad_to_svg(Point(x=10, y=20), 80.0)
        Point(x=10, y=60)  # 80 - 20 = 60
    """
    return Point(x=point.x, y=board_height - point.y)


def svg_to_ecad(point: Point, board_height: float) -> Point:
    """Convert SVG coordinates back to ECAD coordinates.

    This is the inverse of ecad_to_svg. Since the transform is symmetric
    (y' = h - y), the same formula works in both directions.

    Args:
        point: Point in SVG coordinates (millimeters)
        board_height: Total board height for Y-axis flip

    Returns:
        Point in ECAD coordinates (millimeters)
    """
    return Point(x=point.x, y=board_height - point.y)


def compute_component_transform(component: Component) -> np.ndarray:
    """Build the 3x3 affine transform matrix for a component.

    The transform is applied in this order:
    1. Translate to component position
    2. Rotate by component rotation (counterclockwise)
    3. Mirror X if component is on BACK side

    Args:
        component: Component model with transform data

    Returns:
        3x3 numpy array representing the homogeneous transformation matrix

    Note:
        Matrix multiplication order is right-to-left, so we multiply:
        identity @ translation @ rotation @ mirror

        This means mirror is applied first (in component-local space),
        then rotation, then translation (to board space).
    """
    # Start with identity matrix
    matrix = np.eye(3)

    # Step 1: Translation to component position
    tx, ty = component.transform.position.x, component.transform.position.y
    translation = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]])
    matrix = matrix @ translation

    # Step 2: Rotation around origin (now at component position)
    angle_rad = np.deg2rad(component.transform.rotation)
    cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
    rotation = np.array([[cos_a, -sin_a, 0], [sin_a, cos_a, 0], [0, 0, 1]])
    matrix = matrix @ rotation

    # Step 3: Mirror for BACK side components (flip X axis)
    if component.transform.side == Side.BACK:
        mirror = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, 1]])
        matrix = matrix @ mirror

    return matrix


def transform_point(point: Point, matrix: np.ndarray) -> Point:
    """Apply a 3x3 affine transform matrix to a point.

    Uses homogeneous coordinates [x, y, 1] for 2D affine transforms.

    Args:
        point: Point to transform
        matrix: 3x3 transformation matrix from compute_component_transform()

    Returns:
        Transformed Point in new coordinate space
    """
    vec = np.array([point.x, point.y, 1])  # Homogeneous coordinates
    res = matrix @ vec
    return Point(x=float(res[0]), y=float(res[1]))
