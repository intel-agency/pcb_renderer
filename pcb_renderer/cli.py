"""Command-line interface for pcb-renderer.

This module provides the main entry point for the PCB Renderer CLI tool.
It orchestrates the complete pipeline: parse → validate → render.

Challenge Requirements:
----------------------
From the Quilter Backend Engineer Code Challenge:

1. **Input/Output**: Accept an input JSON file and output image path
2. **Parse**: Load and parse the ECAD JSON format
3. **Validate**: Detect 14 types of invalid board errors
4. **Render**: Generate SVG/PNG/PDF output
5. **Error Reporting**: Report validation errors with meaningful messages

CLI Usage:
----------
::

    # Basic render
    pcb-render boards/board.json -o out/board.svg

    # With format specification
    pcb-render boards/board.json -o out/board.png --format png

    # Permissive mode (render despite validation errors)
    pcb-render boards/board.json -o out/board.svg --permissive

    # Export structured JSON (for debugging or LLM plugin)
    pcb-render boards/board.json -o out/board.svg --export-json out/board.json

    # Open output after rendering
    pcb-render boards/board.json -o out/board.svg --open

    # With LLM plugin (requires --extra llm)
    pcb-render boards/board.json -o out/board.svg --llm-explain

Exit Codes:
-----------
- 0: Success (board rendered without errors)
- 1: Failure (parse error, validation error, or render error)

Export JSON Schema:
------------------
When --export-json is used, outputs structured payload consumed by:
- LLM plugin for natural-language error explanations
- Tests for verifying pipeline behavior
- External tools for board analysis

::

    {
        "schema_version": "1.0",
        "input_file": "path/to/board.json",
        "parse_result": {...},
        "validation_result": {...},
        "render_result": {...}
    }

"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .parse import parse_board_data, parse_board_json, read_board_file
from .render import render_board
from .stats import compute_stats
from .validate import CHECKS_RUN, validate_board


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for the CLI.

    Returns:
        Configured ArgumentParser with all CLI options.

    CLI Arguments:
        input: Positional or -i/--input for input JSON file
        -o/--output: Required output file path
        --format: Explicit format (svg, png, pdf) or infer from extension
        --verbose: Show progress messages (default: on)
        --quiet: Suppress success output
        --permissive: Render even if validation errors occur
        --export-json: Write structured export payload to file
        --open: Open output with system default application

    Note:
        LLM plugin flags (--llm-explain, etc.) are registered dynamically
        by _maybe_register_plugin() if llm_plugin is installed.
    """
    parser = argparse.ArgumentParser(prog="pcb-render", description="Render PCB boards from ECAD JSON files")
    parser.add_argument("input", nargs="?", type=Path, help="Input JSON board file")
    parser.add_argument("-i", "--input", dest="input_flag", type=Path, help="Input JSON board file (alias)")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output file path")
    parser.add_argument("--format", choices=["svg", "png", "pdf"], help="Output format (defaults from extension)")
    parser.add_argument("--verbose", action="store_true", default=True, help="Show progress messages (default on)")
    parser.add_argument("--quiet", action="store_true", help="Suppress success output")
    parser.add_argument("--permissive", action="store_true", help="Render even if validation errors occur")
    parser.add_argument("--export-json", dest="export_json", type=Path, help="Write normalized board + errors to JSON")
    parser.add_argument("--open", dest="auto_open", action="store_true", help="Open output with system default app")
    return parser


def _print_errors(errors) -> None:
    """Print validation errors to stderr."""
    for err in errors:
        print(str(err), file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the PCB Renderer CLI.

    Orchestrates the complete pipeline:
    1. Parse input file (read_board_file → parse_board_json → parse_board_data)
    2. Validate board semantics (validate_board with 18 checks)
    3. Render output (render_board to SVG/PNG/PDF)
    4. Export JSON if requested (for LLM plugin or debugging)
    5. Invoke LLM plugin if flags are present

    Args:
        argv: Command-line arguments (None for sys.argv)

    Returns:
        Exit code: 0 for success, 1 for any failure

    Challenge Requirements:
        This function implements the complete solution workflow:
        - Parse ECAD JSON input
        - Validate against 14 error types
        - Render to SVG/PNG/PDF
        - Report errors with meaningful messages
    """
    parser = create_parser()
    _maybe_register_plugin(parser)  # Register LLM plugin flags if available
    args = parser.parse_args(argv)

    # Resolve input path (positional or flag)
    input_path = args.input or args.input_flag
    if not input_path:
        parser.error("Input file is required")
    verbose = args.verbose and not args.quiet

    # ========== PHASE 1: PARSE ==========
    if verbose:
        print(f"Loading board file from {input_path}...")

    # Step 1a: Read raw file content
    raw_text, file_errors = read_board_file(Path(input_path))
    parse_errors: List[Any] = list(file_errors)
    board = None

    if not file_errors and raw_text is not None:
        # Step 1b: Parse JSON syntax
        if verbose:
            print("Parsing JSON...")
        data, json_errors = parse_board_json(raw_text)
        parse_errors.extend(json_errors)

        if not json_errors and data is not None:
            # Step 1c: Parse board structure into Pydantic models
            if verbose:
                print("Parsing board data...")
            board, board_errors = parse_board_data(data)
            parse_errors.extend(board_errors)

    all_errors = list(parse_errors)
    parse_success = not parse_errors and board is not None

    # ========== PHASE 2: VALIDATE ==========
    validation_errors: List[Any] = []
    if parse_success:
        if verbose:
            print("Validating board...")
        assert board is not None
        # Run all 18 validation checks from challenge requirements
        validation_errors = validate_board(board)
        all_errors.extend(validation_errors)

    # ========== PHASE 3: RENDER ==========
    render_success = False
    render_format = args.format or args.output.suffix.lstrip(".")

    # Render if parse succeeded and (no validation errors OR permissive mode)
    if parse_success and (not validation_errors or args.permissive):
        if verbose:
            print("Rendering board...")
        try:
            assert board is not None
            render_board(board, args.output, format=args.format)
            render_success = True
        except Exception as exc:  # pragma: no cover
            print(f"ERROR: Rendering failed: {exc}", file=sys.stderr)
    else:
        # Report validation errors if not rendering
        if validation_errors and not args.permissive:
            _print_errors(validation_errors)

    # ========== PHASE 4: EXPORT & LLM ==========
    # Compute board statistics for export payload
    stats = compute_stats(board) if parse_success and board else None

    # Determine export path (explicit or temp for LLM)
    export_path = args.export_json
    llm_modes = _llm_modes(args)
    temp_export: Optional[Path] = None
    if llm_modes and not export_path:
        # Create temp file for LLM plugin if no explicit export path
        temp_export = Path(tempfile.NamedTemporaryFile(delete=False, suffix=".json").name)
        export_path = temp_export

    # Build export payload (consumed by LLM plugin and tests)
    payload = _build_export_payload(
        input_path=Path(input_path),
        board=board if parse_success else None,
        parse_errors=parse_errors,
        validation_errors=validation_errors,
        render_success=render_success,
        output_path=args.output,
        output_format=render_format,
        stats=stats,
    )

    # Write export JSON if requested
    if export_path:
        _write_export(export_path, payload)

    # Invoke LLM plugin for natural-language error explanations
    if llm_modes:
        _invoke_llm_plugin(export_path, llm_modes, verbose)

    # Open output file in system default application
    if args.auto_open and render_success:
        try:
            open_file(args.output)
        except Exception as exc:  # pragma: no cover
            if verbose:
                print(f"Warning: could not open output: {exc}", file=sys.stderr)

    # Clean up temp export file
    if temp_export and temp_export.exists():
        temp_export.unlink(missing_ok=True)

    # ========== DETERMINE EXIT CODE ==========
    if validation_errors and not args.permissive:
        return 1
    if not parse_success:
        _print_errors(parse_errors)
        return 1
    if not render_success:
        return 1

    if not args.quiet:
        print(f"Success: Board rendered to {args.output}")
    return 0


def _write_export(path: Path, payload: Dict[str, Any]) -> None:
    """Write export payload to JSON file.

    Args:
        path: Destination file path
        payload: Export payload dict from _build_export_payload()
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def open_file(path: Path) -> None:
    """Open a file with the OS default application (best-effort, cross-platform).

    Supports:
    - Windows: os.startfile()
    - macOS: open command
    - Linux: xdg-open or gio

    Args:
        path: File to open

    Raises:
        RuntimeError: If no system opener is available (Linux without xdg-open/gio)
    """

    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
        return

    # Linux: try xdg-open or gio
    opener = shutil.which("xdg-open") or shutil.which("gio")
    if opener:
        subprocess.run([opener, str(path)], check=False)
        return
    raise RuntimeError("No system opener available (xdg-open/gio not found)")


def _build_export_payload(
    *,
    input_path: Path,
    board,
    parse_errors,
    validation_errors,
    render_success: bool,
    output_path: Path,
    output_format: str,
    stats: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the structured export payload.

    This is a PUBLIC CONTRACT consumed by:
    - LLM plugin for natural-language error explanations
    - Tests for verifying pipeline behavior
    - External tools for board analysis

    Args:
        input_path: Path to input board JSON
        board: Parsed Board model (None if parse failed)
        parse_errors: List of parse-phase errors
        validation_errors: List of validation-phase errors
        render_success: Whether rendering succeeded
        output_path: Path to rendered output file
        output_format: Output format (svg, png, pdf)
        stats: Board statistics from compute_stats()

    Returns:
        Dict matching the Export JSON Schema (see module docstring)

    Note:
        Changes to this schema should bump schema_version and be coordinated
        with llm_plugin and tests.
    """
    def _error_to_dict(err):
        """Convert ValidationError to JSON-serializable dict."""
        return {
            "code": err.code.value,
            "severity": err.severity.value,
            "message": err.message,
            "json_path": err.json_path,
            "context": err.context,
        }

    parse_success = not parse_errors and board is not None
    validation_success = parse_success and not validation_errors
    checks_run = CHECKS_RUN if parse_success else []

    return {
        "schema_version": "1.0",
        "input_file": str(input_path),
        "parse_result": {
            "success": parse_success,
            "errors": [_error_to_dict(e) for e in parse_errors],
            "board": board.model_dump(mode="json") if parse_success and board else None,
            "stats": stats,
        },
        "validation_result": {
            "valid": validation_success,
            "error_count": len(validation_errors),
            "warning_count": 0,
            "errors": [_error_to_dict(e) for e in validation_errors],
            "warnings": [],
            "checks_run": checks_run,
        },
        "render_result": {
            "success": render_success,
            "output_file": str(output_path),
            "format": output_format,
        },
    }


def _maybe_register_plugin(parser: argparse.ArgumentParser) -> None:
    """Dynamically register LLM plugin CLI flags if available.

    The LLM plugin is optional. If installed, it adds:
    - --llm-explain: Explain validation errors in natural language
    - --llm-suggest-fixes: Suggest fixes for validation errors
    - --llm-analyze: Provide design analysis

    Args:
        parser: ArgumentParser to add flags to
    """
    try:
        import llm_plugin  # type: ignore

        if hasattr(llm_plugin, "register_cli"):
            llm_plugin.register_cli(parser)
    except ImportError:
        return  # Plugin not installed, skip silently


def _llm_modes(args) -> List[str]:
    """Extract LLM modes from parsed arguments.

    Returns:
        List of mode names (e.g., ["explain", "suggest-fixes"])
    """
    modes: List[str] = []
    for flag, name in [
        ("llm_explain", "explain"),
        ("llm_suggest_fixes", "suggest-fixes"),
        ("llm_analyze", "analyze"),
    ]:
        if getattr(args, flag, False):
            modes.append(name)
    return modes


def _invoke_llm_plugin(export_path: Optional[Path], modes: List[str], verbose: bool) -> None:
    """Invoke the LLM plugin with the export payload.

    Args:
        export_path: Path to export JSON file
        modes: List of LLM modes to run (explain, suggest-fixes, analyze)
        verbose: Whether to print status messages
    """
    if not export_path:
        if verbose:
            print("LLM plugin requested but no export available", file=sys.stderr)
        return
    try:
        import llm_plugin  # type: ignore

        if hasattr(llm_plugin, "run_from_core"):
            llm_plugin.run_from_core(export_path, modes)
        else:
            if verbose:
                print("LLM plugin missing run_from_core handler", file=sys.stderr)
    except ModuleNotFoundError:
        if verbose:
            print("LLM plugin not installed; skipping LLM invocation", file=sys.stderr)
    except Exception as exc:  # pragma: no cover
        if verbose:
            import traceback

            print(f"LLM plugin invocation failed: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
