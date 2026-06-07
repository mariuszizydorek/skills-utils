#!/usr/bin/env bash
# One-time setup + first release via GitHub Actions.
# Run from repo root after committing workflow files.
set -euo pipefail

REPO="mariuszizydorek/skills-utils"
VERSION="${1:-v0.1.0}"

echo "==> 1. Ensure gh is logged in as repo owner with workflow scope"
gh auth switch -u mariuszizydorek
gh auth refresh -h github.com -s workflow,repo

echo "==> 2. Push main (HTTPS via gh credentials)"
git remote set-url origin "https://github.com/${REPO}.git"
gh auth setup-git
git push origin main

echo "==> 3. Create pypi environment (no-op if exists)"
gh api "repos/${REPO}/environments/pypi" -X PUT --input - <<'JSON' || true
{"wait_timer": 0}
JSON

echo "==> 4. Set npm publish token (paste token when prompted)"
echo "    Create at: https://www.npmjs.com/settings/~/tokens (Automation, publish)"
if ! gh secret list | grep -q '^NPM_TOKEN'; then
  gh secret set NPM_TOKEN
else
  echo "    NPM_TOKEN already set — skip or run: gh secret set NPM_TOKEN"
fi

echo "==> 5. Configure PyPI trusted publisher (manual, one-time)"
cat <<'EOF'

Open https://pypi.org/manage/account/publishing/
Add trusted publisher:
  Owner:       mariuszizydorek
  Repository:  skills-utils
  Workflow:    publish.yml
  Environment: pypi
  Project:     skills-utils-mi

EOF
read -r -p "Press Enter after PyPI trusted publisher is saved…"

echo "==> 6. Create GitHub release (triggers publish workflow)"
gh release create "$VERSION" \
  --repo "$REPO" \
  --title "$VERSION" \
  --generate-notes

echo
echo "Watch progress:"
echo "  gh run list --repo $REPO --workflow publish.yml"
echo
echo "After success, install with:"
echo "  pip install skills-utils-mi"
echo "  npm install -g skills-sync-node-mi"
