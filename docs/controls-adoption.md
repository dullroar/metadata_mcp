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

## Secret guard exceptions

none
