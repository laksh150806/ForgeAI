from __future__ import annotations

import asyncio
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import HTTPException

from app.services.github_client import GitHubRepositoryRef, parse_github_repository_url


def public_clone_url(ref: GitHubRepositoryRef) -> str:
    return f"https://github.com/{ref.full_name}.git"


async def _run_git(*args: str, cwd: Path | None = None, timeout: int = 90) -> tuple[int, str, str]:
    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise HTTPException(status_code=504, detail="Git repository checkout timed out.") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Git is unavailable in the ForgeAI runtime.") from exc

    return (
        process.returncode,
        stdout.decode(errors="replace"),
        stderr.decode(errors="replace"),
    )


@asynccontextmanager
async def public_repository_checkout(
    repository_url: str,
) -> AsyncIterator[tuple[GitHubRepositoryRef, Path, str]]:
    ref = parse_github_repository_url(repository_url)

    with tempfile.TemporaryDirectory(prefix="forgeai-public-repo-") as temp_dir:
        root = Path(temp_dir) / "repo"
        code, _, stderr = await _run_git(
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--",
            public_clone_url(ref),
            str(root),
            timeout=90,
        )
        if code != 0:
            raise HTTPException(
                status_code=502,
                detail=f"Public Git repository checkout failed: {stderr[:500]}",
            )

        branch_code, branch_stdout, _ = await _run_git(
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
            cwd=root,
            timeout=15,
        )
        default_branch = branch_stdout.strip() if branch_code == 0 else "main"

        yield ref, root, default_branch
