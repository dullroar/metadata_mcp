# Memory index

<!-- IMMUTABLE HEADER: do not edit the text above the BEGIN marker. -->

This folder holds memories for agents. Humans read `docs/` instead.

- Record findings that would cost time to find again. Note the date, conditions, and when a finding may be obsolete.
- Use one file per topic. Agents can update separate topics at the same time.
- Each file starts with front matter: `gist: "Read me when: <situation>"`.
- Edit the existing file for a topic. Do not add a second file for the same topic.
- **NEVER put PII, secrets, keys, tokens, passwords, personal paths or private host names in a memory.** Memory files are tracked by Git and can become public.
- Write in Simplified Technical English (ASD-STE100). Keep raw logs outside the repository.
- This file is generated. Run `python3 scripts/build_indexes.py` after any change. Do not edit the list below by hand.

Read the list. Open only the files whose "Read me when" or "Read when" line matches your task.

<!-- BEGIN GENERATED INDEX -->

* [fastmcp-registration-checks.md](./fastmcp-registration-checks.md)
  Read when: writing or debugging a test that verifies FastMCP tool registration.
* [local-python-environment.md](./local-python-environment.md)
  Read when: a command fails because python is missing, or the checkout's environment is rebuilt.
* [pandoc-metadata-limits.md](./pandoc-metadata-limits.md)
  Read when: routing a metadata read for PDF, Word, OOXML, ODF or EPUB through Pandoc.

<!-- END GENERATED INDEX -->
