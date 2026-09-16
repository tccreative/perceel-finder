#!/usr/bin/env bash
# Collect -> build docs/ -> push to GitHub Pages.
#   ./publish.sh            full run
#   ./publish.sh --skip-scrape   just rebuild docs/ and push
set -euo pipefail
cd "$(dirname "$0")"

PY=./.venv/bin/python
KEY=${DEPLOY_KEY:-/root/.ssh/perceel_finder_deploy}
export GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=no"

if [ "${1:-}" != "--skip-scrape" ]; then
  $PY update.py --images
fi

echo "building docs/"
rm -rf docs
mkdir -p docs/data docs/thumbs
cp web/index.html docs/index.html
cp data/listings.json docs/data/listings.json
[ -d web/thumbs ] && cp web/thumbs/*.webp docs/thumbs/ 2>/dev/null || true
touch docs/.nojekyll

echo "$(ls docs/thumbs | wc -l) thumbnails, $(du -sh docs | cut -f1) total"

git add -A
if git diff --cached --quiet; then
  echo "nothing changed"
else
  git commit -q -m "update: $(date -u +%Y-%m-%d) — $($PY -c "import json;d=json.load(open('data/listings.json'));c=d['counts'];print(f\"{c['active']} plots, {c['in_target_area']} in Pbo/Wanica, {c['new_this_run']} new\")")"
  git push -q origin main
  echo "pushed"
fi
