# LLM Plugin Architecture

## Overview

The LLM plugin is **fully decoupled** from the core PCB renderer. The core app provides structured outputs that the plugin consumes to generate natural-language explanations, debug assistance, and suggestions.

**Key Principle:** No runtime dependency. The LLM plugin is an optional add-on that works with the core renderer's outputs.

## Core App Responsibilities

The core PCB renderer produces:

1. **Normalized board data** (parsed, units in mm)
2. **Structured validation errors** (code, message, location)
3. **Rendering success/failure** (exit code, output path)

## LLM Plugin Responsibilities

The plugin consumes core outputs and generates:

1. **Natural-language error explanations**
2. **Debugging suggestions** ("Check if net X is declared")
3. **Design insights** ("Board has unusual via density")

## Interface Contract

### Core App Output Format

The core app can export structured JSON for LLM consumption:

```json
{
  "input_file": "boards/board_kappa.json",
  "parse_result": {
    "success": true/false,
    "board": {
      "metadata": {...},
      "boundary": {...},
      "components": {...},
      "traces": {...},
      "vias": {...},
      "stats": {
        "num_components": 5,
        "num_traces": 12,
        "num_vias": 8,
        "board_area_mm2": 1250.5
      }
    }
  },
  "validation_result": {
    "valid": true/false,
    "errors": [
      {
        "code": "DANGLING_TRACE",
        "severity": "ERROR",
        "message": "Trace trace_001 references nonexistent net VCC",
        "json_path": "$.traces.trace_001.net_name",
        "context": {
          "trace_id": "trace_001",
          "referenced_net": "VCC",
          "available_nets": ["GND", "VDD"]
        }
      }
    ],
    "warnings": []
  },
  "render_result": {
    "success": true/false,
    "output_file": "out/board.svg",
    "format": "svg"
  }
}
```

### Export Command

Add optional `--export-json` flag to CLI:

```bash
python -m pcb_renderer board.json -o out.svg --export-json out.json
```

This creates `out.json` with full structured data for LLM consumption.

## LLM Plugin Architecture

### Plugin Entry Point

```python
# llm_plugin.py

def explain_errors(validation_result: dict) -> str:
    """Generate natural-language explanation of errors."""
    errors = validation_result['errors']
    
    if not errors:
        return "Board is valid with no errors."
    
    # Use LLM to generate explanation
    prompt = f"""
    Explain these PCB validation errors in plain English:
    
    {json.dumps(errors, indent=2)}
    
    For each error:
    - What it means
    - Why it's a problem
    - How to fix it
    """
    
    return call_llm(prompt)


def suggest_fixes(board: dict, errors: list) -> str:
    """Generate specific fix suggestions."""
    prompt = f"""
    Given this PCB board structure and validation errors,
    suggest specific fixes:
    
    Board summary:
    - Components: {board['stats']['num_components']}
    - Traces: {board['stats']['num_traces']}
    - Nets: {list(board.get('nets', {}).keys())}
    
    Errors:
    {json.dumps(errors, indent=2)}
    
    Provide concrete JSON edits or design changes.
    """
    
    return call_llm(prompt)


def analyze_design(board: dict) -> str:
    """Provide design insights."""
    prompt = f"""
    Analyze this PCB design and provide insights:
    
    {json.dumps(board['stats'], indent=2)}
    
    Comments on:
    - Component density
    - Routing complexity
    - Potential design issues
    - Manufacturing considerations
    """
    
    return call_llm(prompt)
```

### Plugin CLI

Separate command for LLM-assisted debugging:

```bash
# After rendering
python -m pcb_renderer board.json -o out.svg --export-json board_data.json

# Run LLM plugin
python -m llm_plugin explain board_data.json
python -m llm_plugin suggest-fixes board_data.json
python -m llm_plugin analyze board_data.json
```

## Integration Points

### Option 1: Post-Processing (Recommended)

1. Core renderer runs normally
2. Exports JSON with `--export-json`
3. LLM plugin reads JSON
4. Plugin generates report

**Advantages:**
- Complete decoupling
- Can run plugin on any exported JSON
- No runtime dependency

### Option 2: CLI Integration

Add optional LLM flags to core CLI:

```bash
python -m pcb_renderer board.json -o out.svg --llm-explain
```

Core CLI detects flag, exports JSON, calls plugin, prints output.

**Advantages:**
- Single command
- Better UX

**Disadvantages:**
- Couples core to plugin
- Requires plugin installation

## Data Contract Details

### Error Context

Each validation error includes `context` dict with relevant data:

```python
{
  "code": "DANGLING_TRACE",
  "message": "...",
  "json_path": "$.traces.t1.net_name",
  "context": {
    "trace_id": "t1",
    "referenced_net": "VCC",
    "available_nets": ["GND", "VDD"],
    "layer": "TOP"
  }
}
```

Context varies by error type but always provides actionable data.

### Board Stats

Computed during validation:

```python
"stats": {
  "num_components": 12,
  "num_traces": 45,
  "num_vias": 23,
  "num_nets": 8,
  "board_area_mm2": 1250.5,
  "board_dimensions_mm": [50.0, 25.0],
  "layer_count": 2,
  "component_density": 0.0096,  # components per mm²
  "trace_length_total_mm": 234.5
}
```

### Validation Summary

```python
"validation_result": {
  "valid": false,
  "error_count": 2,
  "warning_count": 1,
  "errors": [...],
  "warnings": [...],
  "checks_run": [
    "boundary", "coordinates", "rotation", 
    "references", "geometry", ...
  ]
}
```

## LLM Prompting Strategy

### Error Explanation Template

```
You are a PCB design expert. Explain this validation error:

Error Code: {code}
Message: {message}
Location: {json_path}
Context: {context}

Provide:
1. What this error means in plain English
2. Why it's a problem (electrical, manufacturing, or design)
3. How to fix it (specific JSON changes or design modifications)

Be concise but thorough.
```

### Design Analysis Template

```
You are a PCB design expert. Analyze this board:

Stats:
{stats}

Nets:
{nets}

Components:
{component_list}

Provide insights on:
- Design quality (good practices vs issues)
- Manufacturing concerns
- Potential electrical problems
- Suggestions for improvement

Be objective and specific.
```

## Example LLM Plugin Usage

### Scenario: Debugging Invalid Board

```bash
# Try to render
$ python -m pcb_renderer boards/board_kappa.json -o out.svg --export-json debug.json
ERROR: Validation failed with 2 errors
  [ERROR] MALFORMED_TRACE: Trace trace_single_point has only 1 point at $.traces.trace_single_point
  [ERROR] NONEXISTENT_NET: Via via_bad_net references unknown net at $.vias.via_bad_net

# Use LLM plugin for help
$ python -m llm_plugin explain debug.json

Error 1: Malformed Trace
━━━━━━━━━━━━━━━━━━━━━━━
A trace must have at least 2 points to form a path. Trace 'trace_single_point' 
only has 1 coordinate, which cannot form a line.

Why this matters:
- Traces represent electrical connections
- A single point has no length and cannot connect components

How to fix:
- Add at least one more coordinate to the trace
- Or remove the trace if it's unintentional

Example fix in JSON:
  "trace_single_point": {
    "path": {
      "coordinates": [[15000, 15000], [20000, 15000]]  // Added endpoint
    }
  }

Error 2: Nonexistent Net
━━━━━━━━━━━━━━━━━━━━━━
Via 'via_bad_net' references net 'NONEXISTENT_NET_XYZ', but this net is not 
declared in the board's nets list.

Available nets: GND, VCC, CLK

How to fix:
Option 1: Change via to reference an existing net
  "via_bad_net": {
    "net_name": "GND"  // Use declared net
  }

Option 2: Add the net to the nets list
  "nets": [
    {"name": "GND", "class": "POWER"},
    {"name": "VCC", "class": "POWER"},
    {"name": "NONEXISTENT_NET_XYZ", "class": "SIGNAL"}  // Declare it
  ]
```

## Implementation Timeline

The LLM plugin is **lower priority** than core renderer. Implement after core is complete and tested.

**Estimated time: 4-6 hours**

1. Export JSON from core (1 hour)
2. LLM prompt templates (1 hour)
3. Plugin CLI (1 hour)
4. Error explanation (1 hour)
5. Design analysis (1 hour)
6. Testing and refinement (1 hour)

## Testing Strategy

### Unit Tests

```python
def test_error_explanation():
    """LLM generates explanation for validation error."""
    error = {
        "code": "DANGLING_TRACE",
        "message": "Trace t1 references unknown net VCC",
        "context": {
            "trace_id": "t1",
            "referenced_net": "VCC",
            "available_nets": ["GND"]
        }
    }
    
    explanation = explain_error(error)
    
    assert "VCC" in explanation
    assert "not declared" in explanation.lower()
    assert "fix" in explanation.lower()
```

### Integration Tests

```python
def test_full_workflow():
    """End-to-end: export JSON, run plugin."""
    # Export from core
    result = run_command([
        'python', '-m', 'pcb_renderer',
        'boards/board_kappa.json',
        '-o', 'out.svg',
        '--export-json', 'data.json'
    ])
    
    assert result.returncode == 1  # Invalid board
    assert Path('data.json').exists()
    
    # Run plugin
    explanation = run_command([
        'python', '-m', 'llm_plugin',
        'explain', 'data.json'
    ])
    
    assert "trace" in explanation.stdout.lower()
    assert "fix" in explanation.stdout.lower()
```

## Future Enhancements

### Interactive Mode

```bash
python -m llm_plugin interactive board_data.json

> What's wrong with this board?
[LLM explains errors]

> How do I fix the dangling trace?
[LLM provides specific fix]

> Show me the trace path
[Plugin visualizes trace in ASCII or links to rendered output]
```

### Automated Fixes

```bash
python -m llm_plugin auto-fix board_data.json -o fixed_board.json
```

LLM suggests fixes, plugin applies them, outputs corrected JSON.

**Caution:** Requires careful validation to avoid breaking valid boards.

## Conclusion

The LLM plugin provides a natural-language interface to the core renderer's structured outputs. By keeping them decoupled, we maintain simplicity in the core while enabling powerful debugging assistance through LLMs.

The interface is designed to be stable and extensible, allowing the plugin to evolve independently of the core renderer.
