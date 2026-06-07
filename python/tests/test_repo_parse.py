import pytest

from skills_utils.repo_parse import default_repo_slug, parse_github_repo


@pytest.mark.parametrize(
    ("owner", "repo", "expected"),
    [
        ("vercel-labs", "agent-skills", ("vercel-labs", "agent-skills")),
        ("", "https://github.com/vercel-labs/agent-skills", ("vercel-labs", "agent-skills")),
        ("https://github.com/vercel-labs/agent-skills", "", ("vercel-labs", "agent-skills")),
        ("vercel-labs/agent-skills", "", ("vercel-labs", "agent-skills")),
        ("anthropics", "skills", ("anthropics", "skills")),
    ],
)
def test_parse_github_repo(owner, repo, expected):
    assert parse_github_repo(owner, repo) == expected


def test_default_repo_slug():
    assert default_repo_slug("vercel-labs", "agent-skills") == "vercel-labs"
    assert default_repo_slug("myuser", "my-custom-skills") == "my-custom-skills"
