---
gist: "Read when: changing inspect_file output, defaults for verbosity or nested metadata, or Git blame handling."
---

# Inspect first, escalate deliberately

**Decision.** Start with `inspect_file` for compact filesystem, content-type, and Git context. Verbose or format-specific reads are intentional escalation, not default context. Full nested metadata and Git blame are opt-in because they can consume disproportionate context. Filesystem, content-type, and Git probe failures are isolated so one unavailable source does not suppress the others.
