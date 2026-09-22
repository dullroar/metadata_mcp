# MEMORY.md

Non-obvious findings about this codebase and its operating environment, discovered during work but not designed for anywhere else — not in README.md (what it is and how to use it), DESIGN.md (architectural decisions), or agent-instruction files (rules). This is background context for whichever LLM works in this repository next, so it does not have to rediscover these findings the hard way.

If you (an LLM) make a finding like the ones below — a gotcha, an environment quirk, or a non-obvious reason one component reads or uses another — add it here rather than only mentioning it in chat. Keep entries factual and dated; note when something might have been fixed since.

## Findings

- 2026-09-20 — FastMCP registration checks must call await mcp.list_tools(); mcp.get_tools() raises AttributeError.
- 2026-09-20 — This checkout requires .venv/bin/python; the system python executable is unavailable. Recheck if the environment is rebuilt.
- 2026-09-20 — Pandoc cannot read PDF and did not expose DOCX subject/custom properties in local testing; route PDF, legacy Word/OLE, OOXML, ODF, and EPUB metadata reads through ExifTool-backed read_metadata instead.
