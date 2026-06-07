#!/usr/bin/env bash
# Bump version in both python/pyproject.toml and node/package.json in lockstep.
# Usage: ./scripts/bump-version.sh 0.2.0
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <X.Y.Z>" >&2
  exit 2
fi

VERSION="${1#v}"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "Version '$VERSION' is not valid semver (expected X.Y.Z)." >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

python3 - "$ROOT/python/pyproject.toml" "$VERSION" <<'PY'
import re, sys, pathlib
path, version = pathlib.Path(sys.argv[1]), sys.argv[2]
text = path.read_text()
new, count = re.subn(r'(?m)^version = "[^"]+"', f'version = "{version}"', text, count=1)
if count == 0:
    raise SystemExit(f"No version line found in {path}")
path.write_text(new)
print(f"  {path}: version = \"{version}\"")
PY

(cd "$ROOT/node" && npm version --no-git-tag-version --allow-same-version "$VERSION" >/dev/null)
echo "  $ROOT/node/package.json: version = \"$VERSION\""

echo
echo "Next:"
echo "  git add python/pyproject.toml node/package.json node/package-lock.json"
echo "  git commit -m \"chore: bump to v$VERSION\""
echo "  git tag v$VERSION && git push origin main v$VERSION"
echo "  gh release create v$VERSION --generate-notes"
