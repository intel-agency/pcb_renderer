"""Pydantic models for PCB structures."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .geometry import Circle, Point, Polygon, Polyline


class Side(str, Enum):
    FRONT = "FRONT"
    BACK = "BACK"


class LayerType(str, Enum):
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    MID = "MID"
    PLANE = "PLANE"
    DIELECTRIC = "DIELECTRIC"


class Layer(BaseModel):
    name: str
    layer_type: LayerType
    index: int
    material: Dict

    model_config = {"extra": "ignore", "populate_by_name": True}


class Net(BaseModel):
    name: str
    net_class: str = Field("SIGNAL", alias="class")

    model_config = {"extra": "ignore", "populate_by_name": True}


class Transform(BaseModel):
    position: Point
    rotation: float = 0.0
    side: Side = Side.FRONT

    model_config = {"extra": "ignore", "populate_by_name": True}

    @field_validator("rotation")
    @classmethod
    def validate_rotation(cls, value: float) -> float:
        if not 0 <= value <= 360:
            raise ValueError("Rotation must be between 0 and 360 degrees")
        return value


class Pin(BaseModel):
    name: str
    comp_name: str
    net_name: Optional[str]
    shape: Dict
    position: Point
    rotation: float = 0.0
    is_throughhole: bool = False

    model_config = {"extra": "ignore", "populate_by_name": True}


class Component(BaseModel):
    name: str
    reference: str
    footprint: str
    outline: Dict
    transform: Transform
    pins: Dict[str, Pin]
    user_preplaced: bool = False

    model_config = {"extra": "ignore", "populate_by_name": True}

class Trace(BaseModel):
    uid: str
    net_name: str
    layer_hash: str
    path: Polyline
    width: float

    model_config = {"extra": "ignore", "populate_by_name": True}

class Via(BaseModel):
    uid: str
    net_name: str
    center: Point
    diameter: float
    hole_size: float
    span: Dict[str, str]

    model_config = {"extra": "ignore", "populate_by_name": True}


class Keepout(BaseModel):
    uid: str
    name: str
    layer: str
    shape: Optional[Polygon | Circle]
    keepout_type: str

    model_config = {"extra": "ignore", "populate_by_name": True}


class Board(BaseModel):
    metadata: Dict
    boundary: Optional[Polygon] = None
    stackup: Dict[str, Any]
    nets: List[Net]
    components: Dict[str, Component]
    traces: Dict[str, Trace]
    vias: Dict[str, Via]
    pours: Dict = Field(default_factory=dict)
    keepouts: List[Keepout] = Field(default_factory=list)

    model_config = {"extra": "ignore", "populate_by_name": True}
# Ensure forward refs are resolved
Board.model_rebuild()
