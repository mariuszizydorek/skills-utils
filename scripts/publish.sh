#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Building Python package (skills-sync)"
cd "$ROOT/python"
PIP_INDEX_URL=https://pypi.org/simple/ python3 -m build

echo "==> Building Node package (skills-sync-node)"
cd "$ROOT/node"
npm run build

echo
echo "Ready to publish. Run:"
echo "  cd $ROOT/python && twine upload dist/skills_sync-*.whl dist/skills_sync-*.tar.gz"
echo "  cd $ROOT/node && npm publish --access public"
