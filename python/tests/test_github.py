import pytest

from skills_utils.github import GitHubClient
from skills_utils.repos import fetch_remote_inventory, repo_from_config


@pytest.mark.integration
def test_fetch_anthropics_skills_inventory():
    repo = repo_from_config(
        "anthropics",
        {
            "owner": "anthropics",
            "repo": "skills",
            "branch": "main",
            "skills_path": "skills",
        },
    )
    with GitHubClient() as client:
        commit_sha, inventory = fetch_remote_inventory(client, repo)
    assert commit_sha
    assert "pdf" in inventory
    assert "SKILL.md" in inventory["pdf"].files
    assert inventory["pdf"].fingerprint.startswith("sha256:")
