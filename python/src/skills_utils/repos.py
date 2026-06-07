from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skills_utils.config_loader import cache_dir
from skills_utils.github import GitHubClient
from skills_utils.hash import remote_fingerprint
from skills_utils.progress import SyncProgress
from skills_utils.repo_parse import parse_github_repo


@dataclass
class RepoConfig:
    slug: str
    owner: str
    repo: str
    branch: str
    skills_path: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"


@dataclass
class RemoteSkill:
    name: str
    remote_path: str
    fingerprint: str
    files: dict[str, str]


def repo_from_config(slug: str, data: dict[str, Any]) -> RepoConfig:
    owner, repo_name = parse_github_repo(data["owner"], data["repo"])
    return RepoConfig(
        slug=slug,
        owner=owner,
        repo=repo_name,
        branch=data.get("branch", "main"),
        skills_path=data.get("skills_path", "skills"),
    )


def repo_cache_dir(repo: RepoConfig) -> Path:
    return cache_dir() / repo.slug


def parse_skill_trees(
    tree: list[dict[str, Any]], skills_path: str
) -> dict[str, dict[str, str]]:
    prefix = f"{skills_path.strip('/')}/"
    skills: dict[str, dict[str, str]] = {}
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        if not path.startswith(prefix):
            continue
        remainder = path[len(prefix) :]
        parts = remainder.split("/", 1)
        if len(parts) != 2:
            continue
        skill_name, rel_path = parts
        skills.setdefault(skill_name, {})[rel_path] = item["sha"]
    return skills


def fetch_remote_inventory(
    client: GitHubClient, repo: RepoConfig
) -> tuple[str, dict[str, RemoteSkill]]:
    commit_sha = client.resolve_commit_sha(repo.owner, repo.repo, repo.branch)
    tree = client.fetch_tree(repo.owner, repo.repo, repo.branch)
    by_skill = parse_skill_trees(tree, repo.skills_path)
    inventory: dict[str, RemoteSkill] = {}
    for name, files in sorted(by_skill.items()):
        if "SKILL.md" not in files:
            continue
        inventory[name] = RemoteSkill(
            name=name,
            remote_path=f"{repo.skills_path}/{name}",
            fingerprint=remote_fingerprint(files),
            files=files,
        )
    return commit_sha, inventory


def download_skill_files(
    client: GitHubClient,
    repo: RepoConfig,
    skill: RemoteSkill,
    dest: Path,
    progress: SyncProgress | None = None,
) -> None:
    if dest.exists():
        import shutil

        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    files = sorted(skill.files.items())
    for index, (rel_path, blob_sha) in enumerate(files, start=1):
        if progress:
            progress.downloading(skill.name, rel_path, index, len(files))
        content = client.download_blob(repo.owner, repo.repo, blob_sha)
        target = dest / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
