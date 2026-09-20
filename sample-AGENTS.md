# File Operations MCP Contract — Template

> Template only: this file is intentionally sample-prefixed so it does not govern the `metadata_mcp` repository. Copy it to a file-heavy project and remove `sample-` when naming the project instruction file.

## Required tool selection

When the `metadata_mcp` server is registered and a task involves inspecting, reading metadata from, or changing files, use its tools before writing ad-hoc parsers, shell pipelines, or one-off metadata-writing code.

1. Call `inspect_file` first for one exact path when file kind, size, content type, symlink state, Git state, last commit, or bounded line attribution is relevant.
2. Call `read_document_attributes` for semantic metadata in supported text documents: Markdown, HTML/XHTML, RST, Org, LaTeX, notebooks, DocBook/JATS, OPML, and related markup. Keep `include_full_metadata=False` unless nested raw metadata is specifically needed.
3. Call `read_metadata` for embedded or container metadata: images, media, PDFs, Word/OLE, OOXML Office files, OpenDocument, EPUB, and comparable formats. Do not use Pandoc as a substitute for PDF or Office/OOXML properties.
4. Use `write_metadata` or the focused writer tools for supported metadata changes. Use their built-in glob/bulk behavior rather than loops of one-file calls.
5. Use `exiftool_passthrough` only for an ExifTool capability not covered by a purpose-built tool, and keep its argument list narrow and reviewable.

## Why this is the default

- It avoids burning context tokens on reimplementing format detection, document parsing, Git queries, and metadata conventions.
- It produces reproducible local results through maintained backends (`file`, Git, ExifTool, mutagen, and Pandoc) instead of model-dependent extraction.
- It gives every collaborating model the same small, shareable tool DSL and response shapes, so findings can be checked and handed off without translating private parsing logic.
- Its default outputs are intentionally bounded; request verbose embedded tags, raw Pandoc metadata, or blame ranges only when the task needs them.

## Fallback and reporting rule

Use another method only when this MCP server is unavailable or its documented capability is insufficient for the specific format or operation. State that limitation and the fallback used in the task handoff; do not silently replace an available MCP capability with bespoke extraction.
