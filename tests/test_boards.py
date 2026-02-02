from pathlib import Path

from pcb_renderer.errors import ErrorCode
from pcb_renderer.parse import load_board
from pcb_renderer.validate import validate_board


BOARDS = Path(__file__).resolve().parent.parent / "boards"


def test_valid_board_renders_without_errors():
    board, errors = load_board(BOARDS / "board_alpha.json")
    assert not errors and board is not None
    validation = validate_board(board)
    assert validation == []


def test_invalid_board_collects_errors():
    board, errors = load_board(BOARDS / "board_lambda.json")
    if errors:
        validation = errors
    else:
        assert board is not None
        validation = validate_board(board)
    assert any(err.code in {ErrorCode.INVALID_VIA_GEOMETRY, ErrorCode.NONEXISTENT_NET} for err in validation)
