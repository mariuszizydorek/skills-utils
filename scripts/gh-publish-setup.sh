#!/usr/bin/env bash
# One-time setup + first release via GitHub Actions.
# Run from repo root after committing workflow files.
set -euo pipefail

REPO="mariuszizydorek/skills-utils"
VERSION="${1:-v0.1.0}"

echo "==> 1. Ensure gh is logged in as repo owner with workflow scope"
ACTIVE_USER="$(gh api user -q .login 2>/dev/null || true)"
if [[ "$ACTIVE_USER" != "mariuszizydorek" ]]; then
  echo "    Switching active gh account to mariuszizydorek"
  gh auth switch -u mariuszizydorek
else
  echo "    Active account already mariuszizydorek"
fi

AUTH_STATUS="$(gh auth status -h github.com 2>&1 || true)"
if grep -q "Token scopes:.*repo" <<<"$AUTH_STATUS" && grep -q "Token scopes:.*workflow" <<<"$AUTH_STATUS"; then
  echo "    Required gh scopes already present (repo, workflow)"
else
  echo "    Refreshing gh token scopes (repo, workflow)"
  gh auth refresh -h github.com -s workflow,repo
fi

echo "==> 2. Push main (HTTPS via gh credentials)"
git remote set-url origin "https://github.com/${REPO}.git"
gh auth setup-git
git push origin main

echo "==> 3. Create pypi environment (no-op if exists)"
gh api "repos/${REPO}/environments/pypi" -X PUT --input - <<'JSON' || true
{"wait_timer": 0}
JSON

echo "==> 4. Configure npm Trusted Publishing (manual, one-time)"
cat <<'EOF'

Open npm package settings for skills-sync-node-mi and add trusted publisher:
  https://www.npmjs.com/package/skills-sync-node-mi

Trusted publisher values:
  Provider:  GitHub Actions
  Owner:     mariuszizydorek
  Repository: skills-utils
  Workflow:  publish.yml

If package does not exist yet, do one manual bootstrap publish first:
  cd node
  npm login
  npm publish --access public

Then return and configure trusted publisher.

EOF
read -r -p "Press Enter after npm trusted publisher is saved…"

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
