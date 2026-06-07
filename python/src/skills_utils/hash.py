from __future__ import annotations

import hashlib
import json
from pathlib import Path

IGNORE_PARTS = {".git", "__pycache__", ".DS_Store"}


def _should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return any(part in IGNORE_PARTS for part in rel.parts)


def file_map(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    mapping: dict[str, str] = {}
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file() or _should_skip(file_path, root):
            continue
        rel = file_path.relative_to(root).as_posix()
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        mapping[rel] = digest
    return mapping


def hash_from_map(mapping: dict[str, str]) -> str:
    payload = json.dumps(mapping, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"sha256:{digest}"


def dir_hash(root: Path) -> str:
    return hash_from_map(file_map(root))


def remote_fingerprint(blob_map: dict[str, str]) -> str:
    return hash_from_map(blob_map)
