"""Additional coverage tests for stats, validate, and parse modules."""

import pytest

from pcb_renderer.errors import ErrorCode
from pcb_renderer.geometry import Point, Polygon, Polyline
from pcb_renderer.models import Board, Component, Net, Trace
from pcb_renderer.stats import compute_stats
from pcb_renderer.validate import is_self_intersecting, validate_board


def test_stats_with_malformed_trace():
    """Test stats skips traces with malformed paths (covers exception handling)."""
    board = Board(
        metadata={"title": "test"},
        boundary=Polygon(
            points=[Point(x=0, y=0), Point(x=100, y=0), Point(x=100, y=100), Point(x=0, y=100)]
        ),
        stackup={"layers": [{"name": "L1", "index": 0, "layerHash": "L1"}]},
        components={},
        traces={
            "t1": Trace(
                uid="t1", net_name="NET1", layer_hash="L1", width=0.2, path=Polyline(points=[])
            )
        },
        vias={},
        keepouts=[],
        nets=[Net(**{"name": "NET1", "class": "SIGNAL"})],
    )
    stats = compute_stats(board)
    assert "trace_length_total_mm" in stats


def test_stats_via_aspect_ratio_with_no_vias():
    """Test via aspect ratio is None when board has no vias."""
    board = Board(
        metadata={"title": "test"},
        boundary=Polygon(
            points=[Point(x=0, y=0), Point(x=50, y=0), Point(x=50, y=50), Point(x=0, y=50)]
        ),
        stackup={"layers": [{"name": "L1", "index": 0, "layerHash": "L1"}], "totalThickness": 1600},
        components={},
        traces={},
        vias={},
        keepouts=[],
        nets=[],
    )
    stats = compute_stats(board)
    assert stats["via_aspect_ratio"] is None


def test_validate_self_intersecting_boundary():
    """Test detection of self-intersecting boundary polygon."""
    points = [Point(x=0, y=0), Point(x=10, y=10), Point(x=10, y=0), Point(x=0, y=10)]
    poly = Polygon(points=points)
    assert is_self_intersecting(poly) is True


def test_validate_non_self_intersecting():
    """Test that regular polygons are not detected as self-intersecting."""
    points = [Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10), Point(x=0, y=10)]
    poly = Polygon(points=points)
    assert is_self_intersecting(poly) is False


def test_validate_component_pin_reference_error():
    """Test validator catches pins with wrong comp_name reference."""
    from pcb_renderer.models import Pin, Side, Transform

    board = Board(
        metadata={"title": "test"},
        boundary=Polygon(
            points=[Point(x=0, y=0), Point(x=100, y=0), Point(x=100, y=100), Point(x=0, y=100)]
        ),
        stackup={"layers": [{"name": "L1", "index": 0, "layerHash": "L1"}]},
        components={
            "C1": Component(
                name="C1",
                reference="C1",
                footprint="RES_0402",
                outline={"width": 1.0, "height": 0.5},
                transform=Transform(position=Point(x=50, y=50), rotation=0, side=Side.FRONT),
                pins={
                    "1": Pin(
                        name="1",
                        comp_name="C2",  # Wrong reference - should be "C1"
                        net_name=None,
                        shape={"type": "rect", "width": 0.5, "height": 0.5},
                        position=Point(x=0, y=0),
                    )
                },
            )
        },
        traces={},
        vias={},
        keepouts=[],
        nets=[],
    )
    errors = validate_board(board)
    pin_errors = [e for e in errors if e.code == ErrorCode.INVALID_PIN_REFERENCE]
    assert len(pin_errors) > 0
