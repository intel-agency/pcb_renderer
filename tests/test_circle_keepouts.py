"""Tests for circle keepout parsing, rendering, and error handling."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from pcb_renderer.geometry import Circle, Polygon
from pcb_renderer.parse import load_board, normalize_units, _parse_board_objects


class TestCircleKeepoutParsing:
    """Tests for circle keepout parsing."""

    def test_parse_circle_keepout_creates_circle_object(self, tmp_path: Path):
        """Verify Circle objects are created correctly from circle keepouts."""
        board_data = {
            "metadata": {"designUnits": "MILLIMETER"},
            "boundary": {"coordinates": [[0, 0], [100, 0], [100, 100], [0, 100]]},
            "stackup": {"layers": []},
            "nets": [],
            "components": {},
            "traces": {},
            "vias": {},
            "keepouts": [
                {
                    "uid": "keepout_circle_1",
                    "name": "TEST_CIRCLE",
                    "layer": "ALL",
                    "shape": {
                        "type": "circle",
                        "center": [50, 50],
                        "radius": 10,
                    },
                    "keepout_type": "ALL",
                }
            ],
        }

        path = tmp_path / "test_board.json"
        path.write_text(json.dumps(board_data))

        board, errors = load_board(path)

        assert board is not None
        assert len(board.keepouts) == 1
        keepout = board.keepouts[0]
        assert isinstance(keepout.shape, Circle)
        assert keepout.shape.center.x == 50
        assert keepout.shape.center.y == 50
        assert keepout.shape.radius == 10

    def test_parse_polygon_keepout_still_works(self, tmp_path: Path):
        """Verify polygon keepouts still work alongside circle support."""
        board_data = {
            "metadata": {"designUnits": "MILLIMETER"},
            "boundary": {"coordinates": [[0, 0], [100, 0], [100, 100], [0, 100]]},
            "stackup": {"layers": []},
            "nets": [],
            "components": {},
            "traces": {},
            "vias": {},
            "keepouts": [
                {
                    "uid": "keepout_polygon_1",
                    "name": "TEST_POLYGON",
                    "layer": "ALL",
                    "shape": {
                        "type": "polygon",
                        "coordinates": [[10, 10], [20, 10], [20, 20], [10, 20]],
                    },
                    "keepout_type": "ALL",
                }
            ],
        }

        path = tmp_path / "test_board.json"
        path.write_text(json.dumps(board_data))

        board, errors = load_board(path)

        assert board is not None
        assert len(board.keepouts) == 1
        keepout = board.keepouts[0]
        assert isinstance(keepout.shape, Polygon)


class TestCircleKeepoutUnitNormalization:
    """Tests for unit normalization of circle keepout radius values."""

    def test_circle_radius_scaled_from_microns(self):
        """Verify circle radius is scaled correctly from microns to mm."""
        data = {
            "metadata": {"designUnits": "MICRON"},
            "keepouts": [
                {
                    "shape": {
                        "type": "circle",
                        "center": [5000, 5000],
                        "radius": 2000,
                    }
                }
            ],
        }

        normalized, errors = normalize_units(data)

        assert len(errors) == 0
        # Radius should be scaled: 2000 microns = 2.0 mm
        assert normalized["keepouts"][0]["shape"]["radius"] == 2.0
        # Center should also be scaled: 5000 microns = 5.0 mm
        assert normalized["keepouts"][0]["shape"]["center"] == [5.0, 5.0]

    def test_circle_radius_unchanged_for_millimeters(self):
        """Verify circle radius is unchanged when already in mm."""
        data = {
            "metadata": {"designUnits": "MILLIMETER"},
            "keepouts": [
                {
                    "shape": {
                        "type": "circle",
                        "center": [5.0, 5.0],
                        "radius": 2.0,
                    }
                }
            ],
        }

        normalized, errors = normalize_units(data)

        assert len(errors) == 0
        assert normalized["keepouts"][0]["shape"]["radius"] == 2.0
        assert normalized["keepouts"][0]["shape"]["center"] == [5.0, 5.0]


class TestMalformedCircleKeepouts:
    """Tests for handling malformed circle keepout data."""

    def test_missing_center_sets_shape_to_none(self):
        """Circle keepout without center should have shape set to None."""
        data = {
            "keepouts": [
                {
                    "shape": {
                        "type": "circle",
                        "radius": 10,
                        # Missing "center"
                    }
                }
            ]
        }

        result = _parse_board_objects(data)

        assert result["keepouts"][0]["shape"] is None

    def test_non_dict_shape_sets_shape_to_none(self):
        """Keepout with non-dict shape should have shape preserved (not processed)."""
        data = {
            "keepouts": [
                {
                    "shape": None,  # Non-dict shape
                }
            ]
        }

        result = _parse_board_objects(data)

        # Non-dict shape is not processed and remains as-is
        assert result["keepouts"][0]["shape"] is None

    def test_string_shape_preserved(self):
        """Keepout with string shape should be preserved (not processed)."""
        data = {
            "keepouts": [
                {
                    "shape": "invalid_shape",  # String instead of dict
                }
            ]
        }

        result = _parse_board_objects(data)

        # Non-dict shape is preserved as-is (filtered by isinstance check)
        assert result["keepouts"][0]["shape"] == "invalid_shape"

    def test_missing_radius_sets_shape_to_none(self):
        """Circle keepout without radius should have shape set to None."""
        data = {
            "keepouts": [
                {
                    "shape": {
                        "type": "circle",
                        "center": [50, 50],
                        # Missing "radius"
                    }
                }
            ]
        }

        result = _parse_board_objects(data)

        assert result["keepouts"][0]["shape"] is None

    def test_invalid_center_type_sets_shape_to_none(self):
        """Circle keepout with invalid center type should have shape set to None."""
        data = {
            "keepouts": [
                {
                    "shape": {
                        "type": "circle",
                        "center": "invalid",  # Should be a list/tuple
                        "radius": 10,
                    }
                }
            ]
        }

        result = _parse_board_objects(data)

        assert result["keepouts"][0]["shape"] is None

    def test_center_wrong_length_sets_shape_to_none(self):
        """Circle keepout with center of wrong length should have shape set to None."""
        data = {
            "keepouts": [
                {
                    "shape": {
                        "type": "circle",
                        "center": [50, 50, 0],  # Should be length 2
                        "radius": 10,
                    }
                }
            ]
        }

        result = _parse_board_objects(data)

        assert result["keepouts"][0]["shape"] is None

    def test_invalid_radius_type_sets_shape_to_none(self):
        """Circle keepout with non-numeric radius should have shape set to None."""
        data = {
            "keepouts": [
                {
                    "shape": {
                        "type": "circle",
                        "center": [50, 50],
                        "radius": "invalid",  # Should be numeric
                    }
                }
            ]
        }

        result = _parse_board_objects(data)

        assert result["keepouts"][0]["shape"] is None


class TestCircleKeepoutRendering:
    """Tests for circle keepout rendering."""

    def test_render_circle_keepout_uses_circle_patch(self, tmp_path: Path):
        """Verify mpatches.Circle is used for circular keepouts."""
        board_data = {
            "metadata": {"designUnits": "MILLIMETER"},
            "boundary": {"coordinates": [[0, 0], [100, 0], [100, 100], [0, 100]]},
            "stackup": {"layers": []},
            "nets": [],
            "components": {},
            "traces": {},
            "vias": {},
            "keepouts": [
                {
                    "uid": "keepout_circle_1",
                    "name": "TEST_CIRCLE",
                    "layer": "ALL",
                    "shape": {
                        "type": "circle",
                        "center": [50, 50],
                        "radius": 10,
                    },
                    "keepout_type": "ALL",
                }
            ],
        }

        path = tmp_path / "test_board.json"
        path.write_text(json.dumps(board_data))

        board, _ = load_board(path)

        # Import render after loading to ensure Agg is used
        from pcb_renderer.render import draw_keepout

        # Create a mock axes object
        mock_ax = MagicMock()

        # Draw the keepout
        draw_keepout(mock_ax, board.keepouts[0], board_height=100)

        # Verify add_patch was called
        mock_ax.add_patch.assert_called_once()

        # Get the patch that was added
        patch = mock_ax.add_patch.call_args[0][0]

        # Verify it's a Circle patch (matplotlib patches)
        import matplotlib.patches as mpatches

        assert isinstance(patch, mpatches.Circle)

        # Verify the center coordinates (Y should be transformed: 100 - 50 = 50)
        assert patch.center == (50, 50)
        assert patch.radius == 10

    def test_render_polygon_keepout_uses_polygon_patch(self, tmp_path: Path):
        """Verify mpatches.Polygon is used for polygon keepouts."""
        board_data = {
            "metadata": {"designUnits": "MILLIMETER"},
            "boundary": {"coordinates": [[0, 0], [100, 0], [100, 100], [0, 100]]},
            "stackup": {"layers": []},
            "nets": [],
            "components": {},
            "traces": {},
            "vias": {},
            "keepouts": [
                {
                    "uid": "keepout_polygon_1",
                    "name": "TEST_POLYGON",
                    "layer": "ALL",
                    "shape": {
                        "type": "polygon",
                        "coordinates": [[10, 10], [20, 10], [20, 20], [10, 20]],
                    },
                    "keepout_type": "ALL",
                }
            ],
        }

        path = tmp_path / "test_board.json"
        path.write_text(json.dumps(board_data))

        board, _ = load_board(path)

        from pcb_renderer.render import draw_keepout

        mock_ax = MagicMock()
        draw_keepout(mock_ax, board.keepouts[0], board_height=100)

        mock_ax.add_patch.assert_called_once()
        patch = mock_ax.add_patch.call_args[0][0]

        import matplotlib.patches as mpatches

        assert isinstance(patch, mpatches.Polygon)


class TestMalformedKeepoutFullPipeline:
    """Tests for full parsing pipeline with malformed keepouts.

    These tests verify that the Board model can be instantiated with
    malformed keepouts, since Keepout.shape is Optional.
    """

    def test_load_board_with_malformed_circle_keepout(self, tmp_path: Path):
        """Verify load_board handles malformed circle keepouts gracefully."""
        board_data = {
            "metadata": {"designUnits": "MILLIMETER"},
            "boundary": {"coordinates": [[0, 0], [100, 0], [100, 100], [0, 100]]},
            "stackup": {"layers": []},
            "nets": [],
            "components": {},
            "traces": {},
            "vias": {},
            "keepouts": [
                {
                    "uid": "keepout_malformed_1",
                    "name": "MALFORMED_CIRCLE",
                    "layer": "ALL",
                    "shape": {
                        "type": "circle",
                        # Missing center and radius
                    },
                    "keepout_type": "ALL",
                }
            ],
        }

        path = tmp_path / "test_board.json"
        path.write_text(json.dumps(board_data))

        board, errors = load_board(path)

        # Board should load successfully with Optional shape
        assert board is not None
        assert len(board.keepouts) == 1
        assert board.keepouts[0].shape is None

    def test_load_board_with_mixed_valid_and_malformed_keepouts(self, tmp_path: Path):
        """Verify load_board handles mix of valid and malformed keepouts."""
        board_data = {
            "metadata": {"designUnits": "MILLIMETER"},
            "boundary": {"coordinates": [[0, 0], [100, 0], [100, 100], [0, 100]]},
            "stackup": {"layers": []},
            "nets": [],
            "components": {},
            "traces": {},
            "vias": {},
            "keepouts": [
                {
                    "uid": "keepout_valid",
                    "name": "VALID_CIRCLE",
                    "layer": "ALL",
                    "shape": {
                        "type": "circle",
                        "center": [50, 50],
                        "radius": 10,
                    },
                    "keepout_type": "ALL",
                },
                {
                    "uid": "keepout_malformed",
                    "name": "MALFORMED_CIRCLE",
                    "layer": "ALL",
                    "shape": {
                        "type": "circle",
                        "center": "invalid",  # Invalid center type
                        "radius": 10,
                    },
                    "keepout_type": "ALL",
                },
            ],
        }

        path = tmp_path / "test_board.json"
        path.write_text(json.dumps(board_data))

        board, errors = load_board(path)

        assert board is not None
        assert len(board.keepouts) == 2
        # First keepout should be valid
        assert isinstance(board.keepouts[0].shape, Circle)
        # Second keepout should have None shape
        assert board.keepouts[1].shape is None

    def test_render_skips_keepout_with_none_shape(self, tmp_path: Path):
        """Verify rendering skips keepouts with None shape without error."""
        board_data = {
            "metadata": {"designUnits": "MILLIMETER"},
            "boundary": {"coordinates": [[0, 0], [100, 0], [100, 100], [0, 100]]},
            "stackup": {"layers": []},
            "nets": [],
            "components": {},
            "traces": {},
            "vias": {},
            "keepouts": [
                {
                    "uid": "keepout_malformed",
                    "name": "MALFORMED_CIRCLE",
                    "layer": "ALL",
                    "shape": {
                        "type": "circle",
                        # Missing center and radius
                    },
                    "keepout_type": "ALL",
                }
            ],
        }

        path = tmp_path / "test_board.json"
        path.write_text(json.dumps(board_data))

        board, _ = load_board(path)
        assert board is not None
        assert board.keepouts[0].shape is None

        from pcb_renderer.render import draw_keepout

        mock_ax = MagicMock()

        # Should not raise when shape is None
        draw_keepout(mock_ax, board.keepouts[0], board_height=100)

        # add_patch should not be called since shape is None
        mock_ax.add_patch.assert_not_called()
