# Manifest and hash schema

Both Python and Node implementations must produce identical values.

## Directory content hash (`installed_hash`)

1. Walk all files under the skill directory recursively.
2. Skip paths containing: `.git`, `__pycache__`, `.DS_Store`
3. Build map `{relative_posix_path: sha256_hex_of_file_bytes}` sorted by key.
4. `installed_hash = "sha256:" + sha256(json.dumps(map, sort_keys=True, separators=(",", ":")))`

## Remote fingerprint (`remote_fingerprint`)

1. From Git tree API, collect blob SHAs for paths under `skills/{skill_name}/`.
2. Keys are paths relative to the skill folder (e.g. `SKILL.md`, `scripts/foo.py`).
3. Build map `{relative_path: blob_sha}` sorted by key.
4. `remote_fingerprint = "sha256:" + sha256(json.dumps(map, sort_keys=True, separators=(",", ":")))`

## Manifest format

```json
{
  "version": 1,
  "agents": {
    "<agent_id>": {
      "<repo_slug>/<skill_name>": {
        "repo_slug": "anthropics",
        "remote_path": "skills/pdf",
        "commit_sha": "abc123",
        "remote_fingerprint": "sha256:...",
        "installed_hash": "sha256:...",
        "installed_at": "2026-06-07T12:00:00Z"
      }
    }
  }
}
```

## Skill status

| Status | Condition |
|--------|-----------|
| `missing` | Not installed locally |
| `synced` | Local hash matches remote fingerprint and manifest |
| `outdated` | Remote fingerprint differs from manifest |
| `modified` | Local hash differs from manifest installed_hash |
| `diverged` | Both outdated and modified |
