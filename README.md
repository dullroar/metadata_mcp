# exiftool-mcp

**Author:** Jim Lehmer  
**License:** MIT

A simple [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes [ExifTool](https://exiftool.org/) as an MCP tool. Connect it to any MCP-compatible LLM client (Claude Desktop, Claude Code, etc.) and ask the LLM to read/write metadata on image, video, and document files — no ExifTool CLI knowledge required on your part.

When this MCP server is available, agents can ask to:
- Read all EXIF metadata from a file
- Write arbitrary tags to media files
- Set Copyright recursively across a directory
- Set GPS coordinates on a file
- Copy metadata between files
- Strip all metadata
- And more via the passthrough tool

---

## Reasons to Use

1. Token/cost savings

For long metadata operations, the model should not be the execution engine. It should be the coordinator, and ExifTool handles the actual work.

2. Determinism

ExifTool gives repeatable output. The LLM can then answer: "Did the metadata write succeed?" rather than guessing if the operation worked.

3. Local privacy

Metadata operations do not need to be pasted wholesale into a chat — file paths suffice.

4. Better promptable workflow

"Read all tags from this image and tell me the camera model" is much friendlier than remembering `exiftool -a -G`.

5. Agentic pipeline building

Extract → validate → embed → archive becomes modular steps.

---

## Favorite Sample Workflows

Read all metadata from a photo:

    read_metadata(path: "photo.jpg")

Set Copyright on a file:

    set_copyright(path: "photo.jpg", copyright: "© My Company 2026")

Strip all metadata before upload:

    strip_metadata(path: "photo.jpg")

Copy metadata from source to destination:

    copy_metadata(source: "original.jpg", dest: "backup.jpg")

Set GPS coordinates for geotagging:

    set_gps(path: "photo.jpg", latitude: 40.7128, longitude: -74.0060, latitudeRef: "N", longitudeRef: "W")

Read all tags with verbose output:

    exiftool_passthrough(arguments: ["-a", "-G", "-v", "photo.jpg"])

---

## Tools

### `read_metadata`

Read all metadata tags from a file.

| Parameter | Type | Default | Description |
|---|---|---|-|
| `path` | `str` | required | File path to read metadata from |

### `write_metadata`

Write arbitrary tag=value pairs to a file.

| Parameter | Type | Default | Description |
|---|---|---|-|
| `path` | `str` | required | File path |
| `tags` | `dict` | required | tag=value pairs, e.g. `{"Title": "My Photo", "Artist": "Me"}` |

### `set_copyright`

Set Copyright tag across a file or directory (recursive flag available).

| Parameter | Type | Default | Description |
|---|---|---|-|
| `path` | `str` | required | File or directory path |
| `copyright` | `str` | required | Copyright text to set |
| `recursive` | `bool` | False | Apply to all files in directory recursively |

### `set_author`

Set Author tag on a file.

| Parameter | Type | Default | Description |
|---|---|---|-|
| `path` | `str` | required | File path |
| `author` | `str` | required | Author name to set |

### `set_description`

Set Description tag on a file.

| Parameter | Type | Default | Description |
|---|---|---|-|
| `path` | `str` | required | File path |
| `description` | `str` | required | Description text to set |

### `set_gps`

Set GPS coordinates (lat/lon) on a file.

| Parameter | Type | Default | Description |
|---|---|---|-|
| `path` | `str` | required | File path |
| `latitude` | `float` | required | GPS latitude |
| `longitude` | `float` | required | GPS longitude |
| `latitudeRef` | `str` | "N" | "N" or "S" |
| `longitudeRef` | `str` | "E" | "E" or "W" |
| `altitude` | `float` | optional | GPS altitude (optional) |
| `altitudeRef` | `str` | "above" | "above" or "below" (optional) |

### `copy_metadata`

Copy all metadata from source file to destination file.

| Parameter | Type | Default | Description |
|---|---|---|-|
| `source` | `str` | required | Source file path |
| `dest` | `str` | required | Destination file path |
| `only` | `list[str]` | optional | Copy only these tag names (if set) |

### `strip_metadata`

Strip all metadata from a file or directory (recursive).

| Parameter | Type | Default | Description |
|---|---|---|-|
| `path` | `str` | required | File or directory path |
| `recursive` | `bool` | False | Apply to all files in directory recursively |

### `exiftool_passthrough`

Passthrough tool for arbitrary ExifTool arguments.

| Parameter | Type | Default | Description |
|---|---|---|-|
| `arguments` | `list[str]` | required | Raw ExifTool CLI arguments |

---

## Requirements

- Python 3.10+
- [ExifTool](https://exiftool.org/) installed and on your `PATH`
- Python packages: `mcp[cli]`

---

## Installation

```bash
git clone https://github.com/dullroar/exiftool_mcp.git
cd exiftool_mcp

# Recommended: use a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

---

## MCP client configuration

### Claude Desktop

Add to your `claude_desktop_config.json` (usually at `%APPDATA%\Claude\claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "exiftool": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```

Using a virtual environment (recommended — avoids dependency conflicts):

```json
{
  "mcpServers": {
    "exiftool": {
      "command": "C:\\path\\to\\exiftool_mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\exiftool_mcp\\server.py"]
    }
  }
}
```

Restart Claude Desktop after editing the config. You should see a hammer icon in the chat input area indicating MCP tools are available.

### Claude Code

Register the server with the Claude Code CLI:

```bash
claude mcp add exiftool -- python C:\path\to\exiftool_mcp\server.py
```

Or with a virtual environment:

```bash
claude mcp add exiftool -- C:\path\to\exiftool_mcp\.venv\Scripts\python.exe C:\path\to\exiftool_mcp\server.py
```

Verify it registered:

```bash
claude mcp list
```

To remove it later:

```bash
claude mcp remove exiftool
```

### HTTP/SSE mode (for other MCP clients)

By default the server uses stdio. Pass `--transport sse` to start an HTTP/SSE server instead:

```bash
python server.py --transport sse
# Listening on http://127.0.0.1:8000/sse
```

Optional flags:

| Flag | Default | Description |
| --- | --- | --- |
| `--transport` | `stdio` | `stdio` or `sse` |
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Bind port |

You can also set `FASTMCP_HOST` and `FASTMCP_PORT` environment variables instead of flags.

Any MCP client that speaks HTTP/SSE (VS Code extensions, the MCP Inspector, or custom agents) can connect to `http://127.0.0.1:8000/sse`.

**Tunneling for a one-off remote demo** (e.g., ChatGPT connector):

```bash
python server.py --transport sse &
ngrok http 8000
# Paste the ngrok HTTPS URL into the ChatGPT custom connector dialog
```

> Note: for production exposure add an auth token. For local experiments, localhost is fine.

---

## Example prompts

Once connected to a Claude client, you can ask naturally:

- *"Read all the metadata from this photo and tell me what camera was used."*
- *"Set the Copyright tag on this image to '© My Company 2026'."*
- *"Copy all metadata from original.jpg to backup.jpg."*
- *"Strip all metadata from this file before uploading."*
- *"Set my GPS coordinates on this photo so I can geotag my travels."*
- *"Set the Author tag on all files in my Pictures folder."*
- *"What tags does this file have?"*

The LLM translates your plain-English request into the appropriate `read_metadata`, `write_metadata`, and other ExifTool tools — you don't need to know ExifTool flags.

---

## Testing with the MCP Inspector

```bash
mcp dev server.py
```

This opens a browser-based inspector where you can call tools manually and inspect inputs/outputs before wiring up a full client.

---

## Error Handling

- If ExifTool is not installed, you'll see a helpful error message suggesting
  where to download it from https://exiftool.org/
- Invalid file paths, missing files, or unsupported file types will be reported
  clearly with suggestions for fixes.

---

## License

MIT — see [LICENSE](LICENSE).
