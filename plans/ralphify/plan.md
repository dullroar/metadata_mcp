---
gist: "Read me when: you are bringing this repository onto the template or reproducing its Docker test."
---

# Ralphify metadata_mcp

The target base branch is `main`. This plan uses three steps. The context step updates the agent entry points and checks. The Docker step adds an image and a project test entry point. The verification step reruns the checks on the combined result and records the evidence.

The reference inputs in `plans/ralphify/template-inputs/` come from [repo-template](https://github.com/dullroar/repo-template) at revision `126277f5b34027bc3766b4ae0804746f90dce959`. Each reference file has an added `.txt` suffix. Use the reference as a guide and preserve existing project rules. The resulting checks and tests must run from this repository alone.

| Step | Goal | Depends on |
| --- | --- | --- |
| [01-adopt-context](./steps/01-adopt-context.md) | Adopt the template context layout. | None |
| [02-build-and-test](./steps/02-build-and-test.md) | Build and test this repository in Docker. | 01 |
| [03-verify-integration](./steps/03-verify-integration.md) | Verify the combined result. | 02 |

See the [requirement record](./spec.md). Keep the base branch available for the owner's review.
