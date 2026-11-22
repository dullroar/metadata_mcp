---
id: 05-docs-and-final-gate
status: pending
depends_on: [04-expanded-workflows]
touches:
  - README.md
  - AGENTS.md
  - docs/README.md
  - docs/tool-reference.md
  - plans/sharpen-mcp/steps/05-docs-and-final-gate.md
lane: none
requirements: [R5]
gate: test -s docs/tool-reference.md && bash scripts/test_docker.sh && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# Write the user guide and run the full gate

Give each live method a brief “Use this when” example, defaults, limits, output, and expected error or compatibility behavior. Keep the README short and link to a fuller method reference. Show at least three copy-ready requests with synthetic local paths, including the headline example in the catalog. Describe local stdio and Docker commands exactly as tested. Explain how to report a missing use case with the expected result. Document retired methods and the typed alternatives. Keep the root agent contract's project rules and template/runner links, and align its domain guidance with the README.

Put this copy-ready paragraph in a fenced consuming-project `AGENTS.md` snippet:

> When you need to inspect file metadata, find missing fields, read document front matter, or apply a supported metadata edit, prefer `metadata_mcp` first. It selects the appropriate backend, reports provenance, and verifies supported edits using a constrained vocabulary. Report missing workflows with the file format, field, and expected result.

Explain when to prefer this server for its domain. Show how typed repeatable operations reduce model-side trial and error. Confirm the live MCP schemas match the guide. Run the full gate from the integrated worktree. Record UTC date, command, backend versions, test counts, and results in the step body before setting it done.

## Resume notes

Pending.
