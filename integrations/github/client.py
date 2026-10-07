"""Small async GitHub REST client with pinned-ref content reads."""

import base64
from typing import Any

import httpx


class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com", timeout: float = 20.0):
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.client.aclose()

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        response = await self.client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        response.raise_for_status()
        return response.json()

    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        page = 1
        while True:
            response = await self.client.get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
                params={"per_page": 100, "page": page},
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                return files
            files.extend(batch)
            if len(batch) < 100:
                return files
            page += 1

    async def get_file_content(self, owner: str, repo: str, path: str, ref: str) -> str:
        response = await self.client.get(f"/repos/{owner}/{repo}/contents/{path}", params={"ref": ref})
        response.raise_for_status()
        data = response.json()
        if data.get("encoding") != "base64":
            raise ValueError("GitHub content response is not base64 encoded")
        return base64.b64decode(data["content"]).decode("utf-8")

    async def search_code(self, query: str) -> list[dict[str, Any]]:
        response = await self.client.get("/search/code", params={"q": query})
        response.raise_for_status()
        return response.json().get("items", [])

