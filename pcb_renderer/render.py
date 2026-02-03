"""Matplotlib rendering pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib import patheffects

from .colors import LAYER_COLORS
from .geometry import Point, Polygon
from .models import Board, Component, Trace, Via
from .transform import ecad_to_svg, compute_component_transform, transform_point

matplotlib.rcParams["svg.hashsalt"] = "pcb-renderer"
matplotlib.rcParams["svg.fonttype"] = "none"


def _board_dimensions(boundary: Polygon) -> tuple[float, float, float, float]:
    return boundary.bbox()


def render_board(board: Board, output_path: Path, format: str | None = None, dpi: int = 300) -> None:
    boundary = board.boundary
    if boundary is None:
        raise ValueError("Board boundary is required for rendering")

    format = (format or output_path.suffix.lstrip(".")).lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    min_x, min_y, max_x, max_y = _board_dimensions(boundary)
    board_height = max_y - min_y
    width = max_x - min_x
    height = max_y - min_y
    padding = 0.1

    fig, ax = plt.subplots(figsize=(max(width, 1) * 0.1 + 6, max(height, 1) * 0.1 + 6))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(min_x - width * padding, max_x + width * padding)
    ax.set_ylim(max_y + height * padding, min_y - height * padding)

    draw_boundary(ax, boundary, board_height)
    draw_pours(ax, board, board_height)
    for trace in board.traces.values():
        draw_trace(ax, trace, board_height)
    for via in board.vias.values():
        draw_via(ax, via, board_height)
    for comp in board.components.values():
        draw_component(ax, comp, board_height)
    for keepout in board.keepouts:
        draw_keepout(ax, keepout, board_height)

    plt.savefig(
        output_path,
        format=format,
        dpi=72 if format == "svg" else dpi,
        bbox_inches="tight",
        pad_inches=0.1,
    )
    plt.close(fig)


def draw_boundary(ax, boundary: Polygon, board_height: float) -> None:
    xs = [p.x for p in boundary.points]
    ys = [board_height - p.y for p in boundary.points]
    patch = mpatches.Polygon(list(zip(xs, ys)), closed=True, fill=False, edgecolor="black", linewidth=2, zorder=1)
    ax.add_patch(patch)


def draw_pours(ax, board: Board, board_height: float) -> None:
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
    xs = [p.x for p in trace.path.points]
    ys = [board_height - p.y for p in trace.path.points]
    color = LAYER_COLORS.get(trace.layer_hash, "#888888")
    ax.plot(xs, ys, color=color, linewidth=trace.width, solid_capstyle="round", solid_joinstyle="round", zorder=3)


def draw_via(ax, via: Via, board_height: float) -> None:
    x = via.center.x
    y = board_height - via.center.y
    outer = mpatches.Circle((x, y), radius=via.diameter / 2, facecolor="silver", edgecolor="black", linewidth=1, zorder=4)
    hole = mpatches.Circle((x, y), radius=via.hole_size / 2, facecolor="white", edgecolor="black", linewidth=0.5, zorder=5)
    ax.add_patch(outer)
    ax.add_patch(hole)


def _component_corners(component: Component) -> Iterable[Point]:
    outline = component.outline or {}
    width = outline.get("width", 1.0)
    height = outline.get("height", 1.0)
    return [
        Point(x=-width / 2, y=-height / 2),
        Point(x=width / 2, y=-height / 2),
        Point(x=width / 2, y=height / 2),
        Point(x=-width / 2, y=height / 2),
    ]


def draw_component(ax, component: Component, board_height: float) -> None:
    matrix = compute_component_transform(component)
    transformed = [transform_point(pt, matrix) for pt in _component_corners(component)]
    xs = [p.x for p in transformed]
    ys = [board_height - p.y for p in transformed]
    patch = mpatches.Polygon(list(zip(xs, ys)), closed=True, facecolor="#d3d3d3", edgecolor="black", linewidth=1, zorder=5)
    ax.add_patch(patch)

    centroid_svg = ecad_to_svg(component.transform.position, board_height)
    text = ax.text(
        centroid_svg.x,
        centroid_svg.y,
        component.reference,
        ha="center",
        va="center",
        fontsize=max(8, min(14, board_height * 0.05)),
        color="white",
        weight="bold",
        zorder=6,
    )
    text.set_path_effects([patheffects.withStroke(linewidth=2, foreground="black")])


def draw_keepout(ax, keepout, board_height: float) -> None:
    xs = [p.x for p in keepout.shape.points]
    ys = [board_height - p.y for p in keepout.shape.points]
    patch = mpatches.Polygon(
        list(zip(xs, ys)),
        closed=True,
        facecolor=LAYER_COLORS.get("KEEP_OUT", "#FF0000"),
        edgecolor="red",
        alpha=0.3,
        hatch="///",
        linewidth=2,
        zorder=7,
    )
    ax.add_patch(patch)
