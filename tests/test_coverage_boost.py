"""Tests to boost coverage to 95%+ targeting specific uncovered lines.

This test file focuses on:
1. stats.py: via aspect ratio calculation with smallest_hole > 0
2. parse.py: coordinate parsing error conditions
3. validate.py: edge cases for error conditions
"""

from pathlib import Path

import pytest

from pcb_renderer.parse import load_board, parse_coordinates
from pcb_renderer.stats import compute_stats
from pcb_renderer.validate import validate_board


def test_stats_via_aspect_ratio_with_valid_vias():
    """Test via aspect ratio calculation in stats.py when smallest_hole > 0.

    This tests the specific condition:
        if smallest_hole:
            via_aspect_ratio = total_thickness / smallest_hole
    """
    board_path = Path("boards/board.json")
    board, parse_errors = load_board(board_path)
    assert board is not None, f"Failed to load board.json: {parse_errors}"

    # Verify board has required data
    assert board.vias, "Board must have vias"
    assert isinstance(board.stackup, dict), "Stackup must be dict"
    assert board.stackup.get("totalThickness"), "Stackup must have totalThickness"

    stats = compute_stats(board)

    # The via_aspect_ratio should be calculated
    assert stats["via_aspect_ratio"] is not None, "via_aspect_ratio should be calculated"

    # Verify it matches expected calculation
    smallest_hole = min(v.hole_size for v in board.vias.values())
    expected_ratio = board.stackup["totalThickness"] / smallest_hole
    assert abs(stats["via_aspect_ratio"] - expected_ratio) < 0.001


def test_parse_coordinates_empty_array():
    """Test parse.py parse_coordinates: empty coordinate array raises ValueError."""
    with pytest.raises(ValueError, match="Empty coordinate array"):
        parse_coordinates([])


def test_parse_coordinates_odd_length_flat_array():
    """Test parse.py parse_coordinates: odd-length flat array raises ValueError."""
    with pytest.raises(ValueError, match="Flat coordinate list must have even length"):
        parse_coordinates([1.0, 2.0, 3.0])  # 3 elements (odd)


def test_parse_coordinates_unrecognized_format():
    """Test parse.py parse_coordinates: unrecognized format raises ValueError.

    Tests the case where coordinates are neither:
    - All flat numbers: [x1, y1, x2, y2, ...]
    - All nested pairs: [[x1, y1], [x2, y2], ...]
    """
    # Mixed format: some flat, some nested
    with pytest.raises(ValueError, match="Unrecognized coordinate format"):
        parse_coordinates([1.0, [2.0, 3.0], 4.0])

    # Wrong nested structure (3-element tuples instead of 2)
    with pytest.raises(ValueError, match="Unrecognized coordinate format"):
        parse_coordinates([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])


def test_validate_negative_trace_width():
    """Test validate.py validate_board: NEGATIVE_WIDTH error for trace.width <= 0.

    This tests the specific condition in validate_board:
        if trace.width <= 0:
            errors.append(ValidationError(code=ErrorCode.NEGATIVE_WIDTH, ...))
    """
    # Load a valid board and modify it to have a trace with negative width
    board_path = Path("boards/board.json")
    board, parse_errors = load_board(board_path)
    assert board is not None, f"Failed to load board: {parse_errors}"

    # Modify first trace to have zero width
    if board.traces:
        first_trace_id = next(iter(board.traces.keys()))
        board.traces[first_trace_id].width = 0.0

        errors = validate_board(board)

        # Should have at least one NEGATIVE_WIDTH error
        negative_width_errors = [err for err in errors if err.code.value == "NEGATIVE_WIDTH"]
        assert len(negative_width_errors) > 0
        assert negative_width_errors[0].message == f"Trace {first_trace_id} width must be positive"


def test_validate_invalid_via_geometry():
    """Test validate.py validate_board: INVALID_VIA_GEOMETRY when hole_size >= diameter.

    This tests the specific condition:
        if via.hole_size >= via.diameter:
            errors.append(ValidationError(code=ErrorCode.INVALID_VIA_GEOMETRY, ...))
    """
    board_path = Path("boards/board.json")
    board, parse_errors = load_board(board_path)
    assert board is not None, f"Failed to load board: {parse_errors}"

    # Modify first via to have invalid geometry (hole >= diameter)
    if board.vias:
        first_via_id = next(iter(board.vias.keys()))
        board.vias[first_via_id].hole_size = board.vias[first_via_id].diameter

        errors = validate_board(board)

        # Should have at least one INVALID_VIA_GEOMETRY error
        invalid_via_errors = [err for err in errors if err.code.value == "INVALID_VIA_GEOMETRY"]
        assert len(invalid_via_errors) > 0


def test_validate_dangling_trace():
    """Test validate.py validate_board: DANGLING_TRACE when trace references non-existent net.

    This tests the specific condition:
        if trace.net_name not in net_names:
            errors.append(ValidationError(code=ErrorCode.DANGLING_TRACE, ...))
    """
    board_path = Path("boards/board.json")
    board, parse_errors = load_board(board_path)
    assert board is not None, f"Failed to load board: {parse_errors}"

    # Modify first trace to reference a non-existent net
    if board.traces:
        first_trace_id = next(iter(board.traces.keys()))
        board.traces[first_trace_id].net_name = "NONEXISTENT_NET_XYZ"

        errors = validate_board(board)

        # Should have at least one DANGLING_TRACE error
        dangling_errors = [err for err in errors if err.code.value == "DANGLING_TRACE"]
        assert len(dangling_errors) > 0
        assert "NONEXISTENT_NET_XYZ" in dangling_errors[0].message


def test_validate_nonexistent_layer_in_trace():
    """Test validate.py validate_board: NONEXISTENT_LAYER when trace references unknown layer.

    This tests the specific condition:
        if trace.layer_hash not in layer_names:
            errors.append(ValidationError(code=ErrorCode.NONEXISTENT_LAYER, ...))
    """
    board_path = Path("boards/board.json")
    board, parse_errors = load_board(board_path)
    assert board is not None, f"Failed to load board: {parse_errors}"

    # Modify first trace to reference a non-existent layer
    if board.traces:
        first_trace_id = next(iter(board.traces.keys()))
        board.traces[first_trace_id].layer_hash = "NONEXISTENT_LAYER_XYZ"

        errors = validate_board(board)

        # Should have at least one NONEXISTENT_LAYER error
        layer_errors = [err for err in errors if err.code.value == "NONEXISTENT_LAYER"]
        assert len(layer_errors) > 0
        assert "NONEXISTENT_LAYER_XYZ" in layer_errors[0].message


def test_validate_nonexistent_net_in_via():
    """Test validate.py validate_board: NONEXISTENT_NET when via references unknown net.

    This tests the specific condition:
        if via.net_name not in net_names:
            errors.append(ValidationError(code=ErrorCode.NONEXISTENT_NET, ...))
    """
    board_path = Path("boards/board.json")
    board, parse_errors = load_board(board_path)
    assert board is not None, f"Failed to load board: {parse_errors}"

    # Modify first via to reference a non-existent net
    if board.vias:
        first_via_id = next(iter(board.vias.keys()))
        board.vias[first_via_id].net_name = "NONEXISTENT_NET_ABC"

        errors = validate_board(board)

        # Should have at least one NONEXISTENT_NET error
        net_errors = [err for err in errors if err.code.value == "NONEXISTENT_NET"]
        assert len(net_errors) > 0
