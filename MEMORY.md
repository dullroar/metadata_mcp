# Project Memory

> Version-controlled, cross-LLM continuity notes. Keep this file compact, factual, and useful to a future contributor.

## Current context

- metadata_mcp is a FastMCP server for inspecting and editing file metadata.
- Use inspect_file first for a compact, read-only filesystem, content-type, and Git-context view. Escalate to format-specific tools only when needed.

## Durable implementation facts

- inspect_file keeps filesystem, content-type, and Git failures isolated; Git blame is returned only when both inclusive line bounds are supplied.
- Use read_document_attributes for semantic attributes in text-centric document formats. Its default output is compact; set include_full_metadata=True only when nested raw Pandoc metadata is needed.
- Use read_metadata for embedded or container metadata, particularly PDF, OOXML/Office, ODF, EPUB, and legacy Word/OLE files. ExifTool remains the appropriate backend for those formats.
- The project interpreter is .venv/bin/python; system python is unavailable in this checkout.
- FastMCP tool registration is verified with await mcp.list_tools().

## Working conventions

- Keep sample-CLAUDE.md and sample-AGENTS.md byte-identical. When copied into another project, remove the sample- prefix.
- Prefer bounded, explicit output. Do not return full nested metadata unless the caller opts in.
- Run the full test suite after dependencies are available; skipped live-integration tests are not sufficient validation.

## Evidence

- 2026-09-20: Implemented and validated compact inspect_file routing and Pandoc-based document-attribute extraction in this checkout.
- 2026-09-20: Repository documentation and tests confirm the compact-first tool-routing contract.

## Open questions

- None recorded.

