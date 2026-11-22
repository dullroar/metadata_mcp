# Goal: <plan name>

## Ralph loop prompt

Use this prompt for each loop iteration. It has no chat history, so keep it complete.

> You work on plan `<plan-name>` in this repository. Read `AGENTS.md`, then `plans/<plan-name>/goal.md` and `plan.md`.
> Open the step file you were given. Work only in the worktree you were given, on its branch.
> Do only that step. Change only the files in `touches`.
> Run the `gate` command. If it fails, find the cause and fix it. Do not weaken or delete the gate.
> When the gate passes, set `status: done` and write `evidence` (command, result, date). Commit.
> If you cannot finish, keep `status: in_progress`, write what remains under "Resume notes" in the step file, and commit.
> If you are blocked, set `status: blocked` and write the reason. Do not guess.
> Never write secrets or personal data in any file. Write in Simplified Technical English.

## Goal

State the goal in one paragraph. Say what is true when the plan is done.

## Done when

- <An observable result that you can check with a command.>

## Out of scope

- <What this plan does not do.>
