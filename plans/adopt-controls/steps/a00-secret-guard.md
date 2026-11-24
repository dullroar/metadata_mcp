---
id: a00-secret-guard
status: pending
depends_on: []
touches:
  - scripts/secret_guard.py
  - scripts/install_hooks.sh
  - tests/test_secret_guard.py
  - .github/workflows/context.yml
  - scripts/AGENTS.md
  - plans/AGENTS.md
  - plans/adopt-controls/steps/a00-secret-guard.md
lane: none
tier: light
gate: python3 -m unittest discover -s tests -p 'test_secret_guard.py' -v && bash scripts/install_hooks.sh --self-test && python3 scripts/secret_guard.py --tracked && grep -q 'secret_guard.py --tracked' .github/workflows/context.yml && grep -q 'secret_guard.py --range' .github/workflows/context.yml && grep -q 'contents: read' .github/workflows/context.yml && ! grep 'uses:' .github/workflows/context.yml | grep -vqE '@[0-9a-f]{40}' && python3 scripts/build_indexes.py --check && python3 scripts/check_context.py && git diff --check
requirements: [R1]
claimed_by: ""
claimed_at: ""
evidence: ""
---

# Install the secret guard, the hooks and the CI step

This repository has no secret guard. Secrets must never be committed. The guard is required from the first commit, with no advisory phase.

## Change

- Copy `plans/adopt-controls/reference/secret_guard.py` to `scripts/secret_guard.py`. Do not change its text.
- Copy `plans/adopt-controls/reference/install_hooks.sh` to `scripts/install_hooks.sh`. Do not change its text. Make it executable.
- Copy `plans/adopt-controls/reference/test_secret_guard.py` to `tests/test_secret_guard.py`. Do not change its text. It builds every synthetic secret at run time. It needs the `git` program (it makes temporary repositories). Step `a02-apply` makes sure the Docker image has `git`, because the Docker test run collects `tests/`.
- `.github/workflows/context.yml`: keep the workflow name, the triggers, the job names `check` and `docker` and all existing steps. Add `permissions: contents: read` to the workflow. In the `check` job, set `fetch-depth: 0` on the checkout (keep `persist-credentials: false` where it is set). Add two steps before the existing steps of that job: `Secret guard on all tracked files` runs `python3 scripts/secret_guard.py --tracked`. `Secret guard on every commit of the pull request` runs only for `pull_request` events and runs `python3 scripts/secret_guard.py --range "$BASE_SHA..$HEAD_SHA"`. Take `BASE_SHA` from `github.event.pull_request.base.sha` and `HEAD_SHA` from `github.event.pull_request.head.sha` through `env:`. Keep `persist-credentials: false` on the checkout of the `docker` job.
- Pin each `uses:` action in this file to a full 40-character commit SHA, with the tag in a trailing comment. For `actions/checkout` use `11d5960a326750d5838078e36cf38b85af677262` with the comment `# v4.4.0` (the pin that `repo-template` uses). If you can reach the network, check it with `git ls-remote --tags https://github.com/actions/checkout`. If it does not match, use the SHA of the newest `v4` tag and write that under "Resume notes".
- Run `bash scripts/install_hooks.sh` in this clone. Run `python3 scripts/build_indexes.py`. It lists the new scripts and the `adopt-controls` plan in `scripts/AGENTS.md` and `plans/AGENTS.md`.

## Do not change

- Files outside `touches`. The `gate` command.
- Do not add an exception to `.secret-guard-allow` to pass the guard. If the guard finds something, remove the cause.
- Do not change the Docker step, `scripts/test_docker.sh` or the `Dockerfile` in this step.

## Already done by earlier steps

- None. This is the first step.

## Done when

- The guard tests pass. The hook self-test passes. The guard finds nothing in the tracked files.
- The workflow runs the guard on all tracked files and, for pull requests, on every commit of the range. Every action is pinned.
- The generated indexes are fresh.

## Record

Set `status: done`. Fill `evidence` with the gate command, the result and the date.
If you cannot finish, write "Resume notes" below. Keep the status `in_progress`.

## Resume notes

(none)
