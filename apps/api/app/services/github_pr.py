from __future__ import annotations

import base64
import os
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from app.schemas.planning import PatchFile
from app.schemas.pull_requests import PullRequestCreateResponse
from app.services.github_client import parse_github_repository_url
from app.services.sandbox_validation import _run, validate_patches


GITHUB_API = "https://api.github.com"


class GitHubWriteClient:
    def __init__(self) -> None:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise HTTPException(
                status_code=503,
                detail="GITHUB_TOKEN is required for pull-request creation.",
            )

        self._client = httpx.AsyncClient(
            base_url=GITHUB_API,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ForgeAI",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs):
        response = await self._client.request(method, path, **kwargs)
        if response.status_code in {401, 403}:
            raise HTTPException(
                status_code=403,
                detail="GitHub token does not have permission to write to this repository.",
            )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="GitHub repository or ref not found.")
        if response.is_error:
            raise HTTPException(
                status_code=502,
                detail=f"GitHub write API returned {response.status_code}: {response.text[:500]}",
            )
        return response.json() if response.content else {}

    async def repository(self, full_name: str) -> dict:
        return await self._request("GET", f"/repos/{full_name}")

    async def ref(self, full_name: str, branch: str) -> dict:
        safe = quote(branch, safe="")
        return await self._request("GET", f"/repos/{full_name}/git/ref/heads/{safe}")

    async def create_branch(self, full_name: str, branch: str, sha: str) -> None:
        await self._request(
            "POST",
            f"/repos/{full_name}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": sha},
        )

    async def file(self, full_name: str, path: str, branch: str) -> dict:
        safe_path = "/".join(quote(part, safe="") for part in path.split("/"))
        return await self._request(
            "GET",
            f"/repos/{full_name}/contents/{safe_path}",
            params={"ref": branch},
        )

    async def update_file(
        self,
        full_name: str,
        path: str,
        branch: str,
        sha: str,
        content: bytes,
        message: str,
    ) -> str:
        safe_path = "/".join(quote(part, safe="") for part in path.split("/"))
        payload = await self._request(
            "PUT",
            f"/repos/{full_name}/contents/{safe_path}",
            json={
                "message": message,
                "content": base64.b64encode(content).decode("ascii"),
                "sha": sha,
                "branch": branch,
            },
        )
        return payload["commit"]["sha"]

    async def create_pull_request(
        self,
        full_name: str,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> dict:
        return await self._request(
            "POST",
            f"/repos/{full_name}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": False,
            },
        )


def _pr_body(task: str, validation, files: list[str]) -> str:
    checks = "\n".join(
        f"- {'✅' if command.status == 'passed' else '❌'} "
        f"{command.command} — {command.status} ({command.duration_ms} ms)"
        for command in validation.commands
    )
    file_lines = "\n".join(f"- `{path}`" for path in files)
    return f"""## ForgeAI validated patch

### Task
{task}

### Changed files
{file_lines}

### Validation
- Sandbox: `{validation.sandbox}`
- Result: **{'PASS' if validation.passed else 'FAIL'}**
- PR gate: **{'OPEN' if validation.safe_to_propose_pr else 'BLOCKED'}**

{checks}

### Safety
This pull request was created only after explicit human approval and a fresh
server-side ForgeAI validation run. The patch was applied and tested in a disposable
workspace before repository write actions were allowed.
"""


async def _materialize_patched_files(
    repository_url: str,
    patches: list[PatchFile],
) -> dict[str, bytes]:
    ref = parse_github_repository_url(repository_url)

    with tempfile.TemporaryDirectory(prefix="forgeai-pr-") as temp_dir:
        root = Path(temp_dir) / "repo"
        repo_url = f"https://github.com/{ref.full_name}.git"

        clone_code, _, clone_err, _, _ = await _run(
            ["git", "clone", "--depth", "1", "--", repo_url, str(root)],
            timeout=60,
        )
        if clone_code != 0:
            raise HTTPException(
                status_code=502,
                detail=f"Could not clone repository for PR materialization: {clone_err[:500]}",
            )

        patch_path = Path(temp_dir) / "validated.patch"
        patch_path.write_text(
            "\n".join(item.unified_diff.rstrip() for item in patches) + "\n",
            encoding="utf-8",
        )

        apply_code, _, apply_err, _, _ = await _run(
            ["git", "apply", "--", str(patch_path)],
            cwd=root,
            timeout=30,
        )
        if apply_code != 0:
            raise HTTPException(
                status_code=409,
                detail=f"Validated patch could not be re-applied: {apply_err[:500]}",
            )

        materialized: dict[str, bytes] = {}
        for patch in patches:
            file_path = root / patch.path
            if not file_path.is_file():
                raise HTTPException(
                    status_code=409,
                    detail=f"Patched file is missing after apply: {patch.path}",
                )
            materialized[patch.path] = file_path.read_bytes()

        return materialized


async def create_validated_pull_request(
    repository_url: str,
    task: str,
    patches: list[PatchFile],
    approved: bool,
) -> PullRequestCreateResponse:
    ref = parse_github_repository_url(repository_url)

    if not approved:
        validation = await validate_patches(repository_url, patches)
        return PullRequestCreateResponse(
            repository=ref.full_name,
            status="approval_required",
            validation=validation,
            message="Explicit human approval is required before repository writes.",
        )

    validation = await validate_patches(repository_url, patches)
    if not validation.safe_to_propose_pr:
        return PullRequestCreateResponse(
            repository=ref.full_name,
            status="validation_blocked",
            validation=validation,
            message="Fresh server-side validation did not open the PR gate.",
        )

    contents = await _materialize_patched_files(repository_url, patches)
    client = GitHubWriteClient()

    try:
        repository = await client.repository(ref.full_name)
        base_branch = repository.get("default_branch") or "main"
        base_ref = await client.ref(ref.full_name, base_branch)
        base_sha = base_ref["object"]["sha"]

        branch_name = f"forgeai/validated-{uuid.uuid4().hex[:8]}"
        await client.create_branch(ref.full_name, branch_name, base_sha)

        committed_files: list[str] = []
        for path, content in contents.items():
            current = await client.file(ref.full_name, path, base_branch)
            await client.update_file(
                full_name=ref.full_name,
                path=path,
                branch=branch_name,
                sha=current["sha"],
                content=content,
                message=f"fix: ForgeAI validated change for {task[:72]}",
            )
            committed_files.append(path)

        pr = await client.create_pull_request(
            full_name=ref.full_name,
            title=f"ForgeAI: {task[:72]}",
            body=_pr_body(task, validation, committed_files),
            head=branch_name,
            base=base_branch,
        )

        return PullRequestCreateResponse(
            repository=ref.full_name,
            branch=branch_name,
            pull_request_url=pr["html_url"],
            pull_request_number=pr["number"],
            status="created",
            validation=validation,
            committed_files=committed_files,
            message="Validated pull request created successfully.",
        )
    finally:
        await client.close()
