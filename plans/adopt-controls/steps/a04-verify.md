---
id: a04-verify
status: pending
depends_on: [a03-probes]
touches:
  - plans/adopt-controls/steps/a04-verify.md
lane: none
tier: light
gate: d=$(mktemp -d) && trap 'rm -rf "$d"' EXIT && git clone -q . "$d/clone" && cd "$d/clone" && python3 scripts/check_context.py && python3 scripts/build_indexes.py --check && python3 scripts/secret_guard.py --tracked && bash scripts/install_hooks.sh --self-test && python3 -m unittest discover -s tests -p 'test_secret_guard.py' && bash scripts/test_docker.sh && cd - >/dev/null && grep -q 'history-findings=[0-9]' plans/adopt-controls/steps/a04-verify.md
requirements: [R4]
claimed_by: ""
claimed_at: ""
evidence: ""
---

# Verify the full gates from a clean clone

## Change

This step changes only its own step file. Agent sessions cannot clone to a temporary directory, use `mktemp` or run Docker. The gate does that: it clones the committed `HEAD` into a temporary directory, runs every check there and runs `bash scripts/test_docker.sh` (the unit tests, the stdio smoke test and the context check, in a container with no network). Your part:

1. In this worktree, run `python3 scripts/secret_guard.py --history`. Write its finding count on its own line under "Resume notes" as `history-findings=<count>` (`0` if none), in place of `(none)`. If the count is more than `0`, do not hide it: list the findings by rule and path (never the secret) under "Resume notes", set the status to `blocked` and stop. The owner decides.
2. Run `python3 scripts/check_context.py`, `python3 scripts/build_indexes.py --check`, `python3 scripts/secret_guard.py --tracked`, `bash scripts/install_hooks.sh --self-test` and the host tests that run without Docker: `python3 -m unittest discover -s tests -v`; if the host has no ExifTool or Pandoc, say so and run the rest. Write each command, its result, the test counts and the UTC date in `evidence`.
3. Say under "Resume notes" that the Docker and clean-clone checks ran in the gate, not in your session. Do not claim a Docker result. Commit.

## Do not change

- Files outside `touches`. The `gate` command. Any other file in this repository.

## Already done by earlier steps

- a03-probes: the probes, the rollback test and the receipt in `docs/controls-adoption.md`.

## Done when

- The gate passes. The evidence has the commands, the results, the counts, the date and the history count.

## Record

Set `status: done`. Fill `evidence` with the gate command, the result and the date.
If you cannot finish, write "Resume notes" below. Keep the status `in_progress`.

After the operator merges this plan, the operator runs `bash scripts/install_hooks.sh` in the canonical clone.

## Resume notes

(none)
