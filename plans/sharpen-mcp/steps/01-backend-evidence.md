---
id: 01-backend-evidence
status: pending
depends_on: []
touches:
  - docs/backend-notes.md
  - docs/README.md
  - plans/sharpen-mcp/steps/01-backend-evidence.md
lane: none
requirements: [R1]
gate: test -s docs/backend-notes.md && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# Verify the backend capabilities

Read `man exiftool`, `exiftool -ver`, the ExifTool file support and tag tables, the installed Pandoc readers, and the Mutagen format API. Make the per-format field matrix central to this plan. Check EXIF/IFD0, IPTC and XMP aliases with grouped JSON output. Trace native Mutagen tags before normalization. Verify which document readers expose YAML copyright and how HTML, PDF and OOXML differ. Audit which backends can write which fields without content loss.

Build a small synthetic corpus in temporary storage. Record installed versions, official references with sections, real operation examples, output fields and tolerances, and options that do not work. Compare the proposed catalog against actual native behavior. For each tool, identify its finite parameter schema, numeric limits, output contract, examples, and the exact backend feature that supports it. Treat community examples as leads and verify behavior against the official backend and installed build.

Use field observations with canonical name, native field and group, backend, original value type, and status. Keep blocked/unknown formats distinct from supported files whose field is absent or blank. If any authoritative source contains non-empty text after trim, it counts as present, with reported conflicts for inconsistent values. Do not infer copyright ownership or licensing. Scoped typed writes use explicit destination, preview and expected state, atomic temp copies, and re-read verification. Preserve original content and untouched tags. Never advertise PDF metadata stripping as irreversible sanitization. Avoid exposing whole document bodies, raw metadata blobs, location data or file content in ordinary results. Keep document semantics via Pandoc and native/container metadata via ExifTool or Mutagen according to support.

Treat the rights audit and the format/field matrix as release gates. Users rely on the difference between missing metadata and an unsupported format.

Write the results to `docs/backend-notes.md` and link it from `docs/README.md`. Record the exact commands and results for successful and unsupported cases.

## Resume notes

Pending.
