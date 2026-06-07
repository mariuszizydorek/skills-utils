from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from skills_utils import MANIFEST_VERSION, SKILLS_UTILS_HOME


def home_dir() -> Path:
    return Path.home() / SKILLS_UTILS_HOME


def cache_dir() -> Path:
    return home_dir() / "cache"


def manifest_path() -> Path:
    return home_dir() / "manifest.json"


def bundled_config_path() -> Path:
    with resources.as_file(
        resources.files("skills_utils").joinpath("bundled_config.yaml")
    ) as path:
        return path


def resolve_config_path(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("SKILLS_UTILS_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    user_config = home_dir() / "config.yaml"
    if user_config.exists():
        return user_config
    home_dir().mkdir(parents=True, exist_ok=True)
    shutil.copy2(bundled_config_path(), user_config)
    return user_config


def _load_bundled_config() -> dict[str, Any]:
    with bundled_config_path().open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _merge_bundled_defaults(config: dict[str, Any]) -> dict[str, Any]:
    bundled = _load_bundled_config()
    for key, value in bundled.get("agents", {}).items():
        config.setdefault("agents", {}).setdefault(key, value)
    config.setdefault("repos", bundled.get("repos", {}))
    config.setdefault("defaults", bundled.get("defaults", {}))
    return config


def load_config(explicit: str | None = None) -> dict[str, Any]:
    path = resolve_config_path(explicit)
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    return _merge_bundled_defaults(config)


def load_manifest() -> dict[str, Any]:
    path = manifest_path()
    if not path.exists():
        return {"version": MANIFEST_VERSION, "agents": {}}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if "agents" not in data:
        data["agents"] = {}
    return data


def save_manifest(data: dict[str, Any]) -> None:
    home_dir().mkdir(parents=True, exist_ok=True)
    data["version"] = MANIFEST_VERSION
    with manifest_path().open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def get_skill_entry(
    manifest: dict[str, Any], agent_id: str, install_key: str
) -> dict[str, Any] | None:
    return manifest.get("agents", {}).get(agent_id, {}).get(install_key)


def set_skill_entry(
    manifest: dict[str, Any],
    agent_id: str,
    install_key: str,
    entry: dict[str, Any],
) -> None:
    manifest.setdefault("agents", {}).setdefault(agent_id, {})[install_key] = entry


def remove_skill_entry(
    manifest: dict[str, Any], agent_id: str, install_key: str
) -> None:
    agents = manifest.get("agents", {})
    if agent_id in agents and install_key in agents[agent_id]:
        del agents[agent_id][install_key]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
