---
id: a01-audit
status: pending
depends_on: [a00-secret-guard]
touches:
  - docs/controls-audit.json
  - plans/adopt-controls/steps/a01-audit.md
lane: none
agent: script
run: python3 -m deterministic_controls adopt audit --root . --format json > docs/controls-audit.json
gate: python3 -c 'import json; d = json.load(open("docs/controls-audit.json")); assert "schema_version" in d and d["classification"] != "blocked", d.get("classification")' && python3 scripts/secret_guard.py --tracked && git diff --check
requirements: [R2]
claimed_by: ""
claimed_at: ""
evidence: ""
---

# Audit the repository with the pinned library

This is a `script` step. The driver runs `run:` and then the gate. No model works on it.

## Change

- `docs/controls-audit.json`: the output of `adopt audit` for this repository, as JSON.

The operator puts the pinned library release on `PYTHONPATH` before the wave, so `python3 -m deterministic_controls` works here.

## Do not change

- Files outside `touches`. The `gate` command. The `run:` command.

## Done when

- The JSON parses, has `schema_version`, and the classification is not `blocked`. A `blocked` result stops the plan for review.

## Record

The driver sets `status: done` and writes `evidence` when the gate passes.
If the step fails, write the cause under "Resume notes". Keep the status `in_progress`.

## Resume notes

(none)
