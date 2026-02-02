from pathlib import Path
import re

from pcb_renderer.parse import load_board
from pcb_renderer.render import render_board


GOLDEN_ALPHA = Path(__file__).resolve().parent / "golden" / "board_alpha.svg"
BOARD_ALPHA = Path(__file__).resolve().parent.parent / "boards" / "board_alpha.json"


def _normalize_svg(path: Path) -> str:
    text = path.read_text()
    text = re.sub(r"<metadata>.*?</metadata>", "", text, flags=re.DOTALL)
    return text.replace("\r\n", "\n").strip()


def test_board_alpha_matches_golden(tmp_path: Path) -> None:
    board, errors = load_board(BOARD_ALPHA)
    assert not errors and board is not None

    out = tmp_path / "alpha.svg"
    render_board(board, out, format="svg")

    assert _normalize_svg(out) == _normalize_svg(GOLDEN_ALPHA)
