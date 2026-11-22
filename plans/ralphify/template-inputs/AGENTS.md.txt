# Agent contract

This repository is `repo-template`. It is the template for all new repositories.
Create a new repository from it. Do not build products in it.

<!-- TEMPLATE-ONLY START: delete this section in every repository created from this template. -->
## Template-only rules

- This repository defines the standard layout, rules and scripts. Other repositories copy them.
- Keep it generic. Do not add project names, personal paths, hosts or user names.
- The files `scripts/hello-listing.sh`, `scripts/hello-listing.ps1` and `memory/example-memory.md` are examples. Delete them in new repositories.
- After you create a new repository from the template:
  1. Replace the first paragraph of this file with one or two sentences about the new project.
  2. Delete this section.
  3. Delete the `Dockerfile` if the project is only for Windows. Add Windows Sandbox instructions to `docs/` instead.
  4. Update `README.md` and `LICENSE`.
  5. Run `python3 scripts/build_indexes.py`.
<!-- TEMPLATE-ONLY END -->

## Standing rules

1. **No private data in tracked files.** Never put PII, secrets, keys, tokens, passwords, personal paths or private host names in a file that Git tracks. This includes memory, plans, docs, logs and examples. Use placeholders. Keep working files outside the repository (see `~/repo-work` below).
2. **Start all work on a branch.** Never commit to `main` directly. This applies in a Git worktree too. A worktree does not replace a branch: create the branch first, or create the worktree with a new branch (`git worktree add -b <branch> <path>`).
3. **Write documents in Simplified Technical English** (ASD-STE100), or close to it. Use short sentences, one idea in each, active voice, simple words and consistent terms. The readers are technical and worldwide. Many do not read English as a first language. This rule applies to all Markdown and other English text.
4. **Do not push, publish or force-push** without authorization from the user.
5. User instructions come first. If sources conflict, use this order: user, this file, the named plan, `docs/`, `memory/`, code and tests, old notes.

## Directory structure

Every repository has these directories. Add other directories when the project needs them.

| Path | Purpose | Index |
| --- | --- | --- |
| `docs/` | Documents for humans: design, references, guides. | `docs/README.md` (edit by hand) |
| `memory/` | Facts for agents that cost time to find. One file for each fact. | `memory/AGENTS.md` (generated) |
| `plans/` | Work plans. One folder for each plan. | `plans/AGENTS.md` (generated) |
| `scripts/` | Scripts for agents and CI: run, test, debug, build. | `scripts/AGENTS.md` (generated) |

### How to load context

1. Read this file.
2. Read `memory/AGENTS.md`, `plans/AGENTS.md` and `scripts/AGENTS.md`.
3. Open only the files whose "Read me when" or "Run me when" line matches your task.
4. Stop when you know the decision, the files, the limits and how to verify.

### memory/

- One memory in one file. Several agents can write at the same time without a lock.
- Edit the file that exists for a topic. Do not add a second file for the same topic.
- Each file starts with front matter that has a `gist` key:

  ```yaml
  ---
  gist: "Read me when: <the situation in which an agent needs this file>"
  ---
  ```

- Never write PII, secrets or personal paths in a memory.
- `memory/AGENTS.md` is generated. Do not edit the part between the markers.

### plans/

- A plan is a folder `plans/<plan-name>/`. Copy `plans/for-each-plan/` to start one.
- `goal.md`: the goal, and the Ralph loop prompt near the top.
- `plan.md`: the high-level plan. It has a `gist` front-matter key.
- `steps/`: one Markdown file for each step. A step is small enough for a small model or agent to implement, test and verify alone.
- A step file has front matter: `id`, `status`, `depends_on`, `touches`, `lane`, `gate`. A step is done only when its `evidence` is recorded.
- Run each plan in its own Git worktree. Give each step its own worktree and branch where steps can run in parallel. Steps that run at the same time must not touch the same files.
- The plan must work if an agent stops at any time (for example, no token budget). Another agent must be able to continue from the files in the repository alone. Record progress in the step files, not in chat.
- Runtime output (logs, usage records, locks) goes outside the repository: `~/repo-work/<repo>/<plan>/` (`%USERPROFILE%\repo-work\<repo>\<plan>\` on Windows). Never track it.
- `plans/AGENTS.md` is generated.

### scripts/

- Scripts are deterministic. They are for agents and CI. CI scripts start here.
- Each script starts with a comment block that contains a line `Run me when: <situation>`.
- `scripts/AGENTS.md` is generated from those lines.

### Generated indexes

Run `python3 scripts/build_indexes.py` after any change to a memory, a plan or a script. CI runs the same script with `--check` and fails if an index is stale. Run `python3 scripts/check_context.py` to run all checks.

## Validation

Run the smallest check that proves your change. For any change to Markdown, memory, plans or scripts, run `python3 scripts/check_context.py`.
