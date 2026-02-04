from pathlib import Path

from pcb_renderer.cli import _build_export_payload
from pcb_renderer.parse import load_board
from pcb_renderer.stats import compute_stats


def test_build_export_payload_structure():
    board_path = Path(__file__).resolve().parent.parent / "boards" / "board_alpha.json"
    board, parse_errors = load_board(board_path)
    assert board is not None
    stats = compute_stats(board)
    payload = _build_export_payload(
        input_path=board_path,
        board=board,
        parse_errors=parse_errors,
        validation_errors=[],
        render_success=True,
        output_path=Path("out.svg"),
        output_format="svg",
        stats=stats,
    )

    assert payload["schema_version"] == "1.0"
    assert payload["parse_result"]["success"] is True
    assert payload["validation_result"]["valid"] is True
    assert payload["render_result"]["success"] is True
    assert payload["parse_result"]["stats"]["num_components"] >= 0
