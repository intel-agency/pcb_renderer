import json
import os
from pathlib import Path

from typer.testing import CliRunner

from llm_plugin.cli import app


runner = CliRunner()


def _write_sample(tmp_path: Path) -> Path:
    data = {
        "parse_result": {"stats": {"num_components": 1}, "board": {"components": {}}, "success": True},
        "validation_result": {
            "valid": False,
            "errors": [
                {
                    "code": "NONEXISTENT_NET",
                    "severity": "ERROR",
                    "message": "Trace t1 references unknown net",
                    "json_path": "$.traces.t1.net_name",
                    "context": {"trace_id": "t1"},
                }
            ],
            "warnings": [],
            "error_count": 1,
            "warning_count": 0,
            "checks_run": [],
        },
        "render_result": {"success": False, "output_file": "out.svg", "format": "svg"},
        "schema_version": "1.0",
        "input_file": "board.json",
    }
    path = tmp_path / "sample.json"
    path.write_text(json.dumps(data))
    return path


def _write_valid_sample(tmp_path: Path) -> Path:
    data = {
        "parse_result": {"stats": {"num_components": 1}, "board": {"components": {}}, "success": True},
        "validation_result": {
            "valid": True,
            "errors": [],
            "warnings": [],
            "error_count": 0,
            "warning_count": 0,
            "checks_run": [],
        },
        "render_result": {"success": True, "output_file": "out.svg", "format": "svg"},
        "schema_version": "1.0",
        "input_file": "board.json",
    }
    path = tmp_path / "sample_valid.json"
    path.write_text(json.dumps(data))
    return path


def test_explain_template_backend(tmp_path):
    sample = _write_sample(tmp_path)
    os.environ["LLM_BACKEND"] = "template"
    result = runner.invoke(app, ["explain", str(sample)])
    assert result.exit_code == 0
    assert "LLM TEMPLATE" in result.stdout


def test_explain_no_errors(tmp_path):
    sample = _write_valid_sample(tmp_path)
    os.environ["LLM_BACKEND"] = "template"
    result = runner.invoke(app, ["explain", str(sample)])
    assert result.exit_code == 0
    assert "No issues found while parsing and validating. This board is valid." in result.stdout


def test_analyze_template_backend(tmp_path):
    sample = _write_sample(tmp_path)
    os.environ["LLM_BACKEND"] = "template"
    result = runner.invoke(app, ["analyze", str(sample)])
    assert result.exit_code == 0
    assert "LLM TEMPLATE" in result.stdout
