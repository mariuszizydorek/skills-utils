from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

from skills_utils.agents import agent_label, list_agents, resolve_skills_dir
from skills_utils.config_loader import load_config, load_manifest, resolve_config_path, save_manifest
from skills_utils.doctor import run_doctor
from skills_utils.github import GitHubClient
from skills_utils.repos import fetch_remote_inventory, repo_from_config
from skills_utils.repo_parse import default_repo_slug, parse_github_repo
from skills_utils.scanner import build_skill_states
from skills_utils.status_cmd import run_status
from skills_utils.progress import SyncProgress
from skills_utils.sync import apply_sync
from skills_utils.ui import (
    confirm_apply,
    print_plan,
    print_result,
    prompt_new_repo,
    select_agent,
    select_repo,
    select_skills,
    select_updates,
)

console = Console()


def save_repo_to_config(config_path: Path, slug: str, repo_data: dict[str, str]) -> str:
    owner, repo_name = parse_github_repo(repo_data["owner"], repo_data["repo"])
    if not slug or slug.startswith("http") or "/" in slug:
        slug = default_repo_slug(owner, repo_name)
    config = load_config(str(config_path))
    config.setdefault("repos", {})[slug] = {
        "owner": owner,
        "repo": repo_name,
        "branch": repo_data["branch"],
        "skills_path": repo_data["skills_path"],
    }
    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)
    console.print(f"[green]Added repo:[/green] {owner}/{repo_name} (slug: {slug})")
    return slug


def run_interactive(args: argparse.Namespace) -> int:
    config_path = resolve_config_path(args.config)
    config = load_config(args.config)
    manifest = load_manifest()
    flat_symlinks = config.get("defaults", {}).get("flat_symlinks", True) and not args.no_symlinks

    agent_choices = [
        (agent_id, f"{agent_label(agent_id, agent)} → {resolve_skills_dir(agent)}")
        for agent_id, agent in list_agents(config)
    ]
    agent_id = select_agent(agent_choices)
    agent = config["agents"][agent_id]
    skills_dir = resolve_skills_dir(agent)
    skills_dir.mkdir(parents=True, exist_ok=True)

    repo_choices = [
        (slug, f"{data['owner']}/{data['repo']}")
        for slug, data in config.get("repos", {}).items()
    ]
    repo_slug = select_repo(repo_choices)
    if repo_slug == "__add__":
        new_repo = prompt_new_repo()
        repo_slug = save_repo_to_config(config_path, new_repo["slug"], new_repo)
        config = load_config(args.config)

    repo = repo_from_config(repo_slug, config["repos"][repo_slug])

    with GitHubClient(token=args.token) as client:
        with console.status(f"Checking {repo.full_name}…"):
            commit_sha, remote_inventory = fetch_remote_inventory(client, repo)

        states = build_skill_states(
            repo.slug, skills_dir, remote_inventory, manifest, agent_id
        )
        selected = select_skills(states)

        existing = {
            s.name
            for s in states
            if not s.read_only and s.installed and s.repo_slug == repo.slug
        }
        install = sorted(selected - existing)
        remove = sorted(existing - selected)
        update_candidates = [
            s
            for s in states
            if s.name in selected
            and s.status in {"outdated", "modified", "diverged"}
            and not s.read_only
        ]
        print_plan(install, remove, [s.name for s in update_candidates])
        if not install and not remove and not update_candidates:
            return 0
        if not confirm_apply():
            console.print("Cancelled.")
            return 0
        to_update = select_updates(update_candidates)
        with SyncProgress() as progress:
            result = apply_sync(
                client,
                repo,
                agent_id,
                agent,
                manifest,
                remote_inventory,
                commit_sha,
                selected,
                to_update,
                flat_symlinks,
                skills_dir,
                progress=progress,
            )
        save_manifest(manifest)
        print_result(result.installed, result.removed, result.updated)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skills-sync")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--token", help="GitHub token")
    parser.add_argument("--no-symlinks", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--prune-unknown", action="store_true")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("sync", help="Interactive sync (default)")

    status = sub.add_parser("status", help="Show installed skills")
    status.add_argument("--agent")
    status.add_argument("--repo")
    status.add_argument("--format", choices=["table", "json"], default="table")
    status.add_argument("--check-remote", action="store_true")

    doctor = sub.add_parser("doctor", help="Health check")
    doctor.add_argument("--agent")
    doctor.add_argument("--fix", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command

    if command == "status":
        raise SystemExit(run_status(args))
    if command == "doctor":
        raise SystemExit(run_doctor(args))
    if command in (None, "sync"):
        if not sys.stdin.isatty():
            console.print("[red]Interactive sync requires a TTY. Use 'skills-sync status'.[/red]")
            raise SystemExit(2)
        raise SystemExit(run_interactive(args))
    parser.print_help()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
