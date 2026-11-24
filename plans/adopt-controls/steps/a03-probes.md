---
id: a03-probes
status: pending
depends_on: [a02-apply]
touches:
  - docs/controls-adoption.md
  - plans/adopt-controls/steps/a03-probes.md
lane: none
gate: python3 scripts/check_context.py && python3 scripts/build_indexes.py --check && python3 scripts/secret_guard.py --tracked && grep -q '^## Probes' docs/controls-adoption.md && grep -q '^## Rollback' docs/controls-adoption.md && grep -q '^## Receipt' docs/controls-adoption.md && for id in markdown.local-links context.index-freshness plans.schema security.secrets repo.forbidden-artifacts; do grep -q "$id" docs/controls-adoption.md || exit 1; done && grep -q '"control_pin": "3a2e9f3d95136958c54f73c831e84b971fc9a054"' docs/controls-adoption.md && git diff --check
requirements: [R3]
claimed_by: ""
claimed_at: ""
evidence: ""
---

# Prove the controls with known-bad probes, test the rollback and write the receipt

## Change

Work in `docs/controls-adoption.md` only. Agent sessions cannot run `mktemp` or write outside the worktree. Make every throwaway copy inside the worktree, in `.probe/`. The operator excludes `/.probe/` in this clone, so it is never tracked and the scope check ignores it. Use `git clone -q . .probe/copy` (or `.probe/copy-<probe>` for each probe) and run each probe and the library in that copy (`--root .probe/copy`). Never change the real tree for a probe. Delete `.probe/` with `rm -rf .probe` before you run the gate: the planted fake secrets must not be on disk when the real checks run.

- `## Probes`: a table with one row for each probe: the probe, the expected rule ID, the exit code and the result. In the copy, run `python3 -m deterministic_controls check --root <copy> --profile ci --format json` and read the rule ID from the JSON. Probes:
  - a broken relative link in a Markdown file: `markdown.local-links`.
  - a stale generated index (change a script, do not rebuild): `context.index-freshness`.
  - a plan step without `gate`: `plans.schema`.
  - a synthetic token in a Markdown file: `security.secrets`. Build the token at run time in the shell. Never write the token in any tracked file, in the step file or in the table. `security.secrets` reads committed content: commit the token in the copy before you run the check.
  - a tracked `driver.out` file: `repo.forbidden-artifacts`.
  - an internal error (an unreadable file, or a forced exception): the check must not pass. Record the exit code (`2` or `3`).
  Each bad probe must fail with the expected rule ID. Then restore the copy and check that it passes (exit `0`). Also run `python3 scripts/check_context.py` (the shim) in the copy for the bad plan step and record that its exit code is `1`.
- `## Rollback`: test it. There is no earlier pin, so use the pre-adoption scripts. The base commit is the parent of the `adopt apply` commit (find it with `git log`). In a clone under `.probe/`, check out that commit and run its `python3 scripts/check_context.py` on the clean tree. Then run the new shim on a clean clone of `HEAD` under `.probe/`. Record that both pass. Write the steps to roll back: change the pin, or `git revert` the adoption commits on a new branch (list the files that the adoption added, changed and kept), then run `python3 scripts/check_context.py`. Say that the cache under `$XDG_CACHE_HOME/deterministic-controls/<commit>/` is safe to delete.
- `## Receipt`: run `python3 -m deterministic_controls adopt receipt --root <clean clone> --commit 3a2e9f3d95136958c54f73c831e84b971fc9a054` in a clean clone of `HEAD` under `.probe/`. Put the JSON in a fenced `json` block. Say that `repository` is the name of the temporary clone, and that `files_added` and `files_changed` are empty in a clean clone (a known library defect). List the files of the adoption in the Rollback section instead. Say that `enforcement_state` is `advisory`.
- Record the UTC date of each run. Do not write local paths or user names in the file.

## Do not change

- Files outside `touches`. The `gate` command.
- Do not add a secret guard exception.

## Already done by earlier steps

- a02-apply: the shim, the pin, `controls.toml`, the CI job, the Dockerfile change and the first text of `docs/controls-adoption.md`.

## Done when

- The gate passes. Each bad probe fails for the expected reason. The good copy passes. The rollback result is recorded.

## Record

Set `status: done`. Fill `evidence` with the gate command, the result and the date.
If you cannot finish, write "Resume notes" below. Keep the status `in_progress`.

## Resume notes

(none)
