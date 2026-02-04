from pathlib import Path
import re

import pytest

from pcb_renderer.parse import load_board
from pcb_renderer.render import render_board


BOARDS_DIR = Path(__file__).resolve().parent.parent / "boards"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
INVALID_BOARDS = {
    "board.json",
    "board_eta.json",
    "board_kappa.json",
    "board_lambda.json",
    "board_mu.json",
    "board_theta.json",
    "board_xi.json",
}
VALID_BOARDS = sorted(p for p in BOARDS_DIR.glob("*.json") if p.name not in INVALID_BOARDS)


def _normalize_svg(path: Path) -> str:
    text = path.read_text()
    text = re.sub(r"<metadata>.*?</metadata>", "", text, flags=re.DOTALL)
    return text.replace("\r\n", "\n").strip()


@pytest.mark.parametrize("board_path", VALID_BOARDS, ids=lambda path: path.stem)
def test_svg_outputs_match_golden(board_path: Path, tmp_path: Path) -> None:
    board, errors = load_board(board_path)
    assert not errors and board is not None

    out = tmp_path / f"{board_path.stem}.svg"
    render_board(board, out, format="svg")

    golden = GOLDEN_DIR / f"{board_path.stem}.svg"
    assert golden.exists(), f"Missing golden SVG: {golden}"
    assert _normalize_svg(out) == _normalize_svg(golden)


@pytest.mark.parametrize("board_path", VALID_BOARDS, ids=lambda path: path.stem)
@pytest.mark.parametrize("format_name", ["png", "pdf"])
def test_render_outputs_for_all_formats(board_path: Path, tmp_path: Path, format_name: str) -> None:
    board, errors = load_board(board_path)
    assert not errors and board is not None

    out = tmp_path / f"{board_path.stem}.{format_name}"
    render_board(board, out, format=format_name)

    assert out.exists() and out.stat().st_size > 0
