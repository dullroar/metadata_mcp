# metadata_mcp migration requirements

## R1 Adopt the shared repository layout

Update the agent contracts, context indexes, template, checks and workflow. Preserve project rules and historical evidence. Include both upstream links and require future structure changes to account for the template and runner.

## R2 Build and test in Docker

Add a Dockerfile and a repeatable Docker test entry point. Use the existing test suite and the required repo-specific checks. Give readers exact build, test and Ralph commands in the README.

## R3 Verify the combined result

Verify context and Docker on the integrated branch. Record commands, observed results, expected skips, and the UTC date. Leave the final plan branch ready for review.
