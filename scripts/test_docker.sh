#!/usr/bin/env bash
# Run me when: I need to build the image and run the project and context checks in Docker.
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/metadata-mcp-test.XXXXXXXX")
run_id=${run_dir##*.}
image="metadata-mcp-test:${run_id,,}"
container="metadata-mcp-test-${run_id}"

cleanup() {
    docker image rm "$image" >/dev/null 2>&1 || true
    rmdir -- "$run_dir"
}
trap cleanup EXIT

docker build --tag "$image" .
docker run --rm --name "$container" --network none --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,mode=1777 "$image" bash -ec '
        python3 -m unittest discover -s tests -v
        python3 tests/smoke_stdio.py
        python3 scripts/check_context.py
    '
