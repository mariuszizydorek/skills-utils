from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from skills_utils.agents import list_agents, resolve_skills_dir
from skills_utils.config_loader import home_dir, load_config, load_manifest, resolve_config_path
from skills_utils.github import GitHubClient
from skills_utils.repos import repo_from_config
from skills_utils.scanner import flat_symlink_path, nested_install_path
from skills_utils.sync import _ensure_flat_symlink

console = Console()


@dataclass
class CheckResult:
    level: str  # ok | warn | error
    message: str


def run_doctor(args: Any) -> int:
    config = load_config(args.config)
    manifest = load_manifest()
    results: list[CheckResult] = []

    config_path = resolve_config_path(args.config)
    if config_path.exists():
        results.append(CheckResult("ok", f"config.yaml found ({config_path})"))
    else:
        results.append(CheckResult("error", "config.yaml missing"))

    try:
        skill_count = sum(
            len(entries) for entries in manifest.get("agents", {}).values()
        )
        results.append(CheckResult("ok", f"manifest.json valid ({skill_count} skills tracked)"))
    except Exception as exc:
        results.append(CheckResult("error", f"manifest.json corrupt: {exc}"))

    token = args.token or GitHubClient._detect_token()
    if token:
        results.append(CheckResult("ok", "GitHub token available"))
    else:
        results.append(
            CheckResult(
                "warn",
                "No GitHub auth detected - set GITHUB_TOKEN/GH_TOKEN, pass --token, or run gh auth login (public repos OK)",
            )
        )

    with GitHubClient(token=token) as client:
        if client.ping():
            results.append(CheckResult("ok", "GitHub API reachable"))
        else:
            results.append(CheckResult("error", "GitHub API unreachable"))

        for slug, data in config.get("repos", {}).items():
            repo = repo_from_config(slug, data)
            try:
                dirs = client.list_skill_dirs(repo.owner, repo.repo, repo.skills_path)
                results.append(
                    CheckResult("ok", f"{repo.full_name} reachable ({len(dirs)} skill folders)")
                )
            except Exception as exc:
                results.append(CheckResult("error", f"{repo.full_name} unreachable: {exc}"))

    agents = list_agents(config)
    if args.agent:
        agents = [(aid, data) for aid, data in agents if aid == args.agent]

    for agent_id, agent in agents:
        skills_dir = resolve_skills_dir(agent)
        if skills_dir.exists() and os.access(skills_dir, os.W_OK):
            results.append(CheckResult("ok", f"{skills_dir} writable"))
        elif not skills_dir.exists():
            results.append(CheckResult("warn", f"{skills_dir} missing (creatable)"))
            if args.fix:
                skills_dir.mkdir(parents=True, exist_ok=True)
                results.append(CheckResult("ok", f"Created {skills_dir}"))
        else:
            results.append(CheckResult("error", f"{skills_dir} not writable"))

        agent_manifest = manifest.get("agents", {}).get(agent_id, {})
        for key, entry in agent_manifest.items():
            repo_slug = entry.get("repo_slug", key.split("/")[0])
            skill_name = key.split("/", 1)[-1]
            path = nested_install_path(skills_dir, repo_slug, skill_name)
            if not path.exists():
                results.append(CheckResult("warn", f"Orphan manifest entry: {agent_id}/{key}"))
                continue
            if not (path / "SKILL.md").exists():
                results.append(CheckResult("error", f"Missing SKILL.md: {path}"))

            link = flat_symlink_path(skills_dir, skill_name)
            if link.is_symlink():
                if link.exists():
                    results.append(CheckResult("ok", f"Symlink valid: {link.name}"))
                else:
                    results.append(CheckResult("error", f"Broken symlink: {link}"))
                    if args.fix:
                        link.unlink(missing_ok=True)
                        _ensure_flat_symlink(skills_dir, repo_slug, skill_name)
                        results.append(CheckResult("ok", f"Repaired symlink: {link.name}"))
            elif config.get("defaults", {}).get("flat_symlinks", True) and path.exists():
                if args.fix:
                    _ensure_flat_symlink(skills_dir, repo_slug, skill_name)
                    results.append(CheckResult("ok", f"Created symlink: {link.name}"))

    console.print("\n[bold]skills-sync doctor[/bold]\n")
    errors = warnings = 0
    for item in results:
        if item.level == "ok":
            console.print(f"  [green]✓[/green]  {item.message}")
        elif item.level == "warn":
            warnings += 1
            console.print(f"  [yellow]⚠[/yellow]  {item.message}")
        else:
            errors += 1
            console.print(f"  [red]✗[/red]  {item.message}")

    console.print()
    if errors:
        console.print(f"[red]{warnings} warnings, {errors} errors[/red]")
        return 2
    if warnings:
        console.print(f"[yellow]{warnings} warnings[/yellow]")
        return 1
    console.print("[green]All checks passed[/green]")
    return 0
