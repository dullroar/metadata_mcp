"""Verify native metadata readers through the MCP stdio entry point."""

import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def read_tool(session, name, path):
    result = await session.call_tool(name, {"path": str(path)})
    if result.isError:
        raise AssertionError(f"{name} failed: {result.content}")
    if result.structuredContent is not None:
        return result.structuredContent
    if len(result.content) == 1 and result.content[0].type == "text":
        return json.loads(result.content[0].text)
    raise AssertionError(f"{name} did not return metadata: {result.content}")


async def main():
    server = Path(__file__).resolve().parents[1] / "server.py"
    params = StdioServerParameters(command=sys.executable, args=[str(server)])

    with TemporaryDirectory(prefix="metadata-mcp-smoke-") as tmp:
        markdown = Path(tmp) / "example.md"
        markdown.write_text("---\ntitle: Pandoc fixture\n---\n\n# Example\n", encoding="utf-8")
        html = Path(tmp) / "example.html"
        html.write_text("<!doctype html><html><head><title>ExifTool fixture</title></head></html>\n", encoding="utf-8")

        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=30)) as session:
                await session.initialize()
                document = await read_tool(session, "read_document_attributes", markdown)
                embedded = await read_tool(session, "read_metadata", html)

        if document.get("status") != "ok" or document["attributes"].get("title") != "Pandoc fixture":
            raise AssertionError(f"Pandoc title check failed: {document}")

        # read_metadata returns ExifTool's grouped text lines as keys.
        for line in embedded:
            label, _, value = line.partition(":")
            if label.split() == ["[HTML]", "Title"] and value.strip() == "ExifTool fixture":
                print("MCP stdio smoke passed: Pandoc and ExifTool titles")
                return
        raise AssertionError(f"ExifTool title check failed: {embedded}")


if __name__ == "__main__":
    asyncio.run(main())
