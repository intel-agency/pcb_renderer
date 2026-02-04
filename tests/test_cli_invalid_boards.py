from pathlib import Path

import pytest

from pcb_renderer.cli import main
from pcb_renderer.errors import ErrorCode


BOARDS = Path(__file__).resolve().parent.parent / "boards"
INVALID_CASES = [
    ("board.json", {ErrorCode.NONEXISTENT_NET}),  # Pins with empty net_name
    ("board_eta.json", {ErrorCode.NEGATIVE_WIDTH}),
    ("board_kappa.json", {ErrorCode.MALFORMED_TRACE, ErrorCode.DANGLING_TRACE}),
    ("board_lambda.json", {ErrorCode.INVALID_VIA_GEOMETRY, ErrorCode.NONEXISTENT_NET}),
    ("board_mu.json", {ErrorCode.PARSE_ERROR}),
    ("board_theta.json", {ErrorCode.NONEXISTENT_NET}),
    ("board_xi.json", {ErrorCode.MALFORMED_STACKUP}),
]


def _error_codes_in_stderr(stderr: str, expected_codes: set[ErrorCode]) -> bool:
    return any(code.value in stderr for code in expected_codes)


@pytest.mark.parametrize(
    "name,expected_codes",
    INVALID_CASES,
    ids=[Path(name).stem for name, _codes in INVALID_CASES],
)
def test_invalid_boards_exit_with_errors(name: str, expected_codes: set[ErrorCode], tmp_path: Path, capsys):
    output_path = tmp_path / f"{Path(name).stem}.svg"
    exit_code = main([str(BOARDS / name), "-o", str(output_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err
    assert _error_codes_in_stderr(captured.err, expected_codes)
    assert not output_path.exists()
