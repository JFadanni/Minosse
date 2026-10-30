#!/bin/bash
# Build the simulated Minosse server and run the test suite inside it.
#
#   Tests/run_tests.sh [pytest args]   run the tests (e.g. -k daemon -x)
#   Tests/run_tests.sh shell           open a root shell on the server
set -euo pipefail

tests=$(cd "$(dirname "$0")" && pwd)
src=$(dirname "$tests")
image=minosse-server
# podman by default; CONTAINER_ENGINE=docker works too.
engine=${CONTAINER_ENGINE:-podman}

"$engine" build -q -t "$image" -f "$tests/container/Containerfile" \
    "$tests/container" > /dev/null

# --init reaps orphaned job processes, as init would on a real server.
run=("$engine" run --rm --init --hostname minosse-node
     --tmpfs /scratch:size=2g -v "$src:/src:ro,Z")

if [[ "${1:-}" == shell ]]; then
    exec "${run[@]}" -it "$image" bash
fi
exec "${run[@]}" "$image" python3 -m pytest -p no:cacheprovider /src/Tests "$@"
