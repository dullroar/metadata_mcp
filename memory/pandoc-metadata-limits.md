---
gist: "Read when: routing a metadata read for PDF, Word, OOXML, ODF or EPUB through Pandoc."
---

# Pandoc metadata limits

- 2026-09-20 - Pandoc cannot read PDF and did not expose DOCX subject/custom properties in local testing; route PDF, legacy Word/OLE, OOXML, ODF, and EPUB metadata reads through the ExifTool-backed `read_metadata` instead.
