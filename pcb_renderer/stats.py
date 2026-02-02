"""Board statistics utilities for export/LLM plugin."""

from __future__ import annotations

from typing import Any, Dict

from .models import Board


def compute_stats(board: Board) -> Dict[str, Any]:
    boundary_bbox = board.boundary.bbox() if board.boundary else (0.0, 0.0, 0.0, 0.0)
    min_x, min_y, max_x, max_y = boundary_bbox
    width = max_x - min_x
    height = max_y - min_y
    area = max(width * height, 0.0)

    num_components = len(board.components)
    num_traces = len(board.traces)
    num_vias = len(board.vias)
    num_nets = len(board.nets)
    layer_count = len(board.stackup.get("layers", [])) if isinstance(board.stackup, dict) else 0

    trace_length_total = 0.0
    for trace in board.traces.values():
        try:
            trace_length_total += trace.path.length()
        except Exception:
            continue

    component_density = (num_components / area) if area else 0.0

    total_thickness = board.stackup.get("totalThickness") if isinstance(board.stackup, dict) else None
    via_aspect_ratio = None
    if total_thickness and num_vias:
        smallest_hole = min(v.hole_size for v in board.vias.values())
        if smallest_hole:
            via_aspect_ratio = float(total_thickness) / float(smallest_hole)

    return {
        "board_dimensions_mm": [width, height],
        "board_area_mm2": area,
        "num_components": num_components,
        "num_traces": num_traces,
        "num_vias": num_vias,
        "num_nets": num_nets,
        "layer_count": layer_count,
        "component_density": component_density,
        "trace_length_total_mm": trace_length_total,
        "total_thickness_um": total_thickness,
        "via_aspect_ratio": via_aspect_ratio,
    }
