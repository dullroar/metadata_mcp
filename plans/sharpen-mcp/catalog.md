# Proposed metadata_mcp methods

Each row is a bounded public workflow. Grouping controls implementation order. Confirm capabilities against the pinned Docker backend before advertising a method. Keep source provenance and unsupported cases visible in the shipped documentation.

## Core

| Tool | Use this when | Acceptance focus |
| --- | --- | --- |
| `inspect_file` | Get type, size and compact context before choosing a tool. | Existing exact path and bounded Git context. |
| `read_metadata` | Read selected camera, container or audio fields. | Finite canonical fields and backend provenance. |
| `read_document_attributes` | Read title, author, date, language and rights from a supported document. | Pandoc metadata AST, front matter and compatibility matrix. |
| `find_missing_metadata` | Locate supported files with no non-empty Copyright field anywhere authoritative. | Stable scan results with present, missing, unsupported, unreadable and conflicting states. |
| `audit_metadata` | Inventory ownership and descriptive field coverage across a folder. | Read-only bounded scan with per-format support and aggregated counts. |
| `compare_metadata` | Explain why an original and export differ. | Canonical and native differences with ignored volatile fields explicit. |
| `export_metadata_csv` | Create a review worksheet of selected metadata fields. | Stable column order, provenance/status columns and safe CSV text. |
| `set_copyright` | Set an explicit rights statement on verified target formats. | Typed rights field, preview/re-read and safe output. |
| `set_author` | Set a verified creator name. | Typed canonical creator mapping and backend read-back. |
| `set_description` | Apply a description or caption. | Typed fields and format-specific mapping. |
| `write_metadata` | Apply a small structured metadata patch. | Finite canonical field map with format-specific support and one operation per field. |

## Expanded

| Tool | Use this when | Acceptance focus |
| --- | --- | --- |
| `copy_metadata` | Copy title and copyright from an original to exports. | Explicit canonical field subset, conflict and overwrite policies. |
| `strip_metadata` | Create a shareable derivative with selected metadata classes removed. | Enumerated privacy profile, read-back and transparent format limitations. |
| `set_gps` | Write explicit coordinates to an approved photo format. | Finite range, typed altitude and omission-aware read-back. |
| `find_inconsistent_metadata` | Locate files with conflicting embedded and semantic owners or dates. | Compare normalized values without flattening sources. |
| `audit_sensitive_metadata` | Report whether photos or documents expose location or device identifiers. | Read-only presence checks with values omittable by default. |
| `normalize_metadata_dates` | Standardize supported timestamps after review. | Typed date/time zones, preservation of original provenance and explicit ambiguity. |
| `apply_metadata_manifest` | Patch an approved batch of assets after preview. | Bounded typed manifest, preconditions, per-file results and verified writes. |
| `inventory_document_metadata` | Build a compact document catalog. | Typed semantic fields via documented readers, with unsupported formats explicit. |

## Primary references

- [ExifTool application manual](https://www.exiftool.org/exiftool_pod.pdf)
- [ExifTool tag tables](https://exiftool.org/TagNames.pdf)
- [ExifTool source and format support](https://github.com/exiftool/exiftool)
- [Pandoc manual and YAML metadata](https://pandoc.org/MANUAL.html#extension-yaml_metadata_block)
- [Mutagen format APIs](https://mutagen.readthedocs.io/en/latest/api/index.html)
