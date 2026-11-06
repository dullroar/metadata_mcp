---
gist: "Read when: writing or debugging a test that verifies FastMCP tool registration."
---

# FastMCP registration checks

- 2026-09-20 - Registration checks must call `await mcp.list_tools()`; `mcp.get_tools()` raises `AttributeError`.
