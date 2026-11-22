---
id: 04-expanded-workflows
status: pending
depends_on: [03-core-workflows]
touches:
  - server.py
  - mcp_tools/**
  - tests/**
  - requirements.txt
  - Dockerfile
  - scripts/test_docker.sh
  - docs/backend-notes.md
  - plans/sharpen-mcp/steps/04-expanded-workflows.md
lane: none
requirements: [R4]
gate: bash scripts/test_docker.sh && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# Deliver the expanded workflows

Implement the Expanded rows of the [catalog](../catalog.md) as distinct bounded workflows over shared server helpers. Group tests by operation family. Verify output limits, deterministic ordering, and repeat calls. Retain checks and supported behavior from earlier steps.

If a pinned backend lacks a capability, record the actual failing probe and safe alternatives. Block or obtain a documented disposition before claiming the row complete. Never expose a raw backend argument as an escape hatch. Keep documented backend capabilities true of the shipped Docker image.

## Resume notes

Pending.
