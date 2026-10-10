from __future__ import annotations

import asyncio
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

from fastapi import HTTPException

from app.services.github_client import GitHubRepositoryRef, parse_github_repository_url


@dataclass(frozen=True)
class GitCommitSnapshot:
    sha: str
    authored_at_epoch: int
    subject: str
    changed_files: list[str]
    patch: str


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


async def checkout_repository_commit(root: Path, sha: str) -> None:
    code, _, stderr = await _run_git(
        "checkout",
        "--detach",
        "--force",
        sha,
        cwd=root,
        timeout=30,
    )
    if code != 0:
        raise HTTPException(
            status_code=502,
            detail=f"Could not materialize target commit {sha[:8]}: {stderr[:500]}",
        )


async def recent_commit_history(
    root: Path,
    limit: int = 10,
    patch_char_limit: int = 20000,
) -> list[GitCommitSnapshot]:
    code, stdout, stderr = await _run_git(
        "log",
        f"-n{limit}",
        "--format=%H%x1f%ct%x1f%s",
        cwd=root,
        timeout=30,
    )
    if code != 0:
        raise HTTPException(
            status_code=502,
            detail=f"Could not inspect repository history: {stderr[:500]}",
        )

    commits: list[GitCommitSnapshot] = []
    for raw_line in stdout.splitlines():
        parts = raw_line.split("\x1f", 2)
        if len(parts) != 3:
            continue
        sha, epoch_text, subject = parts

        files_code, files_stdout, _ = await _run_git(
            "show",
            "--format=",
            "--name-only",
            "--diff-filter=ACMRT",
            sha,
            cwd=root,
            timeout=20,
        )
        changed_files = list(
            dict.fromkeys(
                line.strip()
                for line in files_stdout.splitlines()
                if line.strip()
            )
        ) if files_code == 0 else []

        patch_code, patch_stdout, _ = await _run_git(
            "show",
            "--format=",
            "--unified=0",
            "--no-ext-diff",
            sha,
            "--",
            cwd=root,
            timeout=30,
        )
        patch = patch_stdout[:patch_char_limit] if patch_code == 0 else ""

        try:
            epoch = int(epoch_text)
        except ValueError:
            epoch = 0

        commits.append(
            GitCommitSnapshot(
                sha=sha,
                authored_at_epoch=epoch,
                subject=subject,
                changed_files=changed_files,
                patch=patch,
            )
        )

    return commits


@asynccontextmanager
async def public_repository_checkout(
    repository_url: str,
    depth: int = 1,
) -> AsyncIterator[tuple[GitHubRepositoryRef, Path, str]]:
    ref = parse_github_repository_url(repository_url)

    with tempfile.TemporaryDirectory(prefix="forgeai-public-repo-") as temp_dir:
        root = Path(temp_dir) / "repo"
        code, _, stderr = await _run_git(
            "clone",
            "--depth",
            str(max(1, depth)),
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
