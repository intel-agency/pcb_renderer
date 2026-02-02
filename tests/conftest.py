"""Pytest fixtures for pcb_renderer."""

import json
from pathlib import Path

import pytest

from pcb_renderer.geometry import Point, Polygon


@pytest.fixture
def sample_point() -> Point:
    return Point(x=5.0, y=10.0)


@pytest.fixture
def sample_polygon() -> Polygon:
    return Polygon(points=[Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10), Point(x=0, y=10)])


@pytest.fixture
def minimal_board(tmp_path: Path) -> Path:
    data = {
        "metadata": {"designUnits": "MILLIMETER"},
        "boundary": {"coordinates": [[0, 0], [10, 0], [10, 10], [0, 10]]},
        "stackup": {
            "layers": [
                {"name": "TOP", "layer_type": "TOP", "index": 0, "material": {}},
                {"name": "BOTTOM", "layer_type": "BOTTOM", "index": 1, "material": {}},
            ]
        },
        "nets": [{"name": "GND"}],
        "components": {},
        "traces": {},
        "vias": {},
    }
    path = tmp_path / "board.json"
    path.write_text(json.dumps(data))
    return path
