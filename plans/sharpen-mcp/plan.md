---
gist: "Read me when: you want the bounded metadata_mcp tool catalog, implementation steps, or Docker acceptance gates."
---

# Bounded tool catalog for metadata_mcp

Treat the rights audit and the format/field matrix as release gates. Users rely on the difference between missing metadata and an unsupported format.

The [catalog](./catalog.md) groups user workflows into two implementation steps. Each uses the official backend's supported operations through a typed MCP interface. Research starts with the primary references in the catalog and continues with the tool version installed in the test image. Retain examples, exact checks and tradeoffs in the repository.

See the [acceptance requirements](./spec.md) for the gate coverage.

## Shared contract

Use the host and Docker entry points already documented for this repository. Keep all fixtures synthetic, small, and local. Run Docker tests without credentials or runtime network. No sibling repository may be a build or fixture dependency.

Validate all tool inputs before native dispatch. Accept only local paths beneath configured input/output roots. Resolve symlinks and reject escapes, URI schemes, native filename option syntax, and any argument syntax that can invoke unrelated native features. Use fixed argument arrays or direct library calls, never a shell. Reject unknown fields. Bound per-file and batch work, output volume, subprocess time, and concurrency. Keep deterministic input ordering and return per-file outcomes for partial batch failures. Reject collisions by default. Stage outputs and publish only on success. Tests must confirm invalid inputs never reach the backend. Use stable error codes for unsupported capabilities, invalid inputs, conflicts, and native failures.

Use version-controlled schemas and small Docker fixtures to verify tool discovery and protocol calls. Compare decoded media properties and measured results with stated tolerances. Document byte reproducibility only where the pinned backend demonstrably provides it. Decide and record defaults in the backend-supported catalog before implementation.

## Steps

| Step | Goal | Depends on |
| --- | --- | --- |
| [01-backend-evidence](./steps/01-backend-evidence.md) | Confirm capabilities and choose explicit defaults. | None |
| [02-tool-boundary](./steps/02-tool-boundary.md) | Constrain the MCP boundary and protect it with tests. | 01-backend-evidence |
| [03-core-workflows](./steps/03-core-workflows.md) | Deliver the core workflows. | 02-tool-boundary |
| [04-expanded-workflows](./steps/04-expanded-workflows.md) | Deliver the expanded workflows. | 03-core-workflows |
| [05-docs-and-final-gate](./steps/05-docs-and-final-gate.md) | Publish the guide and verify the integrated result. | 04-expanded-workflows |

One Ralph step runs at a time in this repo because the steps share the public schema and native backend. The other MCP repos can run independently. Use one branch and worktree per step, as the runner provides. Resume using the same repo path, plan name, and external work root. Keep checks and evidence in Git. The root launcher and other MCP servers are independent inputs.
