---
gist: "Read when: adding a file format, changing which engine reads a format, or extending the ExifTool passthrough."
---

# Format-specific engine routing

**Decision.** Responsibilities are explicit: ExifTool handles embedded/container metadata; mutagen handles audio tags; Pandoc reads semantic metadata from text-centric documents; small in-process handlers cover simple text formats. A direct ExifTool passthrough is kept for capabilities that should not be re-expressed as a growing Python API, and glob inputs are supported at the server boundary so agents can batch in one call.

**Boundary.** An orchestration boundary over local tools, not a universal metadata parser.
