# Tasks

Tasks to implement for the project:

## Unimplemented Tasks

### D1 Docker support  

Add support for docker and docker compose to project.

- include support for the plugin system.


### D2 LLM plugin local model support

add local model with ONNX runtime HW acceleration support to LLM plugin

### D3 ECAD JSON schema v1.0.0 support

Enforce support for v1.0.0 of the ECAD JSON schema in the baord design input files

Implement schema version validation with the following behavior:
Expected Version: "v1.0.0.0"
When a different version is encountered:

Display warning message:

``` sh
   WARNING: Unexpected schema version '{actual_version}' detected.
   Expected version: {expected_version}
   
   How would you like to proceed?
   [1] Continue with validation warnings (default)
   [2] Enable permissive mode (skip all validation warnings)
   [3] Exit
   
   Choice (1-3):
```

Handle user response:

Option 1 (or Enter): Continue parsing normally, but log/output warnings for each validation concern encountered
Option 2: Set a permissiveMode flag to true, suppress all validation warnings, attempt best-effort parsing
Option 3: Exit the program gracefully with message "Parsing cancelled by user."

Implementation requirements:

Only prompt once per execution (on first version mismatch)
Add a constant EXPECTED_SCHEMA_VERSION = "v1.0.0.0" at class level
Include a code comment explaining the rationale: "Provides resilience against schema evolution while maintaining visibility into compatibility issues"

### Add golden master output comparison tests for all supplied example designs

Some golden master output comparison tests exist, but not for all example designs.

- Add missing tests.

## Completed Tasks
