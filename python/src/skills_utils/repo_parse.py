from __future__ import annotations

import re

_GITHUB_URL = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/#?]+)",
    re.IGNORECASE,
)


def parse_github_repo(owner: str, repo: str) -> tuple[str, str]:
    """Normalize owner/repo from plain names, owner/repo strings, or GitHub URLs."""
    owner = (owner or "").strip()
    repo = (repo or "").strip()

    for candidate in (repo, owner, f"{owner}/{repo}".strip("/")):
        if not candidate:
            continue
        match = _GITHUB_URL.search(candidate)
        if match:
            return match.group(1), match.group(2).removesuffix(".git")

    if "/" in owner and not repo:
        parts = owner.strip("/").split("/", 1)
        return parts[0], parts[1].removesuffix(".git")

    if "/" in repo and not owner:
        parts = repo.strip("/").split("/", 1)
        return parts[0], parts[1].removesuffix(".git")

    return owner, repo.removesuffix(".git")


def default_repo_slug(owner: str, repo: str) -> str:
    """Short local namespace; prefer repo name unless it is too generic."""
    if repo in {"skills", "agent-skills"}:
        return owner
    return repo
