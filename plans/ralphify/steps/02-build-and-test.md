---
id: 02-build-and-test
status: pending
depends_on: [01-adopt-context]
touches:
  - Dockerfile
  - .dockerignore
  - README.md
  - scripts/test_docker.sh
  - scripts/AGENTS.md
  - .github/workflows/context.yml
  - tests/**
  - plans/ralphify/steps/02-build-and-test.md
lane: none
requirements: [R2]
gate: bash scripts/test_docker.sh && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# 02-build-and-test

Depends on `01-adopt-context`. Add a project Dockerfile, an appropriate `.dockerignore`, and `scripts/test_docker.sh`. Use project dependencies and current lockfiles. Run project tests as a normal container user where supported. Use synthetic fixtures, a temporary output directory, and no developer credentials. Put any new operational or test artifacts under the repo's existing conventions. Document build, test, and any device or platform requirements in `README.md`. Keep existing host usage working. Arrange for CI to call the same entry point wherever the runner supports that gate.

The Docker test script builds the image from the current step worktree and runs the repo-specific gates inside it. For context checks, use a complete source snapshot or an appropriate read-only checkout that works with linked Git worktrees. A linked worktree's `.git` pointer alone does not provide its Git metadata in the container. Keep the image usable without a sibling checkout, host venv, or mutable shared volume. Use repo- and run-specific names for any image tags, container names, and writable paths. Build dependencies can use package registries. The default test runtime uses local fixtures and an isolated container network. The FUSE mount gate is required for the two FUSE lanes, with the host requirements in their repo briefs.

Touches `Dockerfile`, `.dockerignore`, `README.md`, `scripts/test_docker.sh`, generated indexes, any necessary workflow updates, focused test/support paths from the repo brief, and this step file. Gate: `bash scripts/test_docker.sh && python3 scripts/check_context.py && git diff --check`.

## Repository gate

Install ExifTool, Pandoc, and the existing Python requirements. Run `python3 -m unittest discover -s tests -v` and exercise the real binaries through a small stdio smoke if existing tests mock them. Verify a Pandoc semantic attribute and an ExifTool field from synthetic files. Keep real native commands on the required path and record any skips. Add test files under `tests/` as needed. Keep existing host entry points and metadata behavior.
