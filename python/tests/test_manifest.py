import json
from pathlib import Path

import pytest

from skills_utils.config_loader import load_manifest, save_manifest
from skills_utils.hash import dir_hash


def test_manifest_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    from skills_utils import config_loader

    monkeypatch.setattr(config_loader, "home_dir", lambda: home / ".skills-utils")

    data = {
        "version": 1,
        "agents": {
            "cursor": {
                "anthropics/pdf": {
                    "repo_slug": "anthropics",
                    "remote_path": "skills/pdf",
                    "commit_sha": "abc",
                    "remote_fingerprint": "sha256:123",
                    "installed_hash": "sha256:456",
                    "installed_at": "2026-06-07T12:00:00+00:00",
                }
            }
        },
    }
    save_manifest(data)
    loaded = load_manifest()
    assert loaded["agents"]["cursor"]["anthropics/pdf"]["repo_slug"] == "anthropics"
