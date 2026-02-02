import pytest

from pcb_renderer.errors import ErrorCode
from pcb_renderer.geometry import Point
from pcb_renderer.models import Board, Transform, Via
from pcb_renderer.validate import validate_board


def test_point_validation_rejects_nan():
    with pytest.raises(ValueError):
        Point(x=float("nan"), y=0)


def test_transform_rotation_bounds():
    with pytest.raises(ValueError):
        Transform(position=Point(x=0, y=0), rotation=400)


def test_via_hole_smaller_than_diameter():
    via = Via(
        uid="v1",
        net_name="GND",
        center=Point(x=0, y=0),
        diameter=0.5,
        hole_size=0.6,
        span={"start_layer": "TOP", "end_layer": "BOTTOM"},
    )
    board = Board.model_validate(
        {
            "metadata": {},
            "boundary": None,
            "stackup": {"layers": []},
            "nets": [{"name": "GND"}],
            "components": {},
            "traces": {},
            "vias": {"v1": via},
        }
    )
    errors = validate_board(board)
    assert any(err.code == ErrorCode.INVALID_VIA_GEOMETRY for err in errors)
