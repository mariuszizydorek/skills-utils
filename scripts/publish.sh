#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_DIR="$ROOT/python"
VENV_PYTHON="$PYTHON_DIR/.venv/bin/python"

if [[ -x "$VENV_PYTHON" ]]; then
  PYTHON="$VENV_PYTHON"
else
  PYTHON="python3"
  if ! "$PYTHON" -c "import build" 2>/dev/null; then
    echo "==> Installing build into user site-packages"
    PIP_INDEX_URL=https://pypi.org/simple/ "$PYTHON" -m pip install --user build
  fi
fi

echo "==> Building Python package (skills-utils-mi)"
cd "$PYTHON_DIR"
PIP_INDEX_URL=https://pypi.org/simple/ "$PYTHON" -m build

echo "==> Building Node package (skills-sync-node-mi)"
cd "$ROOT/node"
npm run build

echo
echo "Ready to publish. Run:"
echo "  cd $PYTHON_DIR && twine upload dist/skills_utils_mi-*.whl dist/skills_utils_mi-*.tar.gz"
echo "  cd $ROOT/node && npm publish --access public"
