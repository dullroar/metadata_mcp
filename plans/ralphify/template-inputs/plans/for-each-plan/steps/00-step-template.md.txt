---
id: 00-step-template
status: pending
depends_on: []
touches:
  - path/or/glob/this/step/will/change
lane: none
gate: exact command that proves this step is complete
claimed_by: ""
claimed_at: ""
evidence: ""
---

# <One sentence: the goal of this step>

Write for an agent that has no chat history. Size the step so that a small model can do it.

## Change

- `path`: the change to make.

## Do not change

- Files outside `touches`. The `gate` command.

## Already done by earlier steps

- <step id: what it gives you>

## Done when

- <An observable result.>

## Record

Set `status: done`. Fill `evidence` with the gate command, the result and the date.
If you cannot finish, write "Resume notes" below. Keep the status `in_progress`.

## Resume notes

(none)
