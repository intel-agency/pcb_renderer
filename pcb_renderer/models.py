"""Pydantic data models for PCB structures.

This module defines the core data models used throughout the PCB Renderer pipeline.
These models represent the parsed and normalized PCB board structure.

Data Flow:
----------
    Input JSON → parse.py → **models.py** → validate.py → render.py

Key Design Decisions:
--------------------
1. **Permissive Parsing**: All models use `extra="ignore"` to allow unknown fields.
   This prevents parse failures when the input JSON has extra fields not in the schema.
   Semantic validation is handled separately in validate.py.

2. **Field Aliases**: `populate_by_name=True` allows models to accept both the
   Pydantic field name and the JSON field name (e.g., `net_class` vs `class`).

3. **Optional Boundary**: `Board.boundary` is Optional to allow validate.py to
   report MISSING_BOUNDARY instead of failing at parse time.

4. **Relaxed Polyline**: Polyline minimum length is not strictly enforced at
   model level; MALFORMED_TRACE is detected in validate.py.

Model Hierarchy:
---------------
::

    Board
    ├── metadata (Dict)
    ├── boundary (Optional[Polygon])
    ├── stackup (Dict[str, Any])
    ├── nets (List[Net])
    ├── components (Dict[str, Component])
    │   ├── transform (Transform → position, rotation, side)
    │   └── pins (Dict[str, Pin])
    ├── traces (Dict[str, Trace])
    │   └── path (Polyline)
    ├── vias (Dict[str, Via])
    │   └── center (Point)
    ├── pours (Dict)
    └── keepouts (List[Keepout])
        └── shape (Polygon | Circle)

Challenge Requirements:
----------------------
From the Quilter Backend Engineer Code Challenge, these models support:
- Parsing board boundary from `boundary.coordinates`
- Parsing components with reference designators and transforms
- Parsing traces with width and layer assignment
- Parsing vias with center, diameter, and hole_size
- Parsing keepout regions with polygon or circle shapes
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .geometry import Circle, Point, Polygon, Polyline


class Side(str, Enum):
    """Component placement side (which side of the PCB the component is on)."""

    FRONT = "FRONT"  # Top side of board
    BACK = "BACK"  # Bottom side of board (requires mirror transform)


class LayerType(str, Enum):
    """PCB layer types for stackup definition.

    The stackup defines the vertical structure of the PCB from top to bottom.
    """

    TOP = "TOP"  # Top copper layer
    BOTTOM = "BOTTOM"  # Bottom copper layer
    MID = "MID"  # Internal copper layer (signal routing)
    PLANE = "PLANE"  # Internal plane layer (power/ground)
    DIELECTRIC = "DIELECTRIC"  # Insulating layer between copper layers


class Layer(BaseModel):
    """Represents a single layer in the PCB stackup.

    Attributes:
        name: Layer identifier (e.g., "TOP", "L2", "BOTTOM")
        layer_type: Type of layer (TOP, BOTTOM, MID, PLANE, DIELECTRIC)
        index: Layer position in stackup (0 = top, increases downward)
        material: Physical properties (thickness, dielectric constant, etc.)
    """

    name: str
    layer_type: LayerType
    index: int
    material: Dict

    model_config = {"extra": "ignore", "populate_by_name": True}


class Net(BaseModel):
    """Electrical net (a set of connected pins/traces/vias).

    Attributes:
        name: Net identifier (e.g., "VCC", "GND", "NET001")
        net_class: Net classification (SIGNAL, POWER, etc.)
                   Uses alias 'class' for JSON compatibility.

    Note:
        The field is named net_class to avoid collision with Python's
        reserved keyword 'class'. JSON input uses "class": "SIGNAL".
    """

    name: str
    net_class: str = Field("SIGNAL", alias="class")  # Alias for JSON 'class' field

    model_config = {"extra": "ignore", "populate_by_name": True}


class Transform(BaseModel):
    """Component placement transform (position + rotation + side).

    Defines how a component is positioned on the board:
    1. Translate to position
    2. Rotate by rotation degrees (counterclockwise)
    3. Mirror if on BACK side

    Attributes:
        position: Component center in board coordinates (mm)
        rotation: Rotation angle in degrees (0-360)
        side: Which side of the board (FRONT or BACK)

    Validation:
        INVALID_ROTATION error (from challenge doc) is detected by the
        field validator if rotation is outside [0, 360].
    """

    position: Point
    rotation: float = 0.0
    side: Side = Side.FRONT

    model_config = {"extra": "ignore", "populate_by_name": True}

    @field_validator("rotation")
    @classmethod
    def validate_rotation(cls, value: float) -> float:
        """Validate rotation is within [0, 360] degrees.

        Challenge Doc: Components with rotation values outside of valid range
        should be detected and reported.
        """
        if not 0 <= value <= 360:
            raise ValueError("Rotation must be between 0 and 360 degrees")
        return value


class Pin(BaseModel):
    """Component pin (connection point for electrical connectivity).

    Attributes:
        name: Pin identifier within component (e.g., "1", "2", "VCC")
        comp_name: Name of parent component (for back-reference validation)
        net_name: Name of the net this pin connects to (None if unconnected)
        shape: Pin geometry (pad shape, size, etc.)
        position: Pin position relative to component origin
        rotation: Pin rotation in degrees
        is_throughhole: True for through-hole pins, False for SMD

    Validation:
        INVALID_PIN_REFERENCE error if comp_name doesn't match the
        parent component's name.
    """

    name: str
    comp_name: str
    net_name: Optional[str]
    shape: Dict
    position: Point
    rotation: float = 0.0
    is_throughhole: bool = False

    model_config = {"extra": "ignore", "populate_by_name": True}


class Component(BaseModel):
    """PCB component (resistor, capacitor, IC, etc.).

    Challenge Requirements:
        - Draw component outlines at their transformed positions
        - Show component reference designators (R1, C1, U1)
        - Handle rotation correctly

    Attributes:
        name: Component internal name/ID
        reference: Reference designator (e.g., "R1", "C1", "U1") - displayed on render
        footprint: Footprint name (e.g., "0402", "SOIC-8")
        outline: Component body dimensions {width, height}
        transform: Placement transform (position, rotation, side)
        pins: Dict of pins keyed by pin name
        user_preplaced: True if component position was user-specified

    Validation:
        - INVALID_ROTATION if transform.rotation outside [0, 360]
        - COMPONENT_OUTSIDE_BOUNDARY if center is outside board boundary
        - INVALID_PIN_REFERENCE if any pin.comp_name != self.name
    """

    name: str
    reference: str
    footprint: str
    outline: Dict
    transform: Transform
    pins: Dict[str, Pin]
    user_preplaced: bool = False

    model_config = {"extra": "ignore", "populate_by_name": True}


class Trace(BaseModel):
    """PCB trace (copper routing path between points).

    Challenge Requirements:
        - Draw traces as lines/paths with their specified width
        - Use different colors for different layers

    Attributes:
        uid: Unique trace identifier
        net_name: Name of net this trace belongs to
        layer_hash: Layer this trace is on (for color mapping)
        path: Polyline of trace path points
        width: Trace width in millimeters

    Validation:
        - MALFORMED_TRACE if path has < 2 points
        - NEGATIVE_WIDTH if width <= 0
        - DANGLING_TRACE if net_name not in board.nets
        - NONEXISTENT_LAYER if layer_hash not in stackup
    """

    uid: str
    net_name: str
    layer_hash: str
    path: Polyline
    width: float

    model_config = {"extra": "ignore", "populate_by_name": True}


class Via(BaseModel):
    """PCB via (vertical connection between layers).

    Challenge Requirements:
        - Draw vias as circles at their center positions with their diameter

    Attributes:
        uid: Unique via identifier
        net_name: Name of net this via connects
        center: Via center position in millimeters
        diameter: Outer diameter of via pad
        hole_size: Drill hole diameter (must be < diameter for valid annular ring)
        span: Layer span dict with 'start' and 'end' layer names

    Validation:
        - INVALID_VIA_GEOMETRY if hole_size >= diameter
        - NONEXISTENT_LAYER if start/end layers not in stackup
    """
    uid: str
    net_name: str
    center: Point
    diameter: float
    hole_size: float
    span: Dict[str, str]

    model_config = {"extra": "ignore", "populate_by_name": True}


class Keepout(BaseModel):
    """PCB keepout region (area where routing/placement is prohibited).

    Challenge Requirements:
        - Draw keepout regions with a distinct pattern or color
        - Mark them as restricted areas

    Attributes:
        uid: Unique keepout identifier
        name: Keepout name for display/reference
        layer: Layer this keepout applies to
        shape: Keepout geometry (Polygon or Circle). Optional to support
               permissive parsing of malformed keepouts.
        keepout_type: Type of restriction (e.g., "routing", "placement")

    Note:
        shape is Optional to allow parsing of malformed keepout entries
        without failing. validate.py will detect and report malformed keepouts.
    """
    uid: str
    name: str
    layer: str
    shape: Optional[Polygon | Circle]  # Optional for permissive parsing
    keepout_type: str

    model_config = {"extra": "ignore", "populate_by_name": True}


class Board(BaseModel):
    """Root model representing a complete PCB board.

    This is the top-level container for all PCB data. After parsing,
    this object is passed through validate_board() for semantic validation,
    then to render_board() for visualization.

    Data Flow:
        parse.py → Board → validate.py → render.py

    Attributes:
        metadata: Board metadata (title, units, etc.)
        boundary: Board outline polygon. Optional to allow MISSING_BOUNDARY
                  to be detected by validate.py rather than failing at parse.
        stackup: Layer stackup definition {layers: [...], totalThickness: N}
        nets: List of all electrical nets on the board
        components: Dict of components keyed by name
        traces: Dict of traces keyed by uid
        vias: Dict of vias keyed by uid
        pours: Dict of copper pours (ground planes, etc.)
        keepouts: List of keepout regions

    Validation (from challenge doc):
        See validate.py for complete list of 14 validation errors:
        - MISSING_BOUNDARY, SELF_INTERSECTING_BOUNDARY
        - MALFORMED_TRACE, NEGATIVE_WIDTH, DANGLING_TRACE
        - NONEXISTENT_NET, NONEXISTENT_LAYER
        - INVALID_PIN_REFERENCE, INVALID_ROTATION
        - COMPONENT_OUTSIDE_BOUNDARY, INVALID_VIA_GEOMETRY
        - MALFORMED_STACKUP, EMPTY_BOARD, INVALID_UNIT_SPECIFICATION
    """
    metadata: Dict
    boundary: Optional[Polygon] = None  # Optional for MISSING_BOUNDARY validation
    stackup: Dict[str, Any]  # Flexible dict for stackup variations
    nets: List[Net]
    components: Dict[str, Component]
    traces: Dict[str, Trace]
    vias: Dict[str, Via]
    pours: Dict = Field(default_factory=dict)
    keepouts: List[Keepout] = Field(default_factory=list)

    model_config = {"extra": "ignore", "populate_by_name": True}


# Ensure forward refs are resolved for Pydantic v2 compatibility
Board.model_rebuild()
