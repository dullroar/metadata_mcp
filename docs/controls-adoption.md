---
gist: "Read me when: you run, change or roll back the pinned deterministic-controls library, or you need to know why the Dockerfile builds a cache."
---

# Controls adoption

This repository runs the pinned `deterministic-controls` library. The adoption is advisory. The new CI job `controls` is not a required check.

## How it works

- `scripts/check_context.py` is a shim. It runs the library. It keeps the old output lines (`ok  <script>` or `FAIL <script>`) and the exit codes `0` and `1`.
- `scripts/controls-requirements.txt` holds the pin. It is one install line with a full commit.
- `controls.toml` lists the enabled checks and the profile.
- The shim runs the library from a cached virtual environment. The cache path is `$XDG_CACHE_HOME/deterministic-controls/<commit>/`. The default is `~/.cache/deterministic-controls/<commit>/`.
- The first run for a commit needs the network. The shim builds the cache then. Later runs need no network.
- If the library cannot run, the shim exits `2`. It never passes without a result. It never uses the old scripts instead.
- The old check scripts stay in `scripts/`. The shim does not call them.

## How the adoption was made

1. Audit. Step `a01-audit` ran a read-only audit. The result is in `docs/controls-audit.json`.
2. Plan. `adopt plan` made a dry run with the pinned commit. The operator read it.
3. Apply. `adopt apply` wrote the shim, the pin, `controls.toml` and the `controls` CI job. Edits by hand followed (see the next section).

## Where the tools did not fit

- `adopt apply` rewrote `scripts/install_hooks.sh` (a `secretguard.path` fallback). That file is outside the scope of the step. It was restored to the earlier version.
- `adopt apply` did not commit its changes. The step commit holds them.
- The Docker run has no network and uses `--read-only`. The shim needs the network once. So the `Dockerfile` builds the cache at image build time, as user `dev`, after `COPY . .` and `USER dev`. The build has network access. The run only reads the cache.
- The Docker run was not verified in the agent session, which cannot run Docker. The driver gate runs it. If the shim writes outside `/tmp` at run time, record the path here.
- `.dockerignore` is an allowlist. The image did not get `controls.toml`, so the check failed in the container with "manifest not found". The step added `!controls.toml`. The excludes for secrets did not change.
- `scripts/controls-requirements.txt` already had a `Run me when:` line from `apply`.

## Probes

Each probe ran in its own clone of `HEAD`, under `.probe/` in the worktree. The command was `python3 -m deterministic_controls check --root <copy> --profile ci`. Run date (UTC): 2026-11-24.

| Probe | Expected rule ID | Exit code | Result |
| --- | --- | --- | --- |
| Broken relative link in a Markdown file | `markdown.local-links` | 1 | Failed with `markdown.local-links.missing-file`. |
| Stale generated index (script changed, index not rebuilt) | `context.index-freshness` | 1 | Failed with `context.index-freshness.stale`. |
| Plan step without `gate` | `plans.schema` | 1 | Failed with `plans.schema.missing-gate`. |
| Synthetic token in a committed Markdown file | `security.secrets` | 1 | Failed with `security.secrets.aws-access-key-id`. The token was built at run time. `security.personal-data` also reported it. |
| Tracked `driver.out` file | `repo.forbidden-artifacts` | 1 | Failed with `repo.forbidden-artifacts.tracked`. |
| Internal error (unreadable Markdown file) | none (must not pass) | 3 | Status `error`. `markdown.local-links` and `security.personal-data` reported a permission error. |

Each probe was then restored. Each restored copy passed with exit `0`. A clean clone of `HEAD` also passed with exit `0`.

The shim ran in the copy with the bad plan step. `python3 scripts/check_context.py` printed `FAIL check_plan.py` and exited `1`.

## Rollback

There is no earlier pin. The rollback uses the pre-adoption scripts. Tested on 2026-11-24 (UTC):

- Base commit: the parent of the `adopt apply` commit. In a clone under `.probe/`, that commit ran the old `python3 scripts/check_context.py` on a clean tree. It passed.
- Current commit: a clean clone of `HEAD` ran the new shim `python3 scripts/check_context.py`. It passed.

Steps to roll back:

1. Create a new branch. Do not work on `main`.
2. Choose one way:
   - Change the pin. Edit `scripts/controls-requirements.txt`. Put the earlier commit in the install line.
   - Or run `git revert` on the adoption commits.
3. Run `python3 scripts/check_context.py`. It must pass.

Files of the adoption:

- Added: `controls.toml`, `scripts/controls-requirements.txt`, `docs/controls-adoption.md`, `scripts/secret_guard.py` and its hooks (step `a00`).
- Changed: `scripts/check_context.py` (now a shim), `.github/workflows/context.yml` (new `controls` job), `Dockerfile` (builds the cache), `.dockerignore` (allows `controls.toml`), `AGENTS.md`, `docs/README.md`, `scripts/AGENTS.md`.
- Kept: `scripts/build_indexes.py`, `scripts/check_plan.py`, `scripts/check_links.py`, `scripts/scan_secrets.py`, `scripts/ctx_common.py`, `scripts/test_docker.sh`, the other old scripts, the CI jobs `check` and `docker`, and the tests.

The cache under `$XDG_CACHE_HOME/deterministic-controls/<commit>/` is safe to delete. The shim builds it again on the next run.

## Receipt

Command, run on 2026-11-24 (UTC) in a clean clone of `HEAD` under `.probe/`:

`python3 -m deterministic_controls adopt receipt --root <clean clone> --commit 3a2e9f3d95136958c54f73c831e84b971fc9a054`

```json
{
  "base_revision": "29f83a683f209ddeb21008f929b4ede40d7a47da",
  "checks_run": [
    {"check_id": "context.index-freshness", "status": "passed"},
    {"check_id": "markdown.local-links", "status": "passed"},
    {"check_id": "plans.graph", "status": "passed"},
    {"check_id": "plans.schema", "status": "passed"},
    {"check_id": "repo.forbidden-artifacts", "status": "passed"},
    {"check_id": "security.personal-data", "status": "passed"},
    {"check_id": "security.secrets", "status": "passed"}
  ],
  "commands_kept": [
    "scripts/build_context_indexes.py",
    "scripts/build_indexes.py",
    "scripts/check_links.py",
    "scripts/check_plan.py",
    "scripts/ctx_common.py",
    "scripts/scan_context_secrets.py",
    "scripts/scan_secrets.py",
    "scripts/test_docker.sh",
    "test: python3 -m unittest discover -s tests",
    "test: docker build (Dockerfile)",
    "ci-job: check",
    "ci-job: docker"
  ],
  "control_pin": "3a2e9f3d95136958c54f73c831e84b971fc9a054",
  "date": "2026-11-24",
  "enabled_checks": [
    "context.index-freshness",
    "markdown.local-links",
    "plans.graph",
    "plans.schema",
    "repo.forbidden-artifacts",
    "security.personal-data",
    "security.secrets"
  ],
  "enforcement_state": "advisory",
  "files_added": [],
  "files_changed": [],
  "profile": "ci",
  "repository": "clean",
  "rollback": [
    "To restore the previous pin: edit scripts/controls-requirements.txt, put the previous commit in the install line, and run scripts/check_context.py once to build its environment.",
    "To remove the adoption: run 'git revert' on the adoption commit, or restore the files from the base revision with 'git checkout <base> -- <file>' and delete the files that were added.",
    "The cached environment is in the user cache directory under deterministic-controls/<commit>/. It is safe to delete."
  ],
  "schema_version": 1
}
```

Notes:

- `repository` is the name of the temporary clone, not of this repository.
- `files_added` and `files_changed` are empty in a clean clone. This is a known library defect. The Rollback section lists the files of the adoption instead.
- `enforcement_state` is `advisory`. The `controls` CI job is not a required check.
- The `rollback` text is shortened here: the base revision and the long file list are removed.

## Secret guard exceptions

none
