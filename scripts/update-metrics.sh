#!/bin/sh
set -eu

ROOT=/opt/repos/github-profile
LOCK=/tmp/breeze-github-profile.lock

exec 9>"$LOCK"
flock -n 9 || exit 0
cd "$ROOT"

# This job must never publish work from a feature branch or a dirty checkout.
if [ "$(git branch --show-current)" != "main" ] || [ -n "$(git status --porcelain)" ]; then
  echo "Profile refresh skipped: expected a clean main checkout" >&2
  exit 1
fi

git fetch -q origin main
git merge --ff-only -q origin/main
python3 -B scripts/render_metrics.py

# Avoid a new commit unless the public counters actually changed.
if git diff --quiet -- github-metrics.svg; then
  exit 0
fi
git add -- github-metrics.svg
git commit -m "Update public GitHub metrics"
git push origin main
