---
id: 03-core-workflows
status: pending
depends_on: [02-tool-boundary]
touches:
  - server.py
  - mcp_tools/**
  - tests/**
  - requirements.txt
  - Dockerfile
  - scripts/test_docker.sh
  - plans/sharpen-mcp/steps/03-core-workflows.md
lane: none
requirements: [R3]
gate: bash scripts/test_docker.sh && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# Deliver the core workflows

Implement every Core row of the [catalog](../catalog.md) with the schema and defaults documented in step 01. Preserve output semantics from supported existing workflows or record a migration mapping where the new contract is deliberately different.

Use field observations with canonical name, native field and group, backend, original value type, and status. Keep blocked/unknown formats distinct from supported files whose field is absent or blank. If any authoritative source contains non-empty text after trim, it counts as present, with reported conflicts for inconsistent values. Do not infer copyright ownership or licensing. Scoped typed writes use explicit destination, preview and expected state, atomic temp copies, and re-read verification. Preserve original content and untouched tags. Never advertise PDF metadata stripping as irreversible sanitization. Avoid exposing whole document bodies, raw metadata blobs, location data or file content in ordinary results. Keep document semantics via Pandoc and native/container metadata via ExifTool or Mutagen according to support.

Each workflow needs a successful real backend case and at least one applicable failure or unsupported case. Use MCP stdio to test representative calls and validate generated file contents or measured properties. Cover the explicitly named headline scenario end to end.

## Resume notes

Pending.
