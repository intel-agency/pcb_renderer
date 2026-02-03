"""Matplotlib rendering pipeline for PCB board visualization.

This module handles the final stage of the PCB Renderer pipeline:

    Board model → render.py → SVG/PNG/PDF output

Challenge Requirements:
-----------------------
From the Quilter Backend Engineer Code Challenge, render the following:

1. Board Boundary - Draw board outline from boundary.coordinates
2. Components     - Draw outlines at transformed positions with reference designators
3. Traces         - Draw as lines with specified width, colored by layer
4. Vias           - Draw as circles at center positions with diameter
5. Keepout Regions - Draw with distinct pattern/color as restricted areas

Rendering Requirements:
- Output formats: SVG, PNG, PDF
- Board renders correctly and is easily readable
- Solution can be reviewed and verified within 20 minutes

Architecture Notes:
-------------------
**Headless + Deterministic Rendering**

- matplotlib.use("Agg") MUST be called before importing pyplot
  (prevents Tkinter errors in CI/docker environments)
- SVG determinism settings ensure identical output for golden master tests:
  - svg.hashsalt = "pcb-renderer" (stable element IDs)
  - svg.fonttype = "none" (system-independent font handling)

Z-Order (draw order, bottom to top):
1. Boundary (zorder=1)
2. Pours (zorder=2)
3. Traces (zorder=3)
4. Vias - outer ring (zorder=4)
5. Vias - hole / Components (zorder=5)
6. Reference designators (zorder=6)
7. Keepouts (zorder=7)

Coordinate Systems:
-------------------
- ECAD: Y-up (0,0 at bottom-left, Y increases upward)
- SVG:  Y-down (0,0 at top-left, Y increases downward)

The transform is: svg_y = board_height - ecad_y
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib

# CRITICAL: Agg backend must be set before pyplot import for headless rendering
# This prevents Tkinter initialization errors in CI/docker environments
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib import patheffects

from .colors import LAYER_COLORS
from .geometry import Circle, Point, Polygon
from .models import Board, Component, Trace, Via
from .transform import ecad_to_svg, compute_component_transform, transform_point

# SVG determinism settings for reproducible golden master tests
matplotlib.rcParams["svg.hashsalt"] = "pcb-renderer"  # Stable element IDs
matplotlib.rcParams["svg.fonttype"] = "none"  # No font embedding


def _board_dimensions(boundary: Polygon) -> tuple[float, float, float, float]:
    """Extract bounding box from board boundary.

    Returns:
        Tuple of (min_x, min_y, max_x, max_y) in millimeters
    """
    return boundary.bbox()


def render_board(board: Board, output_path: Path, format: str | None = None, dpi: int = 300) -> None:
    """Render a validated board to an image file.

    This is the main entry point for the rendering pipeline. It creates
    a matplotlib figure, draws all board elements in z-order, and exports
    to the specified format.

    Args:
        board: Validated Board model from parse.py
        output_path: Destination file path (e.g., "out/board.svg")
        format: Explicit format override ("svg", "png", "pdf"), or None to infer from extension
        dpi: Resolution for raster formats (PNG). SVG always uses dpi=72.

    Raises:
        ValueError: If board has no boundary defined

    Challenge Requirements:
        This function implements all 5 rendering tasks:
        - Task 1: Board Boundary
        - Task 2: Components with reference designators
        - Task 3: Traces with layer colors and width
        - Task 4: Vias as circles
        - Task 5: Keepout regions with distinct pattern
    """
    # Validate boundary exists (required for rendering)
    boundary = board.boundary
    if boundary is None:
        raise ValueError("Board boundary is required for rendering")

    # Determine output format from extension or explicit parameter
    format = (format or output_path.suffix.lstrip(".")).lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate board dimensions for coordinate transforms
    min_x, min_y, max_x, max_y = _board_dimensions(boundary)
    board_height = max_y - min_y  # Used for ECAD->SVG Y-axis flip
    width = max_x - min_x
    height = max_y - min_y
    padding = 0.1  # 10% padding around board

    # Set up figure with appropriate size (cap at 20 inches for large boards)
    base_width_in = max(width, 1) * 0.1 + 6
    base_height_in = max(height, 1) * 0.1 + 6
    max_inches = 20.0
    scale = min(1.0, max_inches / max(base_width_in, base_height_in))
    fig, ax = plt.subplots(figsize=(base_width_in * scale, base_height_in * scale))
    ax.set_aspect("equal")
    ax.axis("off")

    # Set view limits with padding, Y-axis inverted for SVG convention
    ax.set_xlim(min_x - width * padding, max_x + width * padding)
    ax.set_ylim(max_y + height * padding, min_y - height * padding)

    # Draw all elements in z-order (bottom to top)
    draw_boundary(ax, boundary, board_height)  # z=1 (Task 1)
    draw_pours(ax, board, board_height)  # z=2
    for trace in board.traces.values():
        draw_trace(ax, trace, board_height)  # z=3 (Task 3)
    for via in board.vias.values():
        draw_via(ax, via, board_height)  # z=4,5 (Task 4)
    for comp in board.components.values():
        draw_component(ax, comp, board_height)  # z=5,6 (Task 2)
    for keepout in board.keepouts:
        draw_keepout(ax, keepout, board_height)  # z=7 (Task 5)

    # Export to file
    plt.savefig(
        output_path,
        format=format,
        dpi=72 if format == "svg" else dpi,  # SVG doesn't use DPI
        bbox_inches="tight",
        pad_inches=0.1,
    )
    plt.close(fig)


def draw_boundary(ax, boundary: Polygon, board_height: float) -> None:
    """Draw the board boundary outline.

    Task 1: Board Boundary - Draw the board outline from boundary.coordinates.
    This forms the outer edge of the PCB.

    Args:
        ax: Matplotlib axes object
        boundary: Board boundary polygon
        board_height: Board height for Y-axis coordinate transform
    """
    xs = [p.x for p in boundary.points]
    ys = [board_height - p.y for p in boundary.points]  # ECAD->SVG Y-flip
    patch = mpatches.Polygon(list(zip(xs, ys)), closed=True, fill=False, edgecolor="black", linewidth=2, zorder=1)
    ax.add_patch(patch)


def draw_pours(ax, board: Board, board_height: float) -> None:
    """Draw copper pour regions.

    Pours are filled copper areas (e.g., ground planes). They are drawn
    with low z-order so traces and vias appear on top.

    Args:
        ax: Matplotlib axes object
        board: Board model containing pours
        board_height: Board height for Y-axis coordinate transform
    """
    for pour in board.pours.values():
        shape = pour.get("shape") if isinstance(pour, dict) else None
        coords = shape.get("coordinates") if isinstance(shape, dict) else None
        if coords:
            points = [ecad_to_svg(Point(x=c[0], y=c[1]), board_height) for c in coords]
            xs = [p.x for p in points]
            ys = [p.y for p in points]
            patch = mpatches.Polygon(list(zip(xs, ys)), closed=True, facecolor="#b4d5ff", edgecolor="#6699cc", alpha=0.2, zorder=2)
            ax.add_patch(patch)


def draw_trace(ax, trace: Trace, board_height: float) -> None:
    """Draw a single trace path.

    Task 3: Traces - Draw traces as lines/paths with their specified width.
    Uses different colors for different layers.

    Args:
        ax: Matplotlib axes object
        trace: Trace model with path, width, and layer
        board_height: Board height for Y-axis coordinate transform
    """
    xs = [p.x for p in trace.path.points]
    ys = [board_height - p.y for p in trace.path.points]  # ECAD->SVG Y-flip
    color = LAYER_COLORS.get(trace.layer_hash, "#888888")  # Default gray for unknown layers
    ax.plot(xs, ys, color=color, linewidth=trace.width, solid_capstyle="round", solid_joinstyle="round", zorder=3)


def draw_via(ax, via: Via, board_height: float) -> None:
    """Draw a single via.

    Task 4: Vias - Draw vias as circles at their center positions.
    Two circles are drawn: outer annular ring and inner hole.

    Args:
        ax: Matplotlib axes object
        via: Via model with center, diameter, and hole_size
        board_height: Board height for Y-axis coordinate transform
    """
    x = via.center.x
    y = board_height - via.center.y  # ECAD->SVG Y-flip
    # Outer ring (plated annular ring)
    outer = mpatches.Circle((x, y), radius=via.diameter / 2, facecolor="silver", edgecolor="black", linewidth=1, zorder=4)
    # Inner hole (drill hole)
    hole = mpatches.Circle((x, y), radius=via.hole_size / 2, facecolor="white", edgecolor="black", linewidth=0.5, zorder=5)
    ax.add_patch(outer)
    ax.add_patch(hole)


def _component_corners(component: Component) -> Iterable[Point]:
    """Generate the 4 corner points of a component's outline rectangle.

    Components are rendered as rectangles centered at the origin, then
    transformed to their placed position via compute_component_transform().

    Args:
        component: Component model with outline dimensions

    Returns:
        List of 4 corner Points (counterclockwise from bottom-left)
    """
    outline = component.outline or {}
    width = outline.get("width", 1.0)
    height = outline.get("height", 1.0)
    return [
        Point(x=-width / 2, y=-height / 2),  # Bottom-left
        Point(x=width / 2, y=-height / 2),  # Bottom-right
        Point(x=width / 2, y=height / 2),  # Top-right
        Point(x=-width / 2, y=height / 2),  # Top-left
    ]


def draw_component(ax, component: Component, board_height: float) -> None:
    """Draw a single component with its reference designator.

    Task 2: Components - Draw component outlines at their transformed positions.
    Show component reference designators (R1, C1, U1). Handle rotation correctly.

    The component outline is a rectangle that gets transformed by:
    1. Translation to component position
    2. Rotation by component angle
    3. Mirror if on BACK side

    Args:
        ax: Matplotlib axes object
        component: Component model with transform and outline
        board_height: Board height for Y-axis coordinate transform
    """
    # Compute and apply component transform matrix (translation + rotation + mirror)
    matrix = compute_component_transform(component)
    transformed = [transform_point(pt, matrix) for pt in _component_corners(component)]
    xs = [p.x for p in transformed]
    ys = [board_height - p.y for p in transformed]  # ECAD->SVG Y-flip

    # Draw component body
    patch = mpatches.Polygon(list(zip(xs, ys)), closed=True, facecolor="#d3d3d3", edgecolor="black", linewidth=1, zorder=5)
    ax.add_patch(patch)

    # Draw reference designator (e.g., R1, C1, U1) at component center
    centroid_svg = ecad_to_svg(component.transform.position, board_height)
    text = ax.text(
        centroid_svg.x,
        centroid_svg.y,
        component.reference,
        ha="center",
        va="center",
        fontsize=max(8, min(14, board_height * 0.05)),  # Scale font with board size
        color="white",
        weight="bold",
        zorder=6,
    )
    # Add black outline for visibility against gray component body
    text.set_path_effects([patheffects.withStroke(linewidth=2, foreground="black")])


def draw_keepout(ax, keepout, board_height: float) -> None:
    """Draw a keepout region.

    Task 5: Keepout Regions - Draw keepout areas with a distinct pattern or color.
    Mark them as restricted areas.

    Keepouts can be either circular or polygonal. They are drawn with:
    - Red color and hatching pattern to indicate restriction
    - High z-order so they appear on top of other elements
    - Semi-transparent to show underlying geometry

    Args:
        ax: Matplotlib axes object
        keepout: Keepout model with shape (Circle or Polygon)
        board_height: Board height for Y-axis coordinate transform
    """
    shape = keepout.shape
    # Guard: skip keepouts with malformed/missing shapes (permissive parsing)
    if shape is None:
        return

    # Common styling for keepout regions
    patch_kwargs = {
        "facecolor": LAYER_COLORS.get("KEEP_OUT", "#FF0000"),
        "edgecolor": "red",
        "alpha": 0.3,  # Semi-transparent
        "hatch": "///",  # Diagonal hatching pattern
        "linewidth": 2,
        "zorder": 7,  # Top z-order
    }

    if isinstance(shape, Circle):
        # Circular keepout
        center_x = shape.center.x
        center_y = board_height - shape.center.y  # ECAD->SVG Y-flip
        patch = mpatches.Circle(
            (center_x, center_y),
            shape.radius,
            **patch_kwargs,
        )
    else:
        # Polygon keepout
        xs = [p.x for p in shape.points]
        ys = [board_height - p.y for p in shape.points]  # ECAD->SVG Y-flip
        patch = mpatches.Polygon(
            list(zip(xs, ys)),
            closed=True,
            **patch_kwargs,
        )
    ax.add_patch(patch)
