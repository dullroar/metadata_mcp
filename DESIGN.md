# DESIGN.md

# metadata_mcp Design

## Boundary

metadata_mcp is a FastMCP layer over established metadata engines and lightweight local probes. README.md is the tool and installation guide; this document explains the routing model.

## Core decisions

- Start with `inspect_file` for compact filesystem, content-type, and Git context. Verbose or format-specific reads are intentional escalation rather than default context.
- Keep format-specific responsibilities explicit: ExifTool handles embedded/container metadata; mutagen handles audio tags; Pandoc reads semantic metadata from text-centric documents; small in-process handlers cover simple text formats.
- Preserve a direct ExifTool passthrough for capabilities that should not be re-expressed as a growing Python API.
- Support glob inputs at the server boundary so agents can request batch work in one tool call.
- Isolate filesystem, content-type, and Git probe failures so one unavailable source does not suppress other file context.

## Constraints

The server is an orchestration boundary over local tools, not a universal metadata parser. Full nested metadata and Git blame are opt-in because they can consume disproportionate context.


