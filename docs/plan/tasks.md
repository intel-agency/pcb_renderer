# Tasks

List of tasks for the project.

As you complete each task, move it to the "Completed Tasks" section.

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
   (C)ontinue with validation warnings (default)
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

### D4 Add golden master output comparison tests for all supplied example designs **COMPLETED**

Some golden master output comparison tests exist, but not for all example designs.

- Add missing tests.

### **D5** README improvements **COMPLETED**

Updates to improve the README files:

#### ./README.md

1. add quick blurb on how to install uv
2. collapse pwsh command instrucitons into bash/zsh bc they are the same if you use forward slahes in ppwsh (double-check each command for pwsh compatibility)
3. get rid of standalone plugin invocation section

### D6 Docker container platform smoke tests

Create docker container platform smoke tests to validate basic functionality of the application within a docker container environment.

- One docker for each supported platform (linux, windows, macos)
- Use lightweight base images
- Execute same instructions that are provided for the user from the README:
  - install/setup/usage
  - run test suite

### D7 Create schema and grammar for ECAD JSON v1.0.0.0 from syntax in available boards

Use the synatax in the available boards to create a formal schema and grammar definition for ECAD JSON v1.0.0.0

- Create JSON schema file (ecad_schema_v1.0.0.0.json)
- Create grammar definition file (ecad_grammar_v1.0.0.0.txt)

### D8 Add CI pipeline for LLM plugin testing

Add CI pipeline for LLM plugin testing to ensure functionality and reliability of the LLM plugin component.

- Create tests for LLM plugin features
- Integrate tests into CI pipeline
- Test LLM_BACKEND options (template, http/openai, local)
- Test LLM plugin commands (explain, suggest-fixes, analyze)
- Values for http/openai backend should be provided via CI secrets

### D9 Add package and deploy steps to CI pipeline

### D10 Add codeql security scanning to CI pipeline

## Completed Tasks

### D4 Add golden master output comparison tests for all supplied example designs

- Added golden SVG comparisons for all valid boards.
- Added PNG/PDF render smoke tests for all valid boards.
- Added invalid board CLI failure tests (exit code + error output).
