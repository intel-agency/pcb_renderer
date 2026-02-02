from pathlib import Path

from pcb_renderer.errors import ErrorCode
from pcb_renderer.parse import load_board
from pcb_renderer.validate import validate_board

BOARDS = Path(__file__).resolve().parent.parent / "boards"


def _validate(name: str):
    board, errors = load_board(BOARDS / name)
    if errors:
        return errors
    assert board is not None
    return validate_board(board)


def test_board_theta_reports_nonexistent_net():
    errors = _validate("board_theta.json")
    assert any(err.code == ErrorCode.NONEXISTENT_NET for err in errors)


def test_board_kappa_malformed_trace():
    errors = _validate("board_kappa.json")
    assert any(err.code in {ErrorCode.MALFORMED_TRACE, ErrorCode.DANGLING_TRACE} for err in errors)


def test_board_eta_negative_width():
    errors = _validate("board_eta.json")
    assert any(err.code == ErrorCode.NEGATIVE_WIDTH for err in errors)


def test_board_xi_malformed_stackup():
    errors = _validate("board_xi.json")
    assert any(err.code == ErrorCode.MALFORMED_STACKUP for err in errors)
