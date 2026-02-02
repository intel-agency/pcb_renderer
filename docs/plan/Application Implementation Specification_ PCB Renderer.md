# **Application Implementation Specification: PCB Renderer**

## **New Application**

**App Title:** PCB Renderer (Core)

## **Development Plan**

**Summary:**

The project operates under a strict, condensed 2-day development timeline where **correctness is prioritized over performance**. The primary goal is to produce a tool that is mathematically rigorous and visually accurate, rather than optimizing for high-throughput rendering speed. The implementation roadmap is structured into 8 distinct, sequential phases to ensure stability and testability at every step:

1. **Core Models & Parsing (Phase 1 \- 4 Hours):** Development of strict Pydantic data models to represent PCB entities (Components, Traces, Vias, Keepouts). This phase centers on the JSON parser, which must automatically detect designUnits (e.g., MICRON, MILLIMETER) and normalize all internal geometric coordinates to a single standard unit (Millimeters) to ensure consistent downstream math. Pydantic validators will be used here to catch "impossible" geometry (e.g., NaN coordinates, negative widths) immediately upon loading.  
2. **Validation Layer (Phase 2 \- 3 Hours):** Implementation of the logical validation engine. This involves coding 14 specific error detection rules that check for physical and logical consistency. Developers will map specific error codes to the provided "Greek letter" test boards (e.g., board\_kappa.json) to verify that the system correctly identifies specific failure modes like dangling traces or nonexistent nets.  
3. **Coordinate Systems (Phase 3 \- 2 Hours):** Implementation of the geometric transformation logic. This phase bridges the gap between ECAD coordinate systems (Cartesian, Bottom-Left Origin) and Rendering coordinate systems (Screen, Top-Left Origin). It requires implementing Affine transformations to handle component rotation, translation, and the specific "X-Ray" mirroring required for viewing Bottom-layer components from the Top-down perspective.  
4. **Rendering Engine (Phase 4 \- 5 Hours):** Construction of the Matplotlib-based rendering pipeline. This is the largest phase, requiring the mapping of geometric primitives (LineStrings, Polygons) to Matplotlib patches. It involves setting up the "Z-Order" stack (e.g., Substrate \< Bottom Copper \< Top Copper \< Silkscreen) to ensure layers overlap correctly in the final output file (SVG/PNG/PDF).  
5. **CLI Orchestration (Phase 5 \- 2 Hours):** Wiring the components into a cohesive Command Line Interface. This includes setting up argparse to handle flags, implementing the "Strict" vs "Permissive" execution modes, and designing the user feedback loop (Standard Output for progress, Standard Error for structured failure reports).  
6. **Testing Strategy (Phase 6 \- 4 Hours):** Execution of comprehensive unit and integration tests. This involves not just running the tests, but manually verifying the visual output of valid boards to ensure the rendering engine is interpreting the coordinates correctly (e.g., ensuring text isn't upside down).  
7. **CI/CD Pipeline (Phase 7 \- 1 Hour):** Configuration of GitHub Actions to enforce cross-platform compatibility. The pipeline must verify that the renderer functions identically on Windows, macOS, and Linux environments, particularly regarding file path handling and floating-point determinism.  
8. **Documentation & Polish (Phase 8 \- 2 Hours):** Finalizing the artifact for handoff. This includes writing a comprehensive README, generating API documentation via docstrings, and preparing the ARCHITECTURE.md to explain the system design to future maintainers.

**See development\_plan\_v2.md for the detailed timeline, hourly resource allocation, and specific risk mitigation strategies.**

## **Description**

The PCB Renderer is a standalone Command-Line Interface (CLI) tool designed to serve as the visual verification step in automated Electronics Design Automation (EDA) pipelines. Its purpose is to ingest JSON representations of Printed Circuit Board (PCB) designs, validate them against a strict set of manufacturability and logic rules, and render them into high-fidelity visual formats.

Unlike generic vector drawing tools, this application is domain-aware: it understands the difference between a "Trace" and a "Keepout," handles the specific geometric mirroring required to view the bottom of a board, and enforces logical connectivity rules. It prioritizes **deterministic output**, ensuring that the same input JSON always produces the exact same binary output file, and **strict validation**, ensuring that invalid designs fail explicitly rather than producing misleading visual artifacts.

## **Overview**

The PCB Renderer acts as a gatekeeper in the ECAD workflow. It ingests raw JSON data exported from board design software, acts as a normalizing filter (converting all distinct units to Millimeters), and applies a rigorous "Linting" process to the design.

The system is built on two core operational modes:

1. **Strict Mode (Default):** The application fails immediately upon detecting any validation error (e.g., a trace is too thin, or a component is outside the board boundary). This is intended for CI/CD pipelines where broken builds should be rejected.  
2. **Permissive Mode:** The application attempts to render the board even if errors are present, logging the errors as warnings instead. This allows engineers to visualize partial or in-progress designs to debug issues.

The renderer leverages Matplotlib not for data graphing, but as a robust 2D geometry engine, utilizing its sophisticated patch collection and coordinate transformation capabilities to generate publication-quality vector (SVG, PDF) and raster (PNG) images.

## **Document Links**

* architecture\_guide\_v2.md \- Definitive guide on system architecture, module boundaries, and design principles (Correctness \> Performance).  
* development\_plan\_v2.md \- The project roadmap, technology stack decisions, and risk assessment.  
* implementation\_guide\_v2.md \- Detailed code snippets, directory structures, and specific algorithms for coordinate transformation.

## **Requirements**

### **Functional Requirements**

* **Input Parsing & Normalization:**  
  * The system must accept a file path to a JSON file.  
  * It must parse the designUnits field (supporting MICRON, MILLIMETER, MILS, INCH).  
  * It must normalize **all** spatial coordinates (points, widths, diameters, bounds) into Millimeters (float) immediately upon loading.  
  * It must handle floating-point precision issues by using a consistent epsilon for comparisons.  
* **Validation Logic:**  
  The system must implement a validation engine that runs **before** rendering. It must execute 14 distinct error checks across three categories:  
  * **Geometry:**  
    * MISSING\_BOUNDARY: No board outline defined.  
    * SELF\_INTERSECTING\_BOUNDARY: The board outline crosses itself (bowtie shape).  
    * MALFORMED\_TRACE: Traces with fewer than 2 points.  
    * OFF\_BOARD\_COMPONENT: Component centroids located outside the board boundary.  
  * **Connectivity:**  
    * DANGLING\_TRACE: Traces that do not start or end at a Component Pad or Via.  
    * NONEXISTENT\_NET: Traces or Vias referencing a netId not present in the global netlist.  
  * **Dimensions:**  
    * NEGATIVE\_WIDTH: Traces or pads with width \<= 0\.  
    * INVALID\_DIAMETER: Vias where the drill hole is larger than or equal to the annular ring.

All errors must be returned as structured objects containing a machine-readable code, a human-readable message, and a json\_path locating the error in the input file.

* **Rendering Pipeline:**  
  * Must generate standard image formats: SVG (Scalable Vector Graphics), PNG (Portable Network Graphics), and PDF.  
  * Must implement deterministic "Z-Ordering" to simulate physical board stack-up:  
    1. Board Substrate (Bottom)  
    2. Bottom Layer Copper  
    3. Top Layer Copper  
    4. Silkscreen / Reference Designators (Top)  
  * Must support color-coding by layer (e.g., Red for Top Copper, Blue for Bottom Copper).  
* **Coordinate Transformation:**  
  \* Must mathematically convert ECAD coordinates (Origin: Bottom-Left) to Image coordinates (Origin: Top-Left).  
  * Must apply specific transformations for the "X-Ray" view: Bottom-layer components must be **mirrored** horizontally to simulate looking through the board substrate.  
  * Must handle component-local transformations: translating component primitives to the component's location and applying rotation.  
* **CLI Interface:**  
  * \--input: Path to the source JSON file.  
  * \--output / \-o: Path to the destination image file.  
  * \--verbose / \-v: specific flag to enable detailed INFO logging to stdout.  
  * \--quiet / \-q: specific flag to suppress all stdout (stderr remains active for errors).  
  * \--format: Explicit override for output format (svg/png/pdf), otherwise inferred from output filename extension. \* \--export-json: Flag to dump the internal normalized data structure and validation errors to a JSON file. This is the integration point for the LLM Plugin.

### **Non-Functional Requirements**

* **Correctness & Precision:**  
  * Geometric validity is paramount. Logic must handle floating-point comparisons robustly (e.g., using numpy.isclose).  
  * The renderer must not "smooth" or "anti-alias" geometry in a way that obscures design faults (e.g., gaps in traces must be visible).  
* **Determinism:**  
  * The application must produce bit-exact output for identical inputs. This may require setting explicit seeds or disabling timestamps in generated metadata (e.g., SVG creation dates).  
* **Reviewability:**  
  * The codebase must be written for readability. Type hints are mandatory. Complex logic (like matrix transformations) must be documented with comments explaining the math.  
* **Environment Compatibility:**  
  * The tool must function identically on Windows, macOS, and Linux. File path handling must use pathlib to ensure OS-agnostic path separators.

## **Features**

1. **Multi-Format Rendering Engine:**  
   A unified rendering pipeline that supports SVG for web viewing, PDF for documentation/printing, and PNG for quick thumbnails. All formats share the same geometry generation logic to ensure visual consistency.  
2. **Strict & Permissive Modes:**  
   * **Strict (Default):** Any validation error (Severity: ERROR) causes the CLI to exit with code 1 and abort rendering. This prevents "bad" boards from silently passing through a pipeline. \* **Permissive:** Renders the board regardless of errors. Validation errors are printed to stderr as warnings. This is critical for debugging "work in progress" designs.  
3. **Advanced Visual Styling:**  
   * **Reference Designator Halos:** Text labels (e.g., "R1", "U2") are rendered with a semi-transparent background "halo" to ensure they remain readable even when crossing over dense copper traces.  
   * **Hatched Keepouts:** "Keepout" zones are rendered with a distinct hatched pattern (diagonal lines) to visually differentiate them from solid copper planes.  
   * **Configurable Palette:** Layer colors (Top Copper, Bottom Copper, Silk, Substrate) are defined in a centralized configuration, allowing for easy theming (e.g., "OshPark Purple" vs "Standard Green").  
4. **X-Ray View Simulation:**  
   The renderer simulates a "Top-Down" view of the physical board. Components on the bottom layer are rendered as if seen *through* the fiberglass substrate. This requires logically mirroring the bottom geometry across the Y-axis so that the pin order appears correct from the top perspective.  
5. **Structured Error Reporting:**  
   Errors are not just printed strings; they are structured data. Each error includes a JSON Path (e.g., $.traces\[4\].segments\[0\]) allowing downstream tools (like the LLM plugin) to programmatically identify exactly which part of the input file caused the failure.

## **Test Cases**

* **Unit Tests (Component Level):**  
  * test\_models.py: Verify Pydantic models reject invalid data types (e.g., strings where floats are expected) and catch logical impossibilities (Negative width, Infinite coordinates).  
  * test\_parse.py: Test the unit conversion logic. Verify that 1000 MICRONS becomes 1.0 (mm) and 1 INCH becomes 25.4 (mm).  
  * test\_transform.py: Verify the Affine transformation matrices. Test that a point (1, 1\) rotated 90 degrees becomes (-1, 1\) (or (1, \-1) depending on the coordinate system). Verify the Y-axis flip logic.  
* **Integration Tests (Full Board Validation):**  
  These tests run against the specific "Greek Letter" board files provided in the boards/ directory:  
  * **Board Kappa (Malformed Trace):** Verify the validator catches a trace defined by a single point (needs at least 2). Expected Code: MALFORMED\_TRACE.  
  * **Board Theta (Connectivity):** Verify the validator catches a Via referencing a netId that is not in the nets list. Expected Code: NONEXISTENT\_NET.  
  * **Board Eta (Dimensions):** Verify the validator catches a trace with a negative width value. Expected Code: NEGATIVE\_WIDTH.  
  * **Board X (Boundary):** Verify the validator catches a missing boundary or a boundary polygon that intersects itself (bowtie). Expected Code: MISSING\_BOUNDARY or SELF\_INTERSECTING\_BOUNDARY.  
  * **Board Alpha (Golden Path):** A perfectly valid board. Verify that it parses, validates with 0 errors, and produces an output file.

## **Logging**

* **Standard Output (stdout):**  
  * Reserved for user-facing progress information in Verbose mode.  
  * Messages: "Loading board...", "Normalizing units...", "Validation passed.", "Rendering to output.svg...".  
  * Suppressed entirely when \--quiet is passed.  
* **Standard Error (stderr):**  
  * Reserved for application failures and validation errors.  
  * Format: \[SEVERITY\] ErrorCode: Message (Location).  
  * Example: \[ERROR\] DANGLING\_TRACE: Trace 't1' does not connect to any pad at (10.5, 20.0).  
* **Data Export (JSON):**  
  * When \--export-json is used, the log includes a full dump of the normalized board state and the list of error objects. This file serves as the input for the LLM Plugin.

## **Containerization: Docker**

**Dockerfile Strategy:**

The Docker approach emphasizes reproducibility and minimalism.

* **Base Image:** python:3.11-slim. The slim variant is chosen to reduce image size (\~150MB) while maintaining compatibility with standard Python wheels. Alpine is avoided due to potential compatibility issues with matplotlib and numpy C-extensions.  
* **System Dependencies:** libfreetype6-dev is explicitly installed to ensure Matplotlib has the necessary libraries for font rendering (text is crucial for Reference Designators).  
* **Package Management:** uv is installed and used for dependency resolution. uv sync \--frozen ensures that the container uses the exact package versions locked in uv.lock.  
* **Entrypoint:** The container is configured as an executable. Arguments passed to docker run are passed directly to the pcb-render CLI.

\<\!-- end list \--\>

\# Use slim image for smaller footprint but full glibc compatibility  
FROM python:3.11-slim

\# Install system libraries required for Matplotlib font rendering  
RUN apt-get update && apt-get install \-y libfreetype6-dev && rm \-rf /var/lib/apt/lists/\*

WORKDIR /app

\# Copy dependency definitions first to leverage Docker layer caching  
COPY pyproject.toml uv.lock ./

\# Install uv and sync dependencies  
RUN pip install uv && uv sync \--frozen

\# Copy the actual application source code  
COPY . .

\# Set entrypoint to run the application via uv  
ENTRYPOINT \["uv", "run", "pcb-render"\]

## **Documentation**

* **README.md:** The primary entry point. Must include:  
  * **Installation:** Instructions using uv sync or pip install ..  
  * **Quick Start:** Example commands for rendering the demo boards.  
  * **Error Reference:** A table listing all error codes (e.g., OFF\_BOARD\_COMPONENT) and their meanings.  
  * **Future Work:** A placeholder section (as requested by the plan) outlining potential features like Gerber export or 3D visualization.  
* **Docstrings:** Every public module, class, and function must have a Google-style docstring.  
  * **Modules:** Explain the module's responsibility (e.g., "Handles affine transformations...").  
  * **Functions:** document Args, Returns, and Raises.  
* **ARCHITECTURE.md:** A high-level document describing the pipeline flow (Parse \-\> Validate \-\> Transform \-\> Render) and the decision to prioritize correctness over performance.

## **Acceptance Criteria**

1. **CLI Execution & Output:**  
   * Running pcb-render valid\_board.json \-o output.svg must succeed (Exit Code 0\) and produce a valid SVG file.  
   * Running the command with the \--verbose flag must display step-by-step progress logs.  
2. **Error Handling & Exit Codes:**  
   * Running pcb-render invalid\_board.json (Strict Mode) must fail (Exit Code 1\) and print specific error messages to stderr.  
   * The error messages must contain the correct error code (e.g., MALFORMED\_TRACE) matching the input fault.  
3. **Visual Verification:**  
   * The rendered output must align with the ECAD coordinate system. The origin (0,0) in the input file must correspond to the bottom-left of the board in the image (handled via Y-flip).  
   * Text labels must be legible and oriented correctly (not upside down).  
   * Bottom layer components must appear mirrored (as if looking through the board).  
4. **Performance:**  
   * The renderer should process a typical board (50-100 components) in under 5 seconds on standard hardware.  
   * Note: While correctness is the priority, extreme slowness (e.g., \>30s) is considered a failure.

## **Language**

* **Primary Language:** Python  
* **Version:** 3.11+  
  * **Reasoning:** Python 3.11 offers significant performance improvements over 3.10. It also provides advanced typing features (like Self type) which aid in reviewability and static analysis.

## **Frameworks, Tools, Packages**

* **Validation:** pydantic\>=2.0  
  * Used for: Defining the schema of the board, components, and primitives. Automatically handling type coercion and basic validity checks (e.g., positive numbers).  
* **Rendering:** matplotlib\>=3.7  
  * Used for: The core 2D rendering engine. Its patches module allows for precise definition of polygons and circles, and its backend system handles file format export (SVG/PNG/PDF) uniformly.  
* **Math:** numpy\>=1.24  
  * Used for: Vectorized coordinate transformations. Managing arrays of points and performing matrix multiplication for rotation and translation.  
* **Package Manager:** uv  
  * Used for: Fast, deterministic dependency installation and lockfile management (uv.lock).  
* **Testing:** pytest, pytest-cov  
  * Used for: Running the test suite and ensuring 80%+ code coverage.  
* **Linting:** ruff, pyright  
  * Used for: Enforcing code style (linting) and static type checking to catch errors before runtime.

## **Project Structure**

The project structure is designed to be modular and testable, separating concerns into distinct files.

pcb-renderer/  
├── pyproject.toml          \# Definition of dependencies, build system, and tool config  
├── uv.lock                 \# Locked dependency versions for reproducibility  
├── pcb\_renderer/           \# Source code root package  
│   ├── \_\_init\_\_.py         \# Package marker  
│   ├── \_\_main\_\_.py         \# Application entry point (python \-m pcb\_renderer)  
│   ├── cli.py              \# CLI Argument parsing and Orchestration logic  
│   ├── models.py           \# Pydantic data models (Board, Component, Trace)  
│   ├── parse.py            \# Logic for loading JSON and normalizing units  
│   ├── validate.py         \# The 14 specific validation rules and logic  
│   ├── transform.py        \# Matrix math and coordinate system conversion  
│   ├── render.py           \# Matplotlib interaction and drawing commands  
│   ├── geometry.py         \# Geometric primitives (Point, Polygon) helper classes  
│   ├── colors.py           \# Definitions of color palettes for layers  
│   └── errors.py           \# Data classes for structured Error reporting  
└── tests/                  \# Comprehensive test suite  
    ├── \_\_init\_\_.py         \# Test package marker  
    ├── conftest.py         \# Pytest fixtures (e.g., reusable board data)  
    ├── test\_models.py      \# Unit tests for Pydantic models  
    ├── test\_validate.py    \# Unit tests for validation logic  
    └── test\_boards.py      \# Integration tests against the provided JSON files

## **GitHub**

**Repo:** https://github.com/intel-agency/pcb-renderer (Placeholder)

**Branch:** main

## **Deliverables**

1. **Source Code Repository:** A complete Git repository containing the Python source code, configuration files, and full commit history showing the progression of development.  
2. **Working CLI Tool:** A fully functional Python package installable via pip install . or uv sync, providing the pcb-render executable.  
3. **Comprehensive Test Suite:** A suite of unit and integration tests that passes effectively on Continuous Integration (CI) servers across Windows, Linux, and macOS environments.  
4. **Generated Documentation:** A clear, concise README.md for users and an ARCHITECTURE.md for developers, along with inline docstrings for all code.