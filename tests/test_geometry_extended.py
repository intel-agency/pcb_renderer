"""Additional tests for pcb_renderer.geometry module to increase coverage."""

import pytest

from pcb_renderer.geometry import Circle, Point, Polygon, Polyline


class TestPointOperations:
    """Test Point arithmetic and transformation operations."""

    def test_point_addition(self):
        """Test vector addition of points."""
        p1 = Point(x=10.0, y=20.0)
        p2 = Point(x=5.0, y=3.0)
        result = p1 + p2
        assert result.x == 15.0
        assert result.y == 23.0

    def test_point_subtraction(self):
        """Test vector subtraction of points."""
        p1 = Point(x=10.0, y=20.0)
        p2 = Point(x=5.0, y=3.0)
        result = p1 - p2
        assert result.x == 5.0
        assert result.y == 17.0

    def test_point_scalar_multiplication(self):
        """Test scalar multiplication of points."""
        p = Point(x=10.0, y=20.0)
        result = p * 2.5
        assert result.x == 25.0
        assert result.y == 50.0

    def test_point_distance_to(self):
        """Test distance calculation between points."""
        p1 = Point(x=0.0, y=0.0)
        p2 = Point(x=3.0, y=4.0)
        assert p1.distance_to(p2) == pytest.approx(5.0)

    def test_point_rotate_around_origin(self):
        """Test point rotation around origin."""
        p = Point(x=1.0, y=0.0)
        rotated = p.rotate(90.0)  # 90 degrees counterclockwise
        assert rotated.x == pytest.approx(0.0, abs=1e-10)
        assert rotated.y == pytest.approx(1.0)

    def test_point_rotate_around_custom_origin(self):
        """Test point rotation around custom origin."""
        p = Point(x=2.0, y=0.0)
        origin = Point(x=1.0, y=0.0)
        rotated = p.rotate(90.0, origin=origin)
        assert rotated.x == pytest.approx(1.0, abs=1e-10)
        assert rotated.y == pytest.approx(1.0)

    def test_point_mirror_x(self):
        """Test point mirroring across Y-axis."""
        p = Point(x=10.0, y=20.0)
        mirrored = p.mirror_x()
        assert mirrored.x == -10.0
        assert mirrored.y == 20.0

    def test_point_to_array(self):
        """Test conversion to numpy array."""
        p = Point(x=10.0, y=20.0)
        arr = p.to_array()
        assert arr[0] == 10.0
        assert arr[1] == 20.0
        assert len(arr) == 2


class TestPolygonOperations:
    """Test Polygon methods."""

    def test_polygon_bbox(self):
        """Test bounding box calculation."""
        poly = Polygon(
            points=[Point(x=0, y=0), Point(x=100, y=0), Point(x=100, y=80), Point(x=0, y=80)]
        )
        min_x, min_y, max_x, max_y = poly.bbox()
        assert min_x == 0
        assert min_y == 0
        assert max_x == 100
        assert max_y == 80

    def test_polygon_contains_point_inside(self):
        """Test point containment for point inside polygon."""
        poly = Polygon(
            points=[Point(x=0, y=0), Point(x=100, y=0), Point(x=100, y=100), Point(x=0, y=100)]
        )
        assert poly.contains_point(Point(x=50, y=50)) is True

    def test_polygon_contains_point_outside(self):
        """Test point containment for point outside polygon."""
        poly = Polygon(
            points=[Point(x=0, y=0), Point(x=100, y=0), Point(x=100, y=100), Point(x=0, y=100)]
        )
        assert poly.contains_point(Point(x=150, y=150)) is False

    def test_polygon_contains_point_on_edge(self):
        """Test point containment for point on polygon edge."""
        poly = Polygon(
            points=[Point(x=0, y=0), Point(x=100, y=0), Point(x=100, y=100), Point(x=0, y=100)]
        )
        # Point on edge behavior depends on ray-casting implementation
        result = poly.contains_point(Point(x=50, y=0))
        assert isinstance(result, bool)

    def test_polygon_edges(self):
        """Test polygon edges iteration."""
        poly = Polygon(points=[Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10)])
        edges = list(poly.edges())
        # Polygon auto-closes, so we should have edges including the closing edge
        assert len(edges) >= 3
        # First edge
        assert edges[0][0].x == 0 and edges[0][0].y == 0
        assert edges[0][1].x == 10 and edges[0][1].y == 0

    def test_polygon_to_xy_lists(self):
        """Test conversion to separate X,Y coordinate lists."""
        poly = Polygon(points=[Point(x=0, y=0), Point(x=10, y=20), Point(x=30, y=40)])
        xs, ys = poly.to_xy_lists()
        assert 0 in xs
        assert 10 in xs
        assert 30 in xs
        assert 0 in ys
        assert 20 in ys
        assert 40 in ys


class TestPolylineOperations:
    """Test Polyline methods."""

    def test_polyline_length(self):
        """Test polyline total length calculation."""
        polyline = Polyline(points=[Point(x=0, y=0), Point(x=3, y=0), Point(x=3, y=4)])
        # Length = 3 + 4 = 7
        assert polyline.length() == pytest.approx(7.0)

    def test_polyline_length_empty(self):
        """Test polyline length for empty polyline."""
        polyline = Polyline(points=[])
        assert polyline.length() == 0.0

    def test_polyline_length_single_point(self):
        """Test polyline length for single point."""
        polyline = Polyline(points=[Point(x=0, y=0)])
        assert polyline.length() == 0.0

    def test_polyline_bbox(self):
        """Test polyline bounding box."""
        polyline = Polyline(points=[Point(x=0, y=10), Point(x=50, y=20), Point(x=25, y=5)])
        min_x, min_y, max_x, max_y = polyline.bbox()
        assert min_x == 0
        assert max_x == 50
        assert min_y == 5
        assert max_y == 20


class TestCircleOperations:
    """Test Circle methods."""

    def test_circle_contains_point_inside(self):
        """Test circle containing a point inside."""
        circle = Circle(center=Point(x=0, y=0), radius=10.0)
        assert circle.contains_point(Point(x=5, y=5)) is True

    def test_circle_contains_point_outside(self):
        """Test circle not containing a point outside."""
        circle = Circle(center=Point(x=0, y=0), radius=10.0)
        assert circle.contains_point(Point(x=15, y=0)) is False

    def test_circle_contains_point_on_boundary(self):
        """Test circle containing a point exactly on boundary."""
        circle = Circle(center=Point(x=0, y=0), radius=10.0)
        assert circle.contains_point(Point(x=10, y=0)) is True

    def test_circle_bbox(self):
        """Test circle bounding box calculation."""
        circle = Circle(center=Point(x=50, y=50), radius=10.0)
        min_x, min_y, max_x, max_y = circle.bbox()
        assert min_x == 40.0
        assert min_y == 40.0
        assert max_x == 60.0
        assert max_y == 60.0


class TestGeometryValidation:
    """Test geometry validation and edge cases."""

    def test_point_nan_rejection_x(self):
        """Test that Point rejects NaN x coordinate."""
        with pytest.raises(ValueError, match="finite"):
            Point(x=float("nan"), y=0.0)

    def test_point_nan_rejection_y(self):
        """Test that Point rejects NaN y coordinate."""
        with pytest.raises(ValueError, match="finite"):
            Point(x=0.0, y=float("nan"))

    def test_point_inf_rejection_x(self):
        """Test that Point rejects infinity x coordinate."""
        with pytest.raises(ValueError, match="finite"):
            Point(x=float("inf"), y=0.0)

    def test_point_inf_rejection_y(self):
        """Test that Point rejects infinity y coordinate."""
        with pytest.raises(ValueError, match="finite"):
            Point(x=0.0, y=float("inf"))

    def test_circle_negative_radius(self):
        """Test that Circle rejects negative radius."""
        with pytest.raises(ValueError, match="positive"):
            Circle(center=Point(x=0, y=0), radius=-5.0)

    def test_circle_zero_radius(self):
        """Test that Circle rejects zero radius."""
        with pytest.raises(ValueError, match="positive"):
            Circle(center=Point(x=0, y=0), radius=0.0)

    def test_circle_inf_radius(self):
        """Test that Circle rejects infinite radius."""
        with pytest.raises(ValueError, match="finite"):
            Circle(center=Point(x=0, y=0), radius=float("inf"))

    def test_circle_nan_radius(self):
        """Test that Circle rejects NaN radius."""
        with pytest.raises(ValueError, match="finite"):
            Circle(center=Point(x=0, y=0), radius=float("nan"))

    def test_polygon_min_length_validation(self):
        """Test that Polygon requires at least 3 points."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="at least 3"):
            Polygon(points=[Point(x=0, y=0), Point(x=1, y=1)])

    def test_polygon_auto_close(self):
        """Test that Polygon auto-closes if not already closed."""
        poly = Polygon(points=[Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10)])
        # Should have 4 points after auto-close (first point appended)
        assert len(poly.points) == 4
        assert poly.points[0] == poly.points[-1]

    def test_polygon_already_closed(self):
        """Test Polygon when first and last points are already the same."""
        poly = Polygon(
            points=[Point(x=0, y=0), Point(x=10, y=0), Point(x=10, y=10), Point(x=0, y=0)]
        )
        # Should not duplicate the closing point
        assert len(poly.points) == 4
        assert poly.points[0] == poly.points[-1]
