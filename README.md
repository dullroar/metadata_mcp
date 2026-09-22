# metadata_mcp

For the tool-routing architecture and constraints, see [DESIGN.md](DESIGN.md).

**Author:** Jim Lehmer  
**License:** MIT

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that gives coding agents compact file context plus embedded and semantic document metadata across a broad range of formats. Connect it to any MCP-compatible client and inspect filesystem, content type, Git facts, document attributes, and format-specific tags without rebuilding the relevant parsers in every agent.

---

## Why the name?

This server started as a thin ExifTool wrapper. It has since grown a compact, cross-file context probe; a Pandoc semantic-document reader; and backends for audio formats ExifTool can't write (mutagen) and text-based formats with no binary metadata section (HTML, Markdown). "exiftool_mcp" no longer described it; "metadata_mcp" does.

## First call for coding agents: `inspect_file`

Use `inspect_file` for one exact path before reading source or embedded tags. It returns independently computed sections, so a missing optional command (such as Git or `file`) does not hide valid filesystem facts.

```python
# Compact file context: stat attributes, libmagic type, Git status, and last file commit
inspect_file(path="server.py")

# Attribute only the source lines relevant to a change request
inspect_file(path="server.py", blame_start_line=85, blame_end_line=120)
```

Its default response includes:

- **Filesystem** — normalized and resolved paths, kind, symlink status, size/allocation, permissions, owner IDs on POSIX, and UTC timestamps.
- **Content type** — libmagic (`file`) description, MIME type, and encoding. If `file` is unavailable, extension-based values are returned only as an explicitly labeled fallback.
- **Git** — worktree root, branch and HEAD, tracking/worktree status, and the last commit affecting the file. Files outside a Git worktree receive an explicit `not_repository` status.

Git blame is never returned unless both inclusive line bounds are supplied. `inspect_file` does not return document or embedded tags. Use `read_document_attributes` for semantic text-document attributes and `read_metadata` for potentially verbose embedded/container tags.

## Semantic text-document attributes: `read_document_attributes`

Use this exact-path, read-only tool when a document's meaning-bearing attributes matter: title, author, date, language, description, keywords, YAML-frontmatter values, and similar fields. It asks Pandoc to read the document into its JSON AST, then returns a compact normalized view rather than document content.

```python
# Markdown YAML frontmatter, including custom scalar/list fields
read_document_attributes(path="proposal.md")

# HTML title, author, description, language, and standard meta fields
read_document_attributes(path="site/about.html")

# Inspect nested notebook metadata only when it is specifically needed
read_document_attributes(path="analysis.ipynb", include_full_metadata=True)
```

Supported inferred readers include Markdown, HTML/XHTML, RST, Org, RTF, LaTeX, Jupyter notebooks, DocBook/JATS, OPML, and several wiki/text-markup formats. For an unusual extension, pass an explicit Pandoc `source_format`.

This tool is deliberately **not** the route for PDF, legacy Word/OLE, OOXML (`.docx`, `.xlsx`, `.pptx` and related files), OpenDocument, or EPUB. Use `read_metadata` for those formats: ExifTool exposes their core, application, and custom/container properties more completely than Pandoc. Pandoc cannot read PDF, and local verification shows its DOCX reader can omit Word subject and custom properties.

---

## Backend Architecture

The server dispatches automatically to the right backend based on file extension. You never need to specify which backend to use.

| Format(s) | Embedded/container metadata | Semantic attributes | Write backend |
|---|---|---|---|
| JPEG, TIFF, PNG, HEIC, WebP, RAW, GIF… | ExifTool | — | ExifTool |
| PDF, Word/OLE, OOXML, ODF, EPUB | ExifTool | Use `read_metadata` | ExifTool where supported |
| MP4, MOV, MKV, AVI… | ExifTool | — | ExifTool |
| MP3 | ExifTool | — | mutagen — ID3v2 frames |
| OGG, Opus | ExifTool | — | mutagen — Vorbis comment tags |
| HTML, XHTML | ExifTool raw tags | Pandoc normalized fields | `<meta name="...">` injection in `<head>` |
| Markdown, RST, Org, LaTeX, notebooks, markup | Limited or format-dependent | Pandoc normalized fields | YAML frontmatter for Markdown |

### ExifTool

Handles the widest range of formats. Required for reading metadata from any format and for writing to images, video, and PDF. Must be installed separately and on `PATH`.

### mutagen

Used for audio formats ExifTool can write only partially or not at all. Installed as a Python dependency in the server venv. Tag names are mapped to the appropriate ID3v2 frame (MP3) or used verbatim as Vorbis comment keys (OGG/Opus).

### Pandoc document reader

`read_document_attributes` uses `pypandoc` and a locally installed Pandoc executable to read semantic metadata from text-centric documents. Its default response includes scalar and list attributes only. Nested metadata maps are named in `omitted_attributes`; set `include_full_metadata=True` only when their raw Pandoc AST is worth the additional context.

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

### `inspect_file`

Compact, read-only context for one exact file or directory path. This is the preferred first tool for coding agents.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | One exact path; glob patterns are not expanded |
| `blame_start_line` | `int` | optional | First line for bounded Git blame; requires `blame_end_line` |
| `blame_end_line` | `int` | optional | Last inclusive line for bounded Git blame; requires `blame_start_line` |

### `read_document_attributes`

Read compact semantic attributes from one Pandoc-readable text document. It does not modify the document or expand globs.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str` | required | One exact path |
| `source_format` | `str` | inferred | Pandoc reader for an unusual/ambiguous extension |
| `include_full_metadata` | `bool` | `False` | Include the full raw Pandoc metadata AST, including nested maps |

The response contains `attributes`, `omitted_attributes`, selected `source_format`, and the installed Pandoc version. For PDF, Office/OOXML, OpenDocument, and EPUB, it returns a `not_applicable` response that directs the caller to `read_metadata`.

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
- Git installed and on `PATH` for repository context and blame (optional)
- A `file` command backed by libmagic for content sniffing (optional; extension fallback is labeled)
- [Pandoc](https://pandoc.org/installing.html) installed and on `PATH` for semantic document attributes (optional)
- Python packages: `mcp[cli]`, `mutagen`, `pypandoc` (see `requirements.txt`)

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

- *"Inspect this file before editing it; tell me its type, Git state, and last commit."*
- *"Who last changed lines 85 through 120 of this file?"*
- *"What are this Markdown document's frontmatter attributes?"*
- *"Read the title, author, description, and language from this HTML file."*
- *"Show the full notebook metadata only if its compact document attributes omit something relevant."*
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

## Project-context templates for file-heavy work

This repository includes [sample-CLAUDE.md](sample-CLAUDE.md) and [sample-AGENTS.md](sample-AGENTS.md). They have identical content and are intentionally prefixed with `sample-` so they do **not** govern this MCP project.

For a project that will read or manipulate many files, copy the template appropriate to its agent environment into that project, then remove the prefix: `sample-CLAUDE.md` → `CLAUDE.md` or `sample-AGENTS.md` → `AGENTS.md`. The template directs future agents to use this server's registered tools before ad-hoc parsing or metadata-writing code, preserving bounded context, reproducible extraction, and a shared cross-agent tool vocabulary.

---

## Testing with the MCP Inspector

```bash
mcp dev server.py
```

---

## License

MIT — see [LICENSE](LICENSE).
