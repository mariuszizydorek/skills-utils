from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def expand_path(value: str, cwd: Path | None = None) -> Path:
    base = cwd or Path.cwd()
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (base / path).resolve()
    return path


def project_root(cwd: Path | None = None) -> Path:
    base = cwd or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=base,
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (FileNotFoundError, subprocess.CalledProcessError):
        return base


def resolve_skills_dir(agent: dict[str, Any], cwd: Path | None = None) -> Path:
    base = cwd or Path.cwd()
    if agent.get("scope") == "project":
        root = project_root(base)
        return expand_path(agent["skills_dir"], root)
    return expand_path(agent["skills_dir"], base)


def list_agents(config: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return list((agent_id, data) for agent_id, data in config.get("agents", {}).items())


def agent_label(agent_id: str, agent: dict[str, Any]) -> str:
    label = agent.get("label", agent_id)
    return f"{label} ({agent_id})"
