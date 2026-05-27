# metadata_mcp

**Author:** Jim Lehmer  
**License:** MIT

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that reads and writes file metadata across a broad range of formats. Connect it to any MCP-compatible LLM client (Claude Desktop, Claude Code, etc.) and ask the model to read or write metadata on images, audio, video, documents, and text files — no knowledge of ExifTool, mutagen, or YAML required.

---

## Why the name?

This server started as a thin ExifTool wrapper. It has since grown backends for audio formats ExifTool can't write (mutagen) and text-based formats with no binary metadata section (HTML, Markdown). "exiftool_mcp" no longer described it; "metadata_mcp" does.

---

## Backend Architecture

The server dispatches automatically to the right backend based on file extension. You never need to specify which backend to use.

| Format(s) | read_metadata | write_metadata backend |
|---|---|---|
| JPEG, TIFF, PNG, HEIC, WebP, RAW, GIF… | ExifTool | ExifTool |
| PDF | ExifTool | ExifTool |
| MP4, MOV, MKV, AVI… | ExifTool | ExifTool |
| MP3 | ExifTool | mutagen — ID3v2 frames |
| OGG, Opus | ExifTool | mutagen — Vorbis comment tags |
| HTML, HTM | — | `<meta name="...">` injection in `<head>` |
| MD, Markdown | — | YAML frontmatter block |

### ExifTool

Handles the widest range of formats. Required for reading metadata from any format and for writing to images, video, and PDF. Must be installed separately and on `PATH`.

### mutagen

Used for audio formats ExifTool can write only partially or not at all. Installed as a Python dependency in the server venv. Tag names are mapped to the appropriate ID3v2 frame (MP3) or used verbatim as Vorbis comment keys (OGG/Opus).

**ID3v2 tag name map (MP3):**

| Tag name (case-insensitive) | ID3v2 frame |
|---|---|
| Comment | COMM |
| Title | TIT2 |
| Artist | TPE1 |
| AlbumArtist | TPE2 |
| Album | TALB |
| TrackNumber / Track | TRCK |
| Genre | TCON |
| Date / Year | TDRC |
| Description | TIT3 |
| Encoder | TSSE |
| Copyright | TCOP |

### In-process text handlers

For formats with no binary metadata section:

- **HTML**: injects or updates a `<meta name="..." content="...">` tag before `</head>`. The ExifTool tag name is mapped to a standard HTML meta name (`Comment` → `description`, etc.); unknown tags are lowercased and used verbatim.
- **Markdown**: writes or updates a YAML frontmatter block (`--- ... ---`) at the top of the file. The tag name is lowercased directly as the YAML key — no fixed mapping, any attribute works.

---

## Bulk Operations

ExifTool-backed tools accept **glob patterns** and **directory paths** natively — ExifTool handles the expansion. This covers `read_metadata`, `set_copyright`, `strip_metadata`, `set_author`, `set_description`, `set_gps`, `copy_metadata`, and `write_metadata` for images/video/PDF.

For `write_metadata` on audio (MP3/OGG/Opus) and text (HTML/Markdown) formats, the server expands globs in Python before dispatching to the format-specific backend. All bulk operations happen in a single tool call — no loop needed.

```python
# Read metadata from every photo — one call, no loop
read_metadata(path="photos/*.jpg")

# Set copyright on every photo — one call, no loop
set_copyright(path="photos/*.jpg", copyright="© 2026 Jim Lehmer")

# Strip metadata from every export — one call, no loop
strip_metadata(path="exports/*.jpg")

# Write ID3 tags to every MP3 — one call, no loop
write_metadata(path="music/*.mp3", tags={"Artist": "Jim Lehmer", "Album": "Demo"})

# Write EXIF to every JPEG — one call, no loop
write_metadata(path="photos/*.jpg", tags={"Copyright": "© 2026"})

# Recursive operation via passthrough
exiftool_passthrough(arguments=["-r", "-all=", "exports/"])
```

---

## Tools

### `read_metadata`

Read all metadata tags from any file. Uses ExifTool.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | File to read |

### `write_metadata`

Write arbitrary tag=value pairs to a file. Backend is chosen automatically.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | File to write |
| `tags` | `dict` | Tag names and values, e.g. `{"Comment": "holiday trip", "Author": "Jim"}` |

### `set_copyright`

Set Copyright tag on a file or directory (ExifTool). Recursive flag available.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | File or directory path |
| `copyright` | `str` | required | Copyright text |
| `recursive` | `bool` | `False` | Apply to all files in directory recursively |

### `set_author`

Set Author tag (ExifTool).

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | File path |
| `author` | `str` | Author name |

### `set_description`

Set Description tag (ExifTool).

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | File path |
| `description` | `str` | Description text |

### `set_gps`

Set GPS coordinates (ExifTool).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | File path |
| `latitude` | `float` | required | GPS latitude |
| `longitude` | `float` | required | GPS longitude |
| `latitudeRef` | `str` | `"N"` | `"N"` or `"S"` |
| `longitudeRef` | `str` | `"E"` | `"E"` or `"W"` |
| `altitude` | `float` | optional | Altitude in metres |
| `altitudeRef` | `str` | `"above"` | `"above"` or `"below"` |

### `copy_metadata`

Copy metadata from source to destination (ExifTool).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `source` | `str` | required | Source file |
| `dest` | `str` | required | Destination file |
| `only` | `list[str]` | optional | Restrict to these tag names |

### `strip_metadata`

Strip all metadata from a file or directory (ExifTool).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | File or directory path |
| `recursive` | `bool` | `False` | Apply recursively |

### `exiftool_passthrough`

Run arbitrary ExifTool CLI commands for operations not covered by the tools above.

| Parameter | Type | Description |
|---|---|---|
| `arguments` | `list[str]` | Raw ExifTool CLI arguments (omit `exiftool` itself) |

---

## Requirements

- Python 3.10+
- [ExifTool](https://exiftool.org/) installed and on `PATH`
- Python packages: `mcp[cli]`, `mutagen` (see `requirements.txt`)

---

## Installation

```bash
git clone https://github.com/dullroar/metadata_mcp.git
cd metadata_mcp

python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

pip install -r requirements.txt
```

---

## MCP Client Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "metadata": {
      "command": "/path/to/metadata_mcp/.venv/bin/python",
      "args": ["/path/to/metadata_mcp/server.py"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add metadata -- /path/to/metadata_mcp/.venv/bin/python /path/to/metadata_mcp/server.py
```

### HTTP/SSE mode

```bash
python server.py --transport sse
# Listening on http://127.0.0.1:8000/sse
```

| Flag | Default | Description |
|---|---|---|
| `--transport` | `stdio` | `stdio` or `sse` |
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8000` | Bind port |

---

## Example Prompts

- *"Read all the metadata from this photo and tell me what camera was used."*
- *"Read the metadata from every photo in photos/ and summarize what cameras were used."*
- *"Set the Comment field on this MP3 to 'ripped from vinyl'."*
- *"Set the Artist and Album on every MP3 in music/ to 'Jim Lehmer' and 'Demo'."*
- *"Add an Author and Copyright field to this Markdown file."*
- *"Inject a description meta tag into this HTML page."*
- *"Set copyright on every JPEG in photos/ to '© 2026 Jim Lehmer'."*
- *"Copy all metadata from original.jpg to backup.jpg."*
- *"Strip all metadata from this file before uploading."*
- *"Strip all metadata from every JPEG in exports/ before I upload them."*
- *"Set my GPS coordinates on this photo to geotag my travels."*

---

## Testing with the MCP Inspector

```bash
mcp dev server.py
```

---

## License

MIT — see [LICENSE](LICENSE).
