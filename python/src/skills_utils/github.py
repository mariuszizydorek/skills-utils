from __future__ import annotations

import os
import subprocess
from typing import Any

import httpx


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or self._detect_token()
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers=headers,
            timeout=60.0,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @staticmethod
    def _detect_token() -> str | None:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            return token
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except FileNotFoundError:
            pass
        return None

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = self.client.get(path, params=params)
        if response.status_code >= 400:
            hint = ""
            if response.status_code == 404 and "/repos/" in path:
                hint = " Check owner/repo names — paste owner/repo or a github.com URL, not the full URL in the repo field."
            raise httpx.HTTPStatusError(
                f"{response.status_code} {response.reason_phrase} for {path}.{hint}",
                request=response.request,
                response=response,
            )
        return response.json()

    def resolve_commit_sha(self, owner: str, repo: str, branch: str) -> str:
        data = self.get(f"/repos/{owner}/{repo}/commits/{branch}")
        return data["sha"]

    def list_skill_dirs(
        self, owner: str, repo: str, skills_path: str
    ) -> list[str]:
        data = self.get(f"/repos/{owner}/{repo}/contents/{skills_path}")
        if not isinstance(data, list):
            raise ValueError(f"Expected directory listing at {skills_path}")
        return sorted(
            item["name"] for item in data if item.get("type") == "dir"
        )

    def fetch_tree(self, owner: str, repo: str, ref: str) -> list[dict[str, Any]]:
        commit_sha = self.resolve_commit_sha(owner, repo, ref)
        commit = self.get(f"/repos/{owner}/{repo}/git/commits/{commit_sha}")
        tree_sha = commit["tree"]["sha"]
        data = self.get(
            f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
            params={"recursive": "1"},
        )
        return data.get("tree", [])

    def download_blob(self, owner: str, repo: str, blob_sha: str) -> bytes:
        import base64

        data = self.get(f"/repos/{owner}/{repo}/git/blobs/{blob_sha}")
        return base64.b64decode(data["content"])

    def ping(self) -> bool:
        try:
            self.get("/rate_limit")
            return True
        except httpx.HTTPError:
            return False
