# PCB Renderer Architecture (summary)

Pipeline: parse JSON → normalize units → build Pydantic models → validate (14 rules) → transform coordinates → render via Matplotlib → CLI output and optional JSON export.

- **parse.py**: loads JSON, normalizes MICRON→mm, parses coordinates, builds models or structured errors.
- **validate.py**: deterministic error collection for boundary, nets/layers, geometry, stackup, pins.
- **transform.py**: ECAD (Y-up) to SVG (Y-down), component translation/rotation/mirroring.
- **render.py**: deterministic z-order (boundary, pours, traces, vias, components, refdes, keepouts) with layer colors and haloed text.
- **cli.py**: strict/permissive modes, verbose/quiet, format auto-detect, export-json.
- **tests/**: unit tests per module plus integration over provided boards.
