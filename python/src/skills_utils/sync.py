from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skills_utils.agents import resolve_skills_dir
from skills_utils.config_loader import set_skill_entry, utc_now_iso
from skills_utils.hash import dir_hash
from skills_utils.progress import SyncProgress
from skills_utils.repos import RemoteSkill, RepoConfig, download_skill_files, repo_cache_dir
from skills_utils.github import GitHubClient
from skills_utils.scanner import flat_symlink_path, install_key, nested_install_path


@dataclass
class SyncPlan:
    install: list[str]
    remove: list[str]
    update: list[str]


@dataclass
class SyncResult:
    installed: list[str] = None  # type: ignore[assignment]
    removed: list[str] = None  # type: ignore[assignment]
    updated: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.installed = self.installed or []
        self.removed = self.removed or []
        self.updated = self.updated or []


def apply_sync(
    client: GitHubClient,
    repo: RepoConfig,
    agent_id: str,
    agent: dict[str, Any],
    manifest: dict[str, Any],
    remote_inventory: dict[str, RemoteSkill],
    commit_sha: str,
    selected: set[str],
    to_update: set[str],
    flat_symlinks: bool,
    skills_dir: Path | None = None,
    progress: SyncProgress | None = None,
) -> SyncResult:
    target_dir = skills_dir or resolve_skills_dir(agent)
    target_dir.mkdir(parents=True, exist_ok=True)
    result = SyncResult()
    existing = {
        name
        for name, remote in remote_inventory.items()
        if nested_install_path(target_dir, repo.slug, name).exists()
    }

    to_remove = sorted(existing - selected)
    to_apply: list[tuple[str, RemoteSkill]] = []
    for name in sorted(selected):
        remote = remote_inventory[name]
        install_path = nested_install_path(target_dir, repo.slug, name)
        was_installed = install_path.exists() and (install_path / "SKILL.md").exists()
        key = install_key(repo.slug, name)
        entry = manifest.get("agents", {}).get(agent_id, {}).get(key)
        needs_copy = (
            not was_installed
            or name in to_update
            or not entry
            or entry.get("remote_fingerprint") != remote.fingerprint
        )
        if needs_copy:
            to_apply.append((name, remote))
        elif flat_symlinks:
            _ensure_flat_symlink(target_dir, repo.slug, name)

    if progress:
        progress.begin(len(to_remove) + len(to_apply))

    for index, name in enumerate(to_remove, start=1):
        if progress:
            progress.removing(name, index, len(to_remove))
        _remove_skill(target_dir, repo.slug, name, agent_id, manifest)
        result.removed.append(name)

    for name, remote in to_apply:
        install_path = nested_install_path(target_dir, repo.slug, name)
        was_installed = install_path.exists() and (install_path / "SKILL.md").exists()

        cache_skill_dir = repo_cache_dir(repo) / repo.skills_path / name
        download_skill_files(client, repo, remote, cache_skill_dir, progress=progress)
        if progress:
            progress.installing(name)
        if install_path.exists():
            shutil.rmtree(install_path)
        shutil.copytree(cache_skill_dir, install_path)

        if not was_installed:
            result.installed.append(name)
        else:
            result.updated.append(name)

        set_skill_entry(
            manifest,
            agent_id,
            install_key(repo.slug, name),
            {
                "repo_slug": repo.slug,
                "remote_path": remote.remote_path,
                "commit_sha": commit_sha,
                "remote_fingerprint": remote.fingerprint,
                "installed_hash": dir_hash(install_path),
                "installed_at": utc_now_iso(),
            },
        )
        if flat_symlinks:
            if progress:
                progress.linking(name)
            _ensure_flat_symlink(target_dir, repo.slug, name)

    return result


def _remove_skill(
    skills_dir: Path, repo_slug: str, skill_name: str, agent_id: str, manifest: dict[str, Any]
) -> None:
    path = nested_install_path(skills_dir, repo_slug, skill_name)
    if path.exists():
        shutil.rmtree(path)
    link = flat_symlink_path(skills_dir, skill_name)
    if link.is_symlink():
        link.unlink()
    from skills_utils.config_loader import remove_skill_entry

    remove_skill_entry(manifest, agent_id, install_key(repo_slug, skill_name))


def _ensure_flat_symlink(skills_dir: Path, repo_slug: str, skill_name: str) -> None:
    link = flat_symlink_path(skills_dir, skill_name)
    target = Path(repo_slug) / skill_name
    if link.exists() or link.is_symlink():
        if link.is_symlink() and link.resolve() == (skills_dir / repo_slug / skill_name).resolve():
            return
        if link.exists():
            return
        if link.is_symlink():
            link.unlink()
    if link.exists():
        return
    link.symlink_to(target)
