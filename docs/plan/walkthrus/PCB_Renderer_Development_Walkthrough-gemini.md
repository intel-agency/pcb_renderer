# **PCB Renderer: Step-by-Step Development Walkthrough**

**Objective:** Build a Python CLI tool to render ECAD JSON files to SVG/PNG/PDF with strict validation, plus a decoupled LLM-powered debugging plugin.

**Timeline:** 2 Days (Compressed)

**Tools:** Python 3.11+, Pydantic, Matplotlib, Numpy, uv.

## **Phase 0: Prerequisite & Project Setup**

**Summary:** Initialize the project structure, configure the build system, and lock dependencies to ensure a reproducible environment.

### **Step 0.1: Directory & Dependency Configuration**

* **Source:** development\_plan\_v2.md \> Technology Stack  
* **Source:** implementation\_guide\_v2.md \> Project Setup

**Acceptance Criteria (AC):**

* \[ \] Project directory created.  
* \[ \] pyproject.toml configured with correct python version and dependencies.  
* \[ \] Virtual environment active and dependencies installed via uv.

**Implementation (pyproject.toml):**

\[project\]  
name \= "pcb-renderer"  
version \= "0.1.0"  
description \= "PCB board renderer for ECAD JSON files"  
requires-python \= "\>=3.11"  
dependencies \= \[  
    "pydantic\>=2.0",  
    "matplotlib\>=3.7",  
    "numpy\>=1.24",  
\]

\[project.optional-dependencies\]  
dev \= \[  
    "pytest\>=7.4",  
    "pytest-cov\>=4.1",  
    "ruff\>=0.1",  
    "pyright\>=1.1",  
\]  
llm \= \[  
    "typer\>=0.9.0",  
    "openai\>=1.0.0",  
    "python-dotenv\>=1.0.0"  
\]

\[project.scripts\]  
pcb-render \= "pcb\_renderer.cli:main"  
llm-plugin \= "llm\_plugin.cli:app"

\[build-system\]  
requires \= \["hatchling"\]  
build-backend \= "hatchling.build"

**Results:**

* Running uv sync creates a .venv directory.  
* Running uv run python \--version returns Python 3.11+.

## **Phase 1: Core Models & Parsing**

**Summary:** Define the strict data schema and implement the JSON ingestion logic that normalizes all units to millimeters.

### **Step 1.1: Geometric Primitives**

* **Source:** implementation\_guide\_v2.md \> Core Geometry  
* **Source:** architecture\_guide\_v2.md \> Module Organization

**AC:**

* \[ \] Point model rejects NaN or Infinite values.  
* \[ \] Polygon model requires at least 3 points.

**Implementation (pcb\_renderer/geometry.py):**

from pydantic import BaseModel, field\_validator  
import math  
from typing import List

class Point(BaseModel):  
    x: float  
    y: float

    @field\_validator('x', 'y')  
    @classmethod  
    def validate\_finite(cls, v: float) \-\> float:  
        if not math.isfinite(v):  
            raise ValueError(f"Coordinate must be finite, got {v}")  
        return v

class Polygon(BaseModel):  
    points: List\[Point\]

    @field\_validator('points')  
    @classmethod  
    def validate\_points(cls, v: List\[Point\]) \-\> List\[Point\]:  
        if len(v) \< 3:  
            raise ValueError("Polygon must have at least 3 points")  
        return v

### **Step 1.2: PCB Data Models**

* **Source:** architecture\_guide\_v2.md \> models.py  
* **Source:** Application Implementation Specification\_ PCB Renderer.md \> Requirements

**AC:**

* \[ \] Via model validates that hole\_size is strictly smaller than diameter.  
* \[ \] Trace model ensures width is positive.  
* \[ \] Component model parses pin dictionaries.

**Implementation (pcb\_renderer/models.py):**

from typing import List, Dict, Optional, Literal, Union  
from pydantic import BaseModel, Field, model\_validator, field\_validator  
from .geometry import Point, Polygon

class Via(BaseModel):  
    uid: str  
    location: Point  
    diameter: float  
    hole\_size: float  
    net\_id: str  
    layers: List\[str\]

    @model\_validator(mode='after')  
    def check\_hole\_size(self):  
        if self.hole\_size \>= self.diameter:  
            raise ValueError(f"Via hole size {self.hole\_size} must be smaller than diameter {self.diameter}")  
        return self

class Trace(BaseModel):  
    uid: str  
    net\_id: str  
    width: float  
    layer: str  
    points: List\[Point\]

    @field\_validator('width')  
    @classmethod  
    def validate\_width(cls, v: float) \-\> float:  
        if v \<= 0: raise ValueError("Trace width must be positive")  
        return v

class Component(BaseModel):  
    uid: str  
    designator: str  
    location: Point  
    rotation: float  
    side: Literal\['TOP', 'BOTTOM'\]  
    pins: Dict\[str, Point\] 

class Board(BaseModel):  
    metadata: Dict\[str, Union\[str, float\]\]  
    boundary: Optional\[Polygon\] \= None  
    components: List\[Component\] \= Field(default\_factory=list)  
    traces: List\[Trace\] \= Field(default\_factory=list)  
    vias: List\[Via\] \= Field(default\_factory=list)  
    nets: List\[Dict\[str, str\]\] \= Field(default\_factory=list)

### **Step 1.3: Parsing & Normalization Logic**

* **Source:** development\_plan\_v2.md \> Phase 1  
* **Source:** architecture\_guide\_v2.md \> parse.py

**AC:**

* \[ \] Detects designUnits from JSON metadata.  
* \[ \] Converts MICRON, MILS, INCH to Millimeters.  
* \[ \] Recursively normalizes nested lists and dictionaries.

**Implementation (pcb\_renderer/parse.py):**

import json  
from pathlib import Path  
from typing import Any, Tuple, List, Optional  
from .models import Board  
from .errors import ValidationError

def normalize\_recursive(data: Any, scale: float) \-\> Any:  
    if isinstance(data, float): return data \* scale  
    if isinstance(data, dict): return {k: normalize\_recursive(v, scale) for k, v in data.items()}  
    if isinstance(data, list): return \[normalize\_recursive(i, scale) for i in data\]  
    return data

def load\_board(path: Path) \-\> Tuple\[Optional\[Board\], List\[ValidationError\]\]:  
    try:  
        with open(path, 'r') as f:  
            raw \= json.load(f)  
          
        units \= raw.get('metadata', {}).get('designUnits', 'MILLIMETER')  
        scale \= {'MICRON': 0.001, 'MILS': 0.0254, 'INCH': 25.4}.get(units, 1.0)  
          
        normalized \= normalize\_recursive(raw, scale)  
        return Board(\*\*normalized), \[\]  
    except Exception as e:  
        return None, \[ValidationError(code="PARSE\_ERROR", severity="FATAL", message=str(e), json\_path="root")\]

## **Phase 2: Validation Layer**

**Summary:** Implement the "Building Inspector" that checks the board against 14 specific rules.

### **Step 2.1: Error Definitions**

* **Source:** architecture\_guide\_v2.md \> Error Reporting

**AC:**

* \[ \] ValidationError dataclass defined with code, severity, message, json\_path.

**Implementation (pcb\_renderer/errors.py):**

from dataclasses import dataclass

@dataclass  
class ValidationError:  
    code: str  
    severity: str  
    message: str  
    json\_path: str

### **Step 2.2: The Validator Logic**

* **Source:** development\_plan\_v2.md \> Phase 2  
* **Source:** Application Implementation Specification\_ PCB Renderer.md \> Features

**AC:**

* \[ \] Detects MISSING\_BOUNDARY.  
* \[ \] Detects NONEXISTENT\_NET (Trace referencing unknown net).  
* \[ \] Detects DANGLING\_TRACE (Connectivity check).

**Implementation (pcb\_renderer/validate.py):**

from typing import List  
from .models import Board  
from .errors import ValidationError

def validate\_board(board: Board) \-\> List\[ValidationError\]:  
    errors \= \[\]  
      
    \# Check 1: Geometry \- Missing Boundary  
    if not board.boundary:  
        errors.append(ValidationError("MISSING\_BOUNDARY", "ERROR", "Board has no boundary", "$.boundary"))  
          
    \# Check 2: Connectivity \- Non-existent Net  
    valid\_net\_ids \= {n\['id'\] for n in board.nets}  
    for i, trace in enumerate(board.traces):  
        if trace.net\_id not in valid\_net\_ids:  
            errors.append(ValidationError("NONEXISTENT\_NET", "ERROR", f"Unknown net {trace.net\_id}", f"$.traces\[{i}\]"))

    \# ... Implement remaining 12 checks here ...  
      
    return errors

## **Phase 3: Coordinate Transformation**

**Summary:** Bridge the gap between ECAD (Bottom-Left) and Screen (Top-Left) coordinate systems, including X-Ray views.

### **Step 3.1: Transform Math**

* **Source:** architecture\_guide\_v2.md \> Coordinate System Details  
* **Source:** implementation\_guide\_v2.md \> Transform Math

**AC:**

* \[ \] world\_to\_screen inverts the Y-axis.  
* \[ \] get\_component\_matrix handles translation, rotation, and *mirroring* (for Bottom components).

**Implementation (pcb\_renderer/transform.py):**

import numpy as np  
from .models import Component, Point

def world\_to\_screen(point: Point, board\_height: float, margin: float \= 10.0) \-\> Point:  
    \# ECAD Y-Flip: y\_screen \= height \- y\_world  
    return Point(x=point.x \+ margin, y=(board\_height \- point.y) \+ margin)

def get\_component\_matrix(comp: Component) \-\> np.ndarray:  
    \# 3x3 Affine Transform  
    theta \= np.radians(comp.rotation)  
    c, s \= np.cos(theta), np.sin(theta)  
      
    \# Rotation Matrix  
    rotation \= np.array(\[\[c, \-s, 0\], \[s, c, 0\], \[0, 0, 1\]\])  
    \# Mirror Matrix (X-flip) for X-Ray view of bottom components  
    mirror \= np.array(\[\[-1, 0, 0\], \[0, 1, 0\], \[0, 0, 1\]\]) if comp.side \== 'BOTTOM' else np.eye(3)  
    \# Translation Matrix  
    translation \= np.array(\[\[1, 0, comp.location.x\], \[0, 1, comp.location.y\], \[0, 0, 1\]\])  
      
    return translation @ rotation @ mirror

## **Phase 4: Rendering Engine**

**Summary:** Generate the visual output using Matplotlib.

### **Step 4.1: Rendering Pipeline**

* **Source:** implementation\_guide\_v2.md \> Rendering  
* **Source:** development\_plan\_v2.md \> Phase 4

**AC:**

* \[ \] Renders Boundary, Traces, Vias, and Components.  
* \[ \] Respects Z-Order (Traces \> Vias).  
* \[ \] Saves to path specified.

**Implementation (pcb\_renderer/render.py):**

import matplotlib.pyplot as plt  
from matplotlib.patches import Polygon as MplPolygon, Circle  
from .models import Board

def render\_board(board: Board, output\_path: str):  
    fig, ax \= plt.subplots(figsize=(10, 10))  
    ax.set\_aspect('equal')  
      
    if board.boundary:  
        poly \= MplPolygon(\[(p.x, p.y) for p in board.boundary.points\], closed=True, fill=False, edgecolor='black')  
        ax.add\_patch(poly)

    for trace in board.traces:  
        color \= 'red' if trace.layer \== 'TOP' else 'blue'  
        x, y \= zip(\*\[(p.x, p.y) for p in trace.points\])  
        ax.plot(x, y, color=color, linewidth=trace.width, zorder=2)

    for via in board.vias:  
        circle \= Circle((via.location.x, via.location.y), via.diameter/2, color='orange', zorder=3)  
        ax.add\_patch(circle)

    ax.autoscale()  
    plt.axis('off')  
    plt.savefig(output\_path, dpi=300, bbox\_inches='tight')  
    plt.close()

## **Phase 5: CLI Orchestration**

**Summary:** Wire all components together into a usable command-line tool.

### **Step 5.1: CLI Entry Point**

* **Source:** implementation\_guide\_v2.md \> CLI  
* **Source:** Application Implementation Specification\_ PCB Renderer.md \> Requirements

**AC:**

* \[ \] Accepts \--input and \--output arguments.  
* \[ \] Implements Strict Mode (Exit 1 on validation error).  
* \[ \] Implements Data Export (--export-json) for the LLM plugin.

**Implementation (pcb\_renderer/cli.py):**

import argparse  
import sys  
import json  
from pathlib import Path  
from .parse import load\_board  
from .validate import validate\_board  
from .render import render\_board

def main():  
    parser \= argparse.ArgumentParser(description="PCB Renderer")  
    parser.add\_argument("input", type=Path)  
    parser.add\_argument("-o", "--output", type=Path, required=True)  
    parser.add\_argument("--export-json", type=Path, help="Export data for LLM Plugin")  
    args \= parser.parse\_args()

    board, parse\_errors \= load\_board(args.input)  
    if parse\_errors:  
        print(f"Parse Errors: {parse\_errors}", file=sys.stderr)  
        sys.exit(1)

    val\_errors \= validate\_board(board)  
      
    \# Export for LLM Plugin (Phase 9\)  
    if args.export\_json:  
        export\_data \= {  
            "board": board.model\_dump(),  
            "errors": \[vars(e) for e in val\_errors\]  
        }  
        with open(args.export\_json, "w") as f:  
            json.dump(export\_data, f, default=str)

    if val\_errors:  
        print(f"Validation failed with {len(val\_errors)} errors.", file=sys.stderr)  
        sys.exit(1)

    render\_board(board, args.output)  
    sys.exit(0)

## **Phase 6: Testing**

**Summary:** Verify correctness using pytest and provided board files.

### **Step 6.1: Integration Tests**

* **Source:** development\_plan\_v2.md \> Phase 6  
* **Source:** implementation\_guide\_v2.md \> Board Tests

**AC:**

* \[ \] test\_board\_kappa confirms detection of MALFORMED\_TRACE.

**Implementation (tests/test\_boards.py):**

from pcb\_renderer.parse import load\_board  
from pcb\_renderer.validate import validate\_board

def test\_board\_kappa\_trace\_error():  
    board, errors \= load\_board("boards/board\_kappa.json")  
    if not errors: errors \= validate\_board(board)  
    assert any(e.code \== "MALFORMED\_TRACE" for e in errors)

## **Phase 7: CI/CD**

**Summary:** Automate verification on push.

### **Step 7.1: GitHub Actions**

* **Source:** development\_plan\_v2.md \> Phase 7

**AC:**

* \[ \] Workflow runs on Windows, Ubuntu, MacOS.

**Implementation (.github/workflows/ci.yml):**

name: CI  
on: \[push\]  
jobs:  
  test:  
    runs-on: ubuntu-latest  
    steps:  
      \- uses: actions/checkout@v4  
      \- run: pip install uv && uv sync  
      \- run: uv run pytest

## **Phase 8: Documentation**

**Summary:** Prepare the project for handover.

### **Step 8.1: README**

* **Source:** development\_plan\_v2.md \> Phase 8

**AC:**

* \[ \] README contains Installation, Usage, and Error Code Reference.

## **Phase 9: LLM Plugin (Decoupled)**

**Summary:** Create the standalone plugin for AI debugging.

### **Step 9.1: Plugin CLI**

* **Source:** llm\_plugin\_architecture.md \> Plugin Responsibilities  
* **Source:** plugin\_spec.md \> Functional Requirements

**AC:**

* \[ \] Command explain reads the exported JSON.  
* \[ \] Uses OpenAI API to generate explanations.

**Implementation (llm\_plugin/cli.py):**

import typer  
import json  
import os  
from openai import OpenAI  
from pathlib import Path

app \= typer.Typer()

@app.command()  
def explain(data\_file: Path):  
    with open(data\_file) as f:  
        data \= json.load(f)  
      
    errors \= data.get("errors", \[\])  
    if not errors:  
        print("No errors to explain.")  
        return

    client \= OpenAI(api\_key=os.getenv("OPENAI\_API\_KEY"))  
    prompt \= f"Explain this PCB error: {errors\[0\]}"  
      
    response \= client.chat.completions.create(  
        model="gpt-4",  
        messages=\[{"role": "user", "content": prompt}\]  
    )  
    print(response.choices\[0\].message.content)

if \_\_name\_\_ \== "\_\_main\_\_":  
    app()  
