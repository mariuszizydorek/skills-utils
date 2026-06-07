from pathlib import Path

import pytest

from skills_utils.agents import resolve_skills_dir
from skills_utils.config_loader import load_manifest, save_manifest
from skills_utils.github import GitHubClient
from skills_utils.repos import fetch_remote_inventory, repo_from_config
from skills_utils.sync import apply_sync


@pytest.mark.integration
def test_install_skill_to_temp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    skills_dir = home / ".cursor" / "skills"
    monkeypatch.setenv("HOME", str(home))

    from skills_utils import config_loader

    monkeypatch.setattr(config_loader, "home_dir", lambda: home / ".skills-utils")

    config = {
        "repos": {
            "anthropics": {
                "owner": "anthropics",
                "repo": "skills",
                "branch": "main",
                "skills_path": "skills",
            }
        },
        "agents": {
            "cursor": {
                "label": "Cursor",
                "skills_dir": str(skills_dir),
                "scope": "user",
            }
        },
        "defaults": {"flat_symlinks": True},
    }
    agent = config["agents"]["cursor"]
    repo = repo_from_config("anthropics", config["repos"]["anthropics"])
    manifest = {"version": 1, "agents": {}}

    with GitHubClient() as client:
        commit_sha, inventory = fetch_remote_inventory(client, repo)
        result = apply_sync(
            client,
            repo,
            "cursor",
            agent,
            manifest,
            inventory,
            commit_sha,
            selected={"theme-factory"},
            to_update=set(),
            flat_symlinks=True,
            skills_dir=skills_dir,
        )

    assert result.installed == ["theme-factory"]
    installed_path = skills_dir / "anthropics" / "theme-factory" / "SKILL.md"
    assert installed_path.exists()
    save_manifest(manifest)
    loaded = load_manifest()
    assert "anthropics/theme-factory" in loaded["agents"]["cursor"]
