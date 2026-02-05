# ECAD JSON schema & grammar

This directory contains the formal ECAD JSON schema and grammar for version **1.0.0** derived from the syntax observed in `boards/*.json`.

## Files

- `ecad_schema_v1.0.0.0.json` — **Permissive** JSON Schema (Draft 2020-12). Allows additional properties to match the project’s permissive parsing contract.
- `ecad_schema_v1.0.0.0.strict.json` — **Strict** JSON Schema. Enforces the modeled fields and disallows unknown top-level properties.
- `ecad_grammar_v1.0.0.0.txt` — **Permissive** EBNF grammar (allows extension fields).
- `ecad_grammar_v1.0.0.0.strict.txt` — **Strict** EBNF grammar (no extension fields on modeled objects).

## Choosing a variant

- Use **permissive** variants for real-world ingestion and tooling that must tolerate extra fields.
- Use **strict** variants for contract validation, CI checks, or schema conformance auditing.

## Examples

Generated example boards live in `boards/generated/` and progress from minimal → intermediate → complex to demonstrate schema/grammar coverage.
