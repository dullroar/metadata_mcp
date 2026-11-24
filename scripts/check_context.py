#!/usr/bin/env python3
"""Run every context check through deterministic-controls. Usage: check_context.py [ROOT]

Run me when: I changed any context file, and before every pull request.

deterministic-controls shim. It keeps the output lines and exit codes of the old template script:
one line "ok   <script>" or "FAIL <script>" for each old check, exit 0 if all pass, exit 1 if a check fails.
It runs the library from a cached virtual environment for the pinned commit.
Cache: $XDG_CACHE_HOME/deterministic-controls/<commit>/ (default ~/.cache/deterministic-controls/<commit>/).
The first run needs the network. If the library cannot run, this script exits 2. It never passes then.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REQUIREMENTS = HERE / "controls-requirements.txt"
GROUPS = [
    ("build_indexes.py", ["context.index-freshness"]),
    ("check_plan.py", ["plans.schema", "plans.graph"]),
    ("check_links.py", ["markdown.local-links"]),
    ("scan_secrets.py", ["security.secrets", "security.personal-data"]),
]
EXIT_CONFIG = 2


def fail(message: str) -> int:
    print(f"check_context: {message}", file=sys.stderr)
    return EXIT_CONFIG


def pinned() -> tuple[str, str]:
    """Return (install line, commit) from the requirements file."""
    if not REQUIREMENTS.is_file():
        raise RuntimeError(f"{REQUIREMENTS.name} is missing")
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        match = re.search(r'"deterministic-controls @ git\+\S+@([0-9a-f]{40})"', line)
        if match:
            spec = re.search(r'"([^"]+)"', line)
            assert spec
            return spec.group(1), match.group(1)
    raise RuntimeError(f"{REQUIREMENTS.name} has no pinned install line with a full commit")


def cache_dir(commit: str) -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "deterministic-controls" / commit


def venv_python(venv: Path) -> Path:
    unix = venv / "bin" / "python"
    return unix if unix.exists() else venv / "Scripts" / "python.exe"


def ensure_environment(spec: str, commit: str) -> Path:
    target = cache_dir(commit)
    venv = target / "venv"
    if (target / "ready").is_file() and venv_python(venv).exists():
        return venv_python(venv)
    target.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".build-", dir=target.parent))
    try:
        subprocess.run([sys.executable, "-m", "venv", str(work / "venv")], check=True, capture_output=True)
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        subprocess.run(
            [str(venv_python(work / "venv")), "-m", "pip", "install", "--retries", "1", "--timeout", "20", spec],
            check=True, capture_output=True, env=env,
        )
        (work / "ready").write_text(commit + "\n", encoding="utf-8")
        if target.exists():
            shutil.rmtree(target)
        work.rename(target)
    except (OSError, subprocess.SubprocessError) as exc:
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError(f"cannot create the environment for commit {commit} (network needed once): {type(exc).__name__}") from exc
    return venv_python(target / "venv")


def main(argv: list[str]) -> int:
    root = Path(argv[0]) if argv else HERE.parent
    try:
        spec, commit = pinned()
        python = ensure_environment(spec, commit)
    except RuntimeError as exc:
        return fail(str(exc))
    try:
        proc = subprocess.run(
            [str(python), "-m", "deterministic_controls", "check", "--root", str(root), "--profile", "ci", "--format", "json"],
            capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        return fail(f"cannot run the library: {type(exc).__name__}")
    if proc.returncode not in (0, 1):
        sys.stderr.write(proc.stderr)
        return fail(f"the library failed with exit code {proc.returncode}")
    try:
        status = {c["check_id"]: c["status"] for c in json.loads(proc.stdout)["checks"]}
    except (ValueError, KeyError, TypeError):
        return fail("the library gave no valid result")
    failed = False
    seen: set[str] = set()
    for script, ids in GROUPS:
        present = [i for i in ids if i in status]
        if not present:
            continue
        seen.update(present)
        ok = all(status[i] in ("passed",) for i in present)
        failed |= not ok
        print(f"{'ok  ' if ok else 'FAIL'} {script}")
    for check_id in sorted(set(status) - seen):
        ok = status[check_id] == "passed"
        failed |= not ok
        print(f"{'ok  ' if ok else 'FAIL'} {check_id}")
    if proc.returncode == 1 and not failed:
        print("FAIL deterministic-controls")
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
