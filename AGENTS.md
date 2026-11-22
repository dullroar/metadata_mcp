# Agent contract

A FastMCP layer over established metadata engines (ExifTool, mutagen, Pandoc) and lightweight local probes.

## Standing rules

- Use a branch for all work. Do not commit directly to `main`.
- Write documents in Simplified Technical English. Use short sentences, active voice, and consistent terms.
- Do not commit credentials, personal data, personal filesystem paths, private host names, or sensitive record-level examples. Use placeholders and aggregate evidence.
- Do not push, publish, force-push, or add a remote without authorization.

Before changing this repository's structure, read [repo-template][repo-template] and
[ralph-looper][ralph-looper]. Account for their layout, plan format, generated indexes, worktree
rules, and validation commands in the change.

[repo-template]: https://github.com/dullroar/repo-template
[ralph-looper]: https://github.com/dullroar/ralph-looper

## Load context in this order

1. Read this file.
2. Read the short indexes in full. See [README.md](./README.md), [docs/README.md](./docs/README.md),
   [memory/AGENTS.md](./memory/AGENTS.md), [plans/AGENTS.md](./plans/AGENTS.md), and
   [scripts/AGENTS.md](./scripts/AGENTS.md).
3. Open only the documents with a **Read when**, **Read me when**, or **Run me when** line that matches
   the task. For a large file, find the headings and read only the relevant sections.
4. Stop when you know the decision, intended files, constraints, and validation method.

When sources conflict, use this order. User instructions come first, then this file, `docs/design/`,
the named plan, domain documentation and references, `memory/`, implementation and tests, and
historical notes.

## Context ownership

- Universal rules belong here.
- Architectural reasons belong in `docs/design/`. Record one premise per file.
- Findings that cost time to discover belong in `memory/`. Update the existing topic when it fits.
- Execution state belongs in `plans/`. Deterministic automation belongs in `scripts/`.
- Start each routed Markdown file with `gist: "Read when: ..."` or `gist: "Read me when: ..."` front matter.
- Correct a fact in its source. Keep one source for each fact.

## Planned work

- Work only on a named plan or an explicitly identified off-plan task. Copy
  [plans/for-each-plan/](./plans/for-each-plan/) to start a plan. Keep the goal and loop prompt in
  `goal.md`, the approach in `plan.md`, the requirements in `spec.md`, and execution details in `steps/`.
- Once the spec is approved, proceed through the steps. Diagnose and fix failures within scope.
  Ask the user to resolve contradictory requirements, scope changes, or actions outside the spec's
  delegated authority.
- Keep protected acceptance checks intact. If a check cannot pass as written, report the blocker.
- Run the plan in its own worktree and branch. Give parallel steps separate worktrees and branches.
  Run steps in parallel only when neither depends on the other and their `touches` do not overlap.
  If independence is uncertain, run the steps in order. Run the spec's combined checks after merging
  parallel steps.
- Record evidence before marking a step done. Report unavailable verification. Record progress in
  the step file so another agent can resume. Keep logs, usage records, and locks outside the repo,
  under `~/repo-work/<repo>/<plan>/` or `%USERPROFILE%\repo-work\<repo>\<plan>\`.
- Record separately whether a rule was retired, its documentation was corrected, or a known
  violation was accepted. See the [spec template](./plans/for-each-plan/spec.md#exceptions-and-retirements).

## Validation

Run the smallest check that proves the change. Regenerate indexes with
`python3 scripts/build_indexes.py` after changing a routed file. Use
`python3 scripts/build_indexes.py --check` to verify the generated sections.
Run `python3 scripts/check_context.py` for any context change.
