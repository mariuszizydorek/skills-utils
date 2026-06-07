from __future__ import annotations

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.table import Table

from skills_utils.repo_parse import default_repo_slug, parse_github_repo
from skills_utils.scanner import SkillState

console = Console()


def _choice_label(state: SkillState) -> str:
    suffix = state.note or state.status
    if state.read_only:
        return f"{state.name} ({suffix})"
    if state.status == "synced":
        return f"{state.name} — in sync"
    if state.status == "missing":
        return f"{state.name} — new"
    return f"{state.name} — {suffix}"


def select_agent(choices: list[tuple[str, str]]) -> str:
    options = [Choice(value=agent_id, name=label) for agent_id, label in choices]
    return inquirer.select(message="Which agent?", choices=options).execute()


def select_repo(choices: list[tuple[str, str]]) -> str:
    options = [Choice(value=slug, name=label) for slug, label in choices]
    options.append(Choice(value="__add__", name="+ Add new repo..."))
    return inquirer.select(message="Remote skills repo:", choices=options).execute()


from skills_utils.repo_parse import default_repo_slug, parse_github_repo


def prompt_new_repo() -> dict[str, str]:
    raw = inquirer.text(
        message="GitHub repo (owner/repo or full URL):",
        validate=lambda v: len(v.strip()) > 0,
    ).execute()
    owner, repo_name = parse_github_repo("", raw)
    branch = inquirer.text(message="Branch:", default="main").execute()
    skills_path = inquirer.text(message="Skills path:", default="skills").execute()
    default_slug = default_repo_slug(owner, repo_name)
    slug = inquirer.text(
        message="Repo slug (local folder name):",
        default=default_slug,
    ).execute()
    console.print(f"[dim]Will sync from {owner}/{repo_name} → ./{slug}/<skill>[/dim]")
    return {
        "slug": slug,
        "owner": owner,
        "repo": repo_name,
        "branch": branch,
        "skills_path": skills_path,
    }


def select_skills(states: list[SkillState]) -> set[str]:
    selectable = [s for s in states if not s.read_only]
    default = [s.name for s in selectable if s.installed or s.status != "missing"]
    choices = [Choice(value=s.name, name=_choice_label(s), enabled=not s.read_only) for s in states]
    selected = inquirer.checkbox(
        message="Select skills to install/keep:",
        choices=choices,
        default=default,
        validate=lambda result: True,
    ).execute()
    return set(selected)


def select_updates(candidates: list[SkillState]) -> set[str]:
    if not candidates:
        return set()
    choices = [
        Choice(value=s.name, name=f"{s.name} — {s.note or s.status}") for s in candidates
    ]
    selected = inquirer.checkbox(
        message="Update these outdated/modified skills?",
        choices=choices,
        default=[s.name for s in candidates],
    ).execute()
    return set(selected)


def print_plan(install: list[str], remove: list[str], updates: list[str]) -> None:
    table = Table(title="Sync plan")
    table.add_column("Action")
    table.add_column("Skills")
    if install:
        table.add_row("+ install", ", ".join(install))
    if remove:
        table.add_row("- remove", ", ".join(remove))
    if updates:
        table.add_row("~ update", ", ".join(updates))
    if not install and not remove and not updates:
        console.print("[green]No changes needed.[/green]")
        return
    console.print(table)


def confirm_apply() -> bool:
    return inquirer.confirm(message="Apply changes?", default=True).execute()


def print_result(installed: list[str], removed: list[str], updated: list[str]) -> None:
    console.print("\n[bold green]Done[/bold green]")
    if installed:
        console.print(f"  Installed: {', '.join(installed)}")
    if removed:
        console.print(f"  Removed: {', '.join(removed)}")
    if updated:
        console.print(f"  Updated: {', '.join(updated)}")
