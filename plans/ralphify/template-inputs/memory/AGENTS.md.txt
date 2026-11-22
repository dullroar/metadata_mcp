# Memory index

<!-- IMMUTABLE HEADER: do not edit the text above the BEGIN marker. -->

This folder holds memories for agents. Humans read `docs/` instead.

- One memory is one file. Many agents can write at the same time without a lock.
- Each file starts with front matter: `gist: "Read me when: <situation>"`.
- Edit the existing file for a topic. Do not add a second file for the same topic.
- **NEVER put PII, secrets, keys, tokens, passwords, personal paths or private host names in a memory.** Memory files are tracked by Git and can become public.
- Write in Simplified Technical English (ASD-STE100).
- This file is generated. Run `python3 scripts/build_indexes.py` after any change. Do not edit the list below by hand.

Read the list. Open only the files whose "Read me when" line matches your task.

<!-- BEGIN GENERATED INDEX -->

* [example-memory.md](./example-memory.md)
  Read me when: you want to see the format of a memory file. (Template only. Delete this file in new repositories.)

<!-- END GENERATED INDEX -->
