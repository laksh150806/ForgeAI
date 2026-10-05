from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote, urlparse

import httpx
from fastapi import HTTPException


GITHUB_API = "https://api.github.com"


@dataclass(frozen=True)
class GitHubRepositoryRef:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


def parse_github_repository_url(repository_url: str) -> GitHubRepositoryRef:
    parsed = urlparse(repository_url)

    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {
        "github.com",
        "www.github.com",
    }:
        raise HTTPException(
            status_code=422,
            detail="ForgeAI currently supports github.com repository URLs only.",
        )

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise HTTPException(
            status_code=422,
            detail="Repository URL must look like https://github.com/owner/repository.",
        )

    owner, name = parts[0], parts[1]
    if name.endswith(".git"):
        name = name[:-4]

    if not owner or not name:
        raise HTTPException(status_code=422, detail="Invalid GitHub repository URL.")

    return GitHubRepositoryRef(owner=owner, name=name)


class GitHubClient:
    def __init__(self) -> None:
        token = os.getenv("GITHUB_TOKEN")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ForgeAI",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._client = httpx.AsyncClient(
            base_url=GITHUB_API,
            headers=headers,
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, **params: object) -> dict:
        response = await self._client.get(path, params=params or None)

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Repository not found or it is private and no valid GitHub token was provided.",
            )
        if response.status_code == 403:
            remaining = response.headers.get("x-ratelimit-remaining")
            detail = "GitHub API request was denied."
            if remaining == "0":
                detail = "GitHub API rate limit reached. Configure GITHUB_TOKEN to increase the limit."
            raise HTTPException(status_code=429, detail=detail)
        if response.is_error:
            raise HTTPException(
                status_code=502,
                detail=f"GitHub API returned {response.status_code}.",
            )

        return response.json()

    async def repository(self, ref: GitHubRepositoryRef) -> dict:
        return await self._get(f"/repos/{ref.full_name}")

    async def commit(self, ref: GitHubRepositoryRef, git_ref: str) -> dict:
        safe_ref = quote(git_ref, safe="")
        return await self._get(f"/repos/{ref.full_name}/commits/{safe_ref}")

    async def tree(self, ref: GitHubRepositoryRef, tree_sha: str) -> dict:
        return await self._get(
            f"/repos/{ref.full_name}/git/trees/{tree_sha}",
            recursive=1,
        )
