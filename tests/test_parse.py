import json
from pathlib import Path

from pcb_renderer.errors import ErrorCode
from pcb_renderer.parse import parse_coordinates, load_board


def test_parse_coordinates_flat():
    points = parse_coordinates([0, 0, 1, 1])
    assert points[1].x == 1 and points[1].y == 1


def test_load_board_invalid_units(tmp_path: Path):
    data = {"metadata": {"designUnits": "INCH"}}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    board, errors = load_board(path)
    assert board is None
    assert errors[0].code == ErrorCode.INVALID_UNIT_SPECIFICATION
