# Acceptance requirements

## R1 Establish backend evidence

Confirm the installed backend, document the upstream sources and probes, and record supported defaults, limits and unsupported cases for the catalog.

## R2 Enforce the MCP contract

Use typed inputs with bounded work and a fixed backend dispatch. Test discovery and a real stdio call in Docker. Remove or reject arbitrary native options and unknown fields.

## R3 Deliver core workflows

Implement and verify the core catalog, including the named headline scenario. Check both output properties and failure behavior.

## R4 Deliver expanded workflows

Implement and verify the expanded catalog. Record a confirmed blocker for approval if a required backend feature is missing from the pinned image.

## R5 Publish the usage guide and integrated evidence

Ship the per-tool examples, migration notes, consuming-repo agent snippet, and exact Docker and stdio instructions. Record the successful integrated Docker gate.
