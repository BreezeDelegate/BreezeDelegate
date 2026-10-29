#!/bin/sh
set -eu
ROOT=/opt/repos/github-profile
LOCK=/tmp/breeze-github-profile.lock
exec 9>"$LOCK"
flock -n 9 || exit 0
cd "$ROOT"
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  git fetch -q origin main
  git merge --ff-only -q origin/main
fi
python3 scripts/render_metrics.py
if git rev-parse --verify HEAD >/dev/null 2>&1 && git diff --quiet -- github-metrics.svg; then
  exit 0
fi
git add github-metrics.svg
git commit -m 'Refresh GitHub metrics'
git push origin main
