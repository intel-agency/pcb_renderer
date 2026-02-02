import numpy as np

from pcb_renderer.geometry import Point
from pcb_renderer.models import Component, Transform
from pcb_renderer.transform import ecad_to_svg, svg_to_ecad, compute_component_transform, transform_point


def test_ecad_svg_roundtrip():
    p = Point(x=1.0, y=2.0)
    svg = ecad_to_svg(p, board_height=10.0)
    back = svg_to_ecad(svg, board_height=10.0)
    assert back == p


def test_component_transform_rotation():
    comp = Component(
        name="U1",
        reference="U1",
        footprint="QFN",
        outline={"width": 2, "height": 2},
        transform=Transform(position=Point(x=0, y=0), rotation=90.0),
        pins={},
    )
    m = compute_component_transform(comp)
    pt = transform_point(Point(x=1, y=0), m)
    assert np.isclose(pt.y, 1.0)
