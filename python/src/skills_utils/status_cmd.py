from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from skills_utils.agents import list_agents, resolve_skills_dir
from skills_utils.config_loader import load_config, load_manifest
from skills_utils.github import GitHubClient
from skills_utils.hash import dir_hash
from skills_utils.repos import fetch_remote_inventory, repo_from_config
from skills_utils.scanner import (
    build_skill_states,
    compute_status,
    install_key,
    nested_install_path,
)

console = Console()


@dataclass
class StatusRow:
    agent_id: str
    repo_slug: str
    skill: str
    status: str
    installed_at: str


def collect_status_rows(
    config: dict[str, Any],
    manifest: dict[str, Any],
    agent_filter: str | None = None,
    repo_filter: str | None = None,
    check_remote: bool = False,
    token: str | None = None,
) -> list[StatusRow]:
    rows: list[StatusRow] = []
    repos = {
        slug: repo_from_config(slug, data)
        for slug, data in config.get("repos", {}).items()
    }

    with GitHubClient(token=token) as client:
        remote_by_repo: dict[str, dict] = {}
        if check_remote:
            for slug, repo in repos.items():
                if repo_filter and slug != repo_filter:
                    continue
                _, inventory = fetch_remote_inventory(client, repo)
                remote_by_repo[slug] = inventory

        for agent_id, agent in list_agents(config):
            if agent_filter and agent_id != agent_filter:
                continue
            skills_dir = resolve_skills_dir(agent)
            agent_manifest = manifest.get("agents", {}).get(agent_id, {})
            for key, entry in sorted(agent_manifest.items()):
                repo_slug = entry.get("repo_slug", key.split("/")[0])
                skill_name = key.split("/", 1)[-1]
                if repo_filter and repo_slug != repo_filter:
                    continue
                path = nested_install_path(skills_dir, repo_slug, skill_name)
                local_hash = dir_hash(path) if path.exists() else None
                remote_fp = None
                if check_remote and repo_slug in remote_by_repo:
                    remote = remote_by_repo[repo_slug].get(skill_name)
                    remote_fp = remote.fingerprint if remote else None
                status = compute_status(
                    path.exists(),
                    local_hash,
                    entry.get("installed_hash"),
                    entry.get("remote_fingerprint"),
                    remote_fp,
                )
                rows.append(
                    StatusRow(
                        agent_id=agent_id,
                        repo_slug=repo_slug,
                        skill=skill_name,
                        status=status,
                        installed_at=entry.get("installed_at", ""),
                    )
                )
    return rows


def print_status_table(rows: list[StatusRow]) -> None:
    table = Table(title="Installed skills")
    table.add_column("Agent")
    table.add_column("Repo")
    table.add_column("Skill")
    table.add_column("Status")
    table.add_column("Installed")
    for row in rows:
        table.add_row(
            row.agent_id,
            row.repo_slug,
            row.skill,
            row.status,
            row.installed_at[:10] if row.installed_at else "",
        )
    console.print(table)


def status_exit_code(rows: list[StatusRow]) -> int:
    if any(row.status in {"outdated", "modified", "diverged"} for row in rows):
        return 1
    return 0


def run_status(args: Any) -> int:
    import json

    config = load_config(args.config)
    manifest = load_manifest()
    rows = collect_status_rows(
        config,
        manifest,
        agent_filter=args.agent,
        repo_filter=args.repo,
        check_remote=args.check_remote,
        token=args.token,
    )
    if args.format == "json":
        payload = {
            "agents": {}
        }
        for row in rows:
            payload["agents"].setdefault(row.agent_id, []).append(
                {
                    "repo": row.repo_slug,
                    "skill": row.skill,
                    "status": row.status,
                    "installed_at": row.installed_at,
                }
            )
        print(json.dumps(payload, indent=2))
    else:
        if not rows:
            console.print("[yellow]No skills installed.[/yellow]")
        else:
            print_status_table(rows)
    return status_exit_code(rows)
