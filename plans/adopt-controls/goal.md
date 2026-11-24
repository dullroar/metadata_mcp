# Goal: adopt the pinned controls in metadata_mcp

## Ralph loop prompt

Use this prompt for each loop iteration. It has no chat history, so keep it complete.

> You work on plan `adopt-controls` in this repository. Read `AGENTS.md`, then `plans/adopt-controls/goal.md` and `plan.md`.
> Open the step file you were given. Work only in the worktree you were given, on its branch.
> Do only that step. Change only the files in `touches`.
> Run the full test suite that the step names and the `gate` command. If one fails, find the cause and fix it. Do not weaken or delete the gate.
> When the gate passes, set `status: done` and write `evidence` (command, result, date). Commit.
> If you cannot finish, keep `status: in_progress`, write what remains under "Resume notes" in the step file, and commit.
> If you are blocked, set `status: blocked` and write the reason. Do not guess.
> Never push, publish, change a remote or change a GitHub setting. Never run `ralph-pusher`.
> Never write secrets or personal data in any file. Write in Simplified Technical English.

## Goal

`metadata_mcp` is an MCP server (stdio) that reads and writes file metadata with ExifTool and Pandoc. This plan gives it the pinned `deterministic-controls` library and a blocking secret guard. The adoption is advisory: the new CI job is not a required check yet. All existing gates, entry points and CI job names stay.

The library is `v0.1.2` at a pinned commit. Install line:

`python3 -m pip install "deterministic-controls @ git+https://github.com/dullroar/deterministic-controls@3a2e9f3d95136958c54f73c831e84b971fc9a054"`

## Done when

- `python3 scripts/check_context.py` passes. It runs the pinned library through a shim.
- `bash scripts/test_docker.sh` passes. The unit tests and the stdio smoke test (`tests/smoke_stdio.py`) still pass with the real native binaries. The Docker run has no network.
- The secret guard runs in CI (`--tracked`, and `--range` on pull requests) and in the pre-commit and pre-push hooks.
- Known-bad probes fail with the expected rule ID. The rollback is tested.
- `docs/controls-adoption.md` has the receipt and the rollback.
- Every step of this plan is `done` with evidence.

## Out of scope

- Any other repository. Pushing, publishing, changing a remote or a GitHub setting.
- Required checks and branch protection. The operator does that later.
- Changes to product code, to the existing tests, to the host entry points or to the pinned library.
