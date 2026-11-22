---
id: 03-verify-integration
status: done
depends_on: [02-build-and-test]
touches:
  - plans/ralphify/steps/03-verify-integration.md
lane: none
requirements: [R3]
gate: python3 scripts/check_context.py && bash scripts/test_docker.sh && git diff --check
evidence: gate passed 2026-11-22 (driver-verified)
claimed_by: codex cli-default
claimed_at: "2026-11-22T21:07:18Z"
---

# 03-verify-integration

Depends on `02-build-and-test`. Update only the step file. Rerun the context and Docker gate from the integrated worktree as the driver would. Check the template and runner links in `AGENTS.md` and the structural-change rule. Verify README commands and the existing entry points. Record the worktree base commit, exact commands, build result, test counts or concrete smoke assertions, expected opt-in skips, real FUSE result where required, and UTC date. Keep logs outside Git. Gate: `python3 scripts/check_context.py && bash scripts/test_docker.sh && git diff --check`.

The driver writes its own `evidence` field. Put detailed test evidence in the body of the verification step and commit it. The parent verifies the final child commit and result. A green build alone cannot satisfy R2 or R3.

## Repository gate

Install ExifTool, Pandoc, and the existing Python requirements. Run `python3 -m unittest discover -s tests -v` and exercise the real binaries through a small stdio smoke if existing tests mock them. Verify a Pandoc semantic attribute and an ExifTool field from synthetic files. Keep real native commands on the required path and record any skips. Add test files under `tests/` as needed. Keep existing host entry points and metadata behavior.

Run `git merge-base HEAD plan/ralphify` to identify the integrated base commit. Replace each pending value in the results below. For each passing check, put details after `PASS`. Include the actual Docker commands or image reference and test counts or concrete smoke results. Record `n/a` in the FUSE field for other repos. If a required test fails or skips, record that in resume notes and leave the result pending.

## Results

- Base commit: `483056372ba4da4d6fc1852df19c3b2beb70d186` from
  `git merge-base HEAD plan/ralphify`.
- Commands: PASS. `python3 scripts/check_context.py && bash scripts/test_docker.sh && git diff --check`.
  The context checks passed on the host and in the container.
- Docker build: PASS. `docker build --tag "$image" .` built the current worktree
  with a temporary `metadata-mcp-test` image tag.
- Tests: PASS. `python3 -m unittest discover -s tests -v` passed 17 tests.
  `python3 tests/smoke_stdio.py` verified the Markdown title from Pandoc and the
  HTML title from ExifTool through MCP stdio. Docker ran both commands with
  `--network none`.
- Skips: None. The required native tool checks ran.
- FUSE: n/a.
- UTC date: 2026-11-22.

## Links and entry points

- Both upstream links in `AGENTS.md` returned HTTP 200. Its structural-change
  rule requires agents to read both sources and account for their layout, plan
  format, generated indexes, worktree rules, and validation commands.
- The Docker gate ran the README build command with a temporary image tag and
  ran the README test command as written. The runner's `--help` confirms the
  README command accepts `--repo`, `--plan`, and `--agent codex`. This step ran
  under the active plan and did not start a second plan loop.
- The default `server.py` entry point passed the stdio smoke test.
  `python server.py --transport sse` served `/sse` with HTTP 200, a
  `text/event-stream` content type, and an `endpoint` event. `mcp dev --help`
  succeeded. The Inspector UI was not launched.

## Resume notes

None.
