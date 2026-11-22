---
id: 01-adopt-context
status: pending
depends_on: []
touches:
  - AGENTS.md
  - CLAUDE.md
  - docs/README.md
  - memory/README.md
  - memory/AGENTS.md
  - plans/AGENTS.md
  - plans/TEMPLATE/**
  - plans/for-each-plan/**
  - plans/archive/legacy-template/**
  - .github/workflows/context.yml
  - scripts/README.md
  - scripts/AGENTS.md
  - scripts/build_indexes.py
  - scripts/build_context_indexes.py
  - scripts/check_context.py
  - scripts/check_links.py
  - scripts/check_plan.py
  - scripts/ctx_common.py
  - scripts/scan_context_secrets.py
  - scripts/scan_secrets.py
  - plans/ralphify/steps/01-adopt-context.md
lane: none
requirements: [R1]
gate: python3 scripts/build_indexes.py --check && python3 scripts/check_context.py && git diff --check
evidence: ""
---

# 01-adopt-context

Depends on no step. Carry forward the project description, existing local rules, and context ownership. Keep `CLAUDE.md` as a pointer to the root contract. Put this rule in `AGENTS.md`, with links to both upstream repositories:

> Before changing this repository's structure, read `repo-template` and `ralph-looper`. Account for their layout, plan format, generated indexes, worktree rules, and validation commands in the change.

Adopt `docs/README.md`, `memory/AGENTS.md`, `plans/AGENTS.md`, `scripts/AGENTS.md`, and `plans/for-each-plan/`. Preserve any existing docs and archive references. Move the old `plans/TEMPLATE/` out of the active plan namespace and repair references. Keep archived plans readable without rewriting their evidence. Adapt and reuse existing checker logic where it preserves coverage. Provide `scripts/build_indexes.py` and `scripts/check_context.py`. Preserve compatibility for documented checker commands and repository-specific checks. Add or adapt `.github/workflows/context.yml` for the actual base branch and preserve existing workflows. Regenerate indexes. Resolve any local links that would fail from a standalone checkout.

Touches the agent contracts, the relevant index and checker files, current plan templates, references to the old layout, `.github/workflows/context.yml`, and this step file. Review the exact layout diff and test that broken links, stale indexes, malformed active plans, and the existing secret scan still fail their checks. Gate: `python3 scripts/build_indexes.py --check && python3 scripts/check_context.py && git diff --check`.

Use `main` as the workflow base branch. Copy the pinned inputs from `plans/ralphify/template-inputs/`. Remove the final `.txt` suffix on copy.
