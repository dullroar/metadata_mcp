# adopt-controls for metadata_mcp - specification and execution agreement

Status: approved (by the owner, as part of the controls rollout program decisions of 2026-11-23: pilot repositories, advisory enforcement, secret guard from the first commit)

## Goal and exclusions

Adopt the pinned `deterministic-controls` library in advisory mode and add a blocking secret guard. Keep every existing gate, entry point and CI job.

This work does NOT change product code, the existing tests, the host entry points, the Docker run commands, branch protection or any remote.

## Requirements

### R1. The secret guard blocks a secret before it is committed or pushed

- Basis: documented (rollout program rule: secrets are never tracked, committed or pushed).
- Example: a tracked Markdown file with a synthetic token -> `python3 scripts/secret_guard.py --tracked` exits with a nonzero code.
- Acceptance check: `tests/test_secret_guard.py` and `bash scripts/install_hooks.sh --self-test`.

### R2. The pinned library runs the context checks and the existing gates still pass

- Basis: documented (rollout program, child spec `adopt-controls`).
- Example: `python3 scripts/check_context.py` runs the library from the pinned commit and exits `0` on the clean tree.
- Acceptance check: `python3 scripts/check_context.py` and `python3 scripts/build_indexes.py --check`.

### R3. A known-bad input fails with the expected rule ID, and the adoption can be rolled back

- Basis: documented (rollout program).
- Example: a step file without `gate` -> the check fails with `plans.schema`.
- Acceptance check: the probe table and the rollback test in `docs/controls-adoption.md`.

### R4. The full gates pass from a clean clone, with the real native tools

- Basis: documented (rollout program).
- Example: `bash scripts/test_docker.sh` exits `0` in a clone. The unit tests and the stdio smoke test run and pass.
- Acceptance check: the commands and results recorded in the evidence of step `a04-verify`.

## Constraints and assumptions

- The controls job is advisory. It fails honestly (no `continue-on-error`). It is not required in branch protection yet. The operator decides that later.
- The Docker run has no network (`--network none`) and a read-only root file system. The shim needs the network once for each pinned commit. So the image build must prepare the library (see step `a02-apply`).
- Assumption (inferred, the operator can confirm): the host has network access when the Docker image builds.

## Domain challenge

- The tests use the real ExifTool and Pandoc binaries. They stay on the required path. Do not mock them.

## Delegated authority

- The executor MAY: change the files in the `touches` of its step; run the local checks and the full tests; read the pinned library help.
- The executor MUST NOT: weaken, skip or delete a gate or a protected check; change requirements; push, publish or change a remote or a GitHub setting; add a secret guard exception to pass a step.

## Acceptance and evidence

- Protected checks: the `gate` of each step, `scripts/check_context.py`, `python3 -m unittest discover -s tests -v`, `python3 tests/smoke_stdio.py`, `scripts/test_docker.sh`.
- Combined validation after the last step: `bash scripts/test_docker.sh` in a clean clone.
- Completion evidence is in each step's `evidence:` field.

## Escalate when

Contradictory requirements, scope expansion, an action outside the delegated authority, or a protected check that cannot pass as written. Failed tests and dead ends inside scope: diagnose, repair, continue.

## Exceptions and retirements

None. No rule is retired. No violation is tolerated.
