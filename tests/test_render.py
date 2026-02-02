from pathlib import Path

from pcb_renderer.parse import load_board
from pcb_renderer.render import render_board


def test_render_smoke(tmp_path: Path):
    board, errors = load_board(Path(__file__).resolve().parent.parent / "boards" / "board_simple_2layer.json")
    assert not errors and board is not None
    out = tmp_path / "out.svg"
    render_board(board, out, format="svg")
    assert out.exists() and out.stat().st_size > 0
