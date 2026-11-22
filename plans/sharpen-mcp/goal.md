# Sharpen metadata_mcp

## Ralph loop prompt

> Read the root agent contract, this goal, the plan, and the assigned step. Work only in the step worktree and on files the step lists in `touches`. Run the step gate unchanged and commit the result. If work stops, record resume notes or the exact blocker in the step file. Keep local paths, credentials, and raw runtime output outside tracked files.

## Goal

Make `metadata_mcp` the first choice for file inspection, embedded metadata and document front matter. Deliver a generous catalog of bounded tools with predictable behavior and useful error reporting. Use a constrained domain vocabulary so clients can select tested workflows without reconstructing backend commands.

## Done when

- Docker exercises real stdio tool discovery and representative native outputs for the [catalog](./catalog.md). Required core and expanded workflows are implemented, or a concrete backend blocker is recorded for review.
- The catalog has typed inputs and reject-path tests. No tool exposes native passthrough, unbounded parameters, or unsupported variants.
- The README explains when to prefer the server, gives real examples, and includes a copy-ready rule for consuming repositories.
- The published plan can resume from Git and Ralph's existing external state without any sibling checkout or shared writable resources.
