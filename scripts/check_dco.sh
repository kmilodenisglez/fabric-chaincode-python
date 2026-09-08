#!/usr/bin/env bash
set -euo pipefail

# Check that all commits in the current range have a Signed-off-by trailer.
# In CI, GitHub provides the commits in the PR; for local checks this will inspect HEAD.

missing=0

# If no range provided, check the last commit
range="${1:-HEAD}"

for sha in $(git rev-list --reverse "$range"); do
  if ! git show --no-patch --format=%B "$sha" | grep -q "Signed-off-by:"; then
    echo "Commit $sha is missing Signed-off-by:" >&2
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "DCO check failed: one or more commits are missing Signed-off-by:" >&2
  exit 1
fi

echo "DCO check passed"
