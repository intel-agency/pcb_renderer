"""Board statistics utilities for export/LLM plugin.

This module computes aggregate statistics about a parsed PCB board.
These statistics are included in the export JSON payload and consumed by:
- LLM plugin for design analysis
- Tests for verifying correct board parsing
- External tools for board comparison

Statistics Computed:
-------------------
- Board dimensions and area (mm/mm²)
- Component, trace, via, and net counts
- Layer count from stackup
- Component density (components per mm²)
- Total trace length (mm)
- Via aspect ratio (thickness / smallest hole)

Usage:
------
::

    from pcb_renderer.stats import compute_stats
    stats = compute_stats(board)
    # stats["board_dimensions_mm"] == [width, height]
    # stats["num_components"] == 42
    # etc.

"""

from __future__ import annotations

from typing import Any, Dict

from .models import Board


def compute_stats(board: Board) -> Dict[str, Any]:
    """Compute aggregate statistics for a parsed board.

    This function analyzes the board and returns a dict of statistics
    that provide an overview of the board's complexity and characteristics.

    Args:
        board: Parsed and validated Board model

    Returns:
        Dict with the following keys:
        - board_dimensions_mm: [width, height] in millimeters
        - board_area_mm2: Board area in square millimeters
        - num_components: Total component count
        - num_traces: Total trace count
        - num_vias: Total via count
        - num_nets: Total net count
        - layer_count: Number of layers in stackup
        - component_density: Components per mm² (0 if no area)
        - trace_length_total_mm: Sum of all trace lengths
        - total_thickness_um: Board thickness in microns (from stackup, may be None)
        - via_aspect_ratio: thickness / smallest_hole (may be None)

    Note:
        Via aspect ratio is a manufacturing metric. Higher ratios (>10:1)
        indicate more challenging fabrication requirements.
    """
    # Calculate board dimensions from boundary bounding box
    boundary_bbox = board.boundary.bbox() if board.boundary else (0.0, 0.0, 0.0, 0.0)
    min_x, min_y, max_x, max_y = boundary_bbox
    width = max_x - min_x
    height = max_y - min_y
    area = max(width * height, 0.0)  # Ensure non-negative

    # Count board elements
    num_components = len(board.components)
    num_traces = len(board.traces)
    num_vias = len(board.vias)
    num_nets = len(board.nets)
    layer_count = len(board.stackup.get("layers", [])) if isinstance(board.stackup, dict) else 0

    # Sum all trace lengths (skip malformed traces that may fail)
    trace_length_total = 0.0
    for trace in board.traces.values():
        try:
            trace_length_total += trace.path.length()
        except Exception:
            continue  # Skip traces with malformed paths

    # Component density (components per square millimeter)
    component_density = (num_components / area) if area else 0.0

    # Via aspect ratio: board_thickness / smallest_hole_diameter
    # This is a key manufacturing metric for via drillability
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
