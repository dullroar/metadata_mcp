---
id: 02-tool-boundary
status: pending
depends_on: [01-backend-evidence]
touches:
  - server.py
  - mcp_tools/**
  - requirements.txt
  - Dockerfile
  - .dockerignore
  - scripts/test_docker.sh
  - scripts/AGENTS.md
  - .github/workflows/context.yml
  - tests/**
  - plans/sharpen-mcp/steps/02-tool-boundary.md
lane: none
requirements: [R2]
gate: test -s tests/test_tool_contract.py && bash scripts/test_docker.sh && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# Enforce the FastMCP tool boundary

Remove `exiftool_passthrough` and release the typed replacements in the same change as any removal. Replace raw tag dictionaries, arbitrary write selectors, implicit recursion and unrestricted reader overrides with typed canonical fields, bounded selectors and known reader variants. Preserve `inspect_file`, `read_metadata`, `read_document_attributes`, and useful named setters where the current behavior can be constrained. Keep version/capabilities concise. Treat generic `help` as README/catalog or a structured summary.

Keep the supported workflows reachable through the existing entry point. Declare precise tool schemas and deterministic error mapping. Test exact tool discovery, verify removal of passthrough names, and reject unknown fields and unsupported enum values before any native invocation. Update the existing smoke contract to reflect intentional changes.

Use the host and Docker entry points already documented for this repository. Keep all fixtures synthetic, small, and local. Run Docker tests without credentials or runtime network. No sibling repository may be a build or fixture dependency.

Validate all tool inputs before native dispatch. Accept only local paths beneath configured input/output roots. Resolve symlinks and reject escapes, URI schemes, native filename option syntax, and any argument syntax that can invoke unrelated native features. Use fixed argument arrays or direct library calls, never a shell. Reject unknown fields. Bound per-file and batch work, output volume, subprocess time, and concurrency. Keep deterministic input ordering and return per-file outcomes for partial batch failures. Reject collisions by default. Stage outputs and publish only on success. Tests must confirm invalid inputs never reach the backend. Use stable error codes for unsupported capabilities, invalid inputs, conflicts, and native failures.

Use version-controlled schemas and small Docker fixtures to verify tool discovery and protocol calls. Compare decoded media properties and measured results with stated tolerances. Document byte reproducibility only where the pinned backend demonstrably provides it. Decide and record defaults in the backend-supported catalog before implementation.

Put contract tests in `tests/test_tool_contract.py` and ensure the Docker test entry point actually runs them.

## Resume notes

Pending.
