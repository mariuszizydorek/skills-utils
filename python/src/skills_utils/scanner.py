from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skills_utils.hash import dir_hash
from skills_utils.repos import RemoteSkill


SkillStatus = str  # missing | synced | outdated | modified | diverged


@dataclass
class SkillState:
    name: str
    status: SkillStatus
    installed: bool
    repo_slug: str | None = None
    install_path: Path | None = None
    remote: RemoteSkill | None = None
    local_hash: str | None = None
    manifest_hash: str | None = None
    manifest_fingerprint: str | None = None
    read_only: bool = False
    note: str = ""


def install_key(repo_slug: str, skill_name: str) -> str:
    return f"{repo_slug}/{skill_name}"


def nested_install_path(skills_dir: Path, repo_slug: str, skill_name: str) -> Path:
    return skills_dir / repo_slug / skill_name


def flat_symlink_path(skills_dir: Path, skill_name: str) -> Path:
    return skills_dir / skill_name


def compute_status(
    installed: bool,
    local_hash: str | None,
    manifest_hash: str | None,
    manifest_fingerprint: str | None,
    remote_fingerprint: str | None,
) -> SkillStatus:
    if not installed:
        return "missing"
    outdated = (
        remote_fingerprint is not None
        and manifest_fingerprint is not None
        and remote_fingerprint != manifest_fingerprint
    )
    modified = (
        local_hash is not None
        and manifest_hash is not None
        and local_hash != manifest_hash
    )
    if outdated and modified:
        return "diverged"
    if outdated:
        return "outdated"
    if modified:
        return "modified"
    if remote_fingerprint and local_hash and manifest_hash:
        if remote_fingerprint != manifest_fingerprint:
            return "outdated"
    return "synced"


def build_skill_states(
    repo_slug: str,
    skills_dir: Path,
    remote_inventory: dict[str, RemoteSkill],
    manifest: dict[str, Any],
    agent_id: str,
    current_repo_only: bool = True,
) -> list[SkillState]:
    agent_manifest = manifest.get("agents", {}).get(agent_id, {})
    states: list[SkillState] = []

    for name, remote in sorted(remote_inventory.items()):
        key = install_key(repo_slug, name)
        entry = agent_manifest.get(key)
        path = nested_install_path(skills_dir, repo_slug, name)
        installed = path.exists() and (path / "SKILL.md").exists()
        local_hash = dir_hash(path) if installed else None
        manifest_hash = entry.get("installed_hash") if entry else None
        manifest_fp = entry.get("remote_fingerprint") if entry else None
        status = compute_status(
            installed,
            local_hash,
            manifest_hash,
            manifest_fp,
            remote.fingerprint,
        )
        states.append(
            SkillState(
                name=name,
                status=status,
                installed=installed,
                repo_slug=repo_slug,
                install_path=path,
                remote=remote,
                local_hash=local_hash,
                manifest_hash=manifest_hash,
                manifest_fingerprint=manifest_fp,
                note=_status_note(status),
            )
        )

    if not current_repo_only:
        return states

    for key, entry in agent_manifest.items():
        if entry.get("repo_slug") == repo_slug:
            continue
        if "/" not in key:
            continue
        other_repo, skill_name = key.split("/", 1)
        if skill_name in remote_inventory:
            continue
        path = nested_install_path(skills_dir, other_repo, skill_name)
        if not path.exists():
            continue
        states.append(
            SkillState(
                name=skill_name,
                status="synced",
                installed=True,
                repo_slug=other_repo,
                install_path=path,
                read_only=True,
                note=f"from repo: {other_repo}",
            )
        )

    for child in skills_dir.iterdir() if skills_dir.exists() else []:
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.is_symlink():
            continue
        nested = list(child.iterdir()) if child.is_dir() else []
        for skill_dir in nested:
            if not skill_dir.is_dir():
                continue
            if (skill_dir / "SKILL.md").exists():
                key = install_key(child.name, skill_dir.name)
                if key in agent_manifest or skill_dir.name in remote_inventory:
                    continue
                states.append(
                    SkillState(
                        name=skill_dir.name,
                        status="synced",
                        installed=True,
                        repo_slug=child.name,
                        install_path=skill_dir,
                        read_only=True,
                        note="local/unknown",
                    )
                )

    return states


def _status_note(status: SkillStatus) -> str:
    return {
        "missing": "new",
        "synced": "in sync",
        "outdated": "remote changed",
        "modified": "local differs",
        "diverged": "local + remote changed",
    }.get(status, status)
