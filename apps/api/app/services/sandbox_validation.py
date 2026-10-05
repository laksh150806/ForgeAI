from __future__ import annotations

import asyncio
import os
import tempfile
import time
from pathlib import Path

from app.schemas.planning import PatchFile
from app.schemas.validation import (
    PatchApplicationResult,
    ValidationCommandResult,
    ValidationResponse,
)
from app.services.github_client import parse_github_repository_url


MAX_LOG_CHARS = 12000
COMMAND_TIMEOUT_SECONDS = int(os.getenv("VALIDATION_COMMAND_TIMEOUT_SECONDS", "120"))
DOCKER_MEMORY = os.getenv("VALIDATION_DOCKER_MEMORY", "768m")
DOCKER_CPUS = os.getenv("VALIDATION_DOCKER_CPUS", "1.0")
DOCKER_IMAGE_PYTHON = os.getenv("VALIDATION_PYTHON_IMAGE", "python:3.12-slim")
DOCKER_IMAGE_NODE = os.getenv("VALIDATION_NODE_IMAGE", "node:22-slim")


def _trim(value: str) -> str:
    if len(value) <= MAX_LOG_CHARS:
        return value
    return value[-MAX_LOG_CHARS:]


async def _run(
    argv: list[str],
    cwd: Path | None = None,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
) -> tuple[int | None, str, str, int, str]:
    start = time.perf_counter()
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout,
        )
        status = "passed" if process.returncode == 0 else "failed"
        return (
            process.returncode,
            _trim(stdout_bytes.decode(errors="replace")),
            _trim(stderr_bytes.decode(errors="replace")),
            int((time.perf_counter() - start) * 1000),
            status,
        )
    except asyncio.TimeoutError:
        if process.returncode is None:
            process.kill()
            await process.communicate()
        return (
            None,
            "",
            f"Command exceeded {timeout}s timeout.",
            int((time.perf_counter() - start) * 1000),
            "timeout",
        )
    except FileNotFoundError as exc:
        return (
            None,
            "",
            str(exc),
            int((time.perf_counter() - start) * 1000),
            "unavailable",
        )


def _repo_url(repository_url: str) -> str:
    ref = parse_github_repository_url(repository_url)
    return f"https://github.com/{ref.full_name}.git"


def _safe_patch_paths(patches: list[PatchFile]) -> bool:
    for patch in patches:
        path = Path(patch.path)
        if path.is_absolute() or ".." in path.parts:
            return False
        if "\x00" in patch.unified_diff:
            return False
    return True


def _validation_specs(root: Path) -> list[tuple[str, str, list[str]]]:
    specs: list[tuple[str, str, list[str]]] = []

    if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists() or (root / "tests").exists():
        specs.append(("Python compile", DOCKER_IMAGE_PYTHON, ["python", "-m", "compileall", "-q", "."]))
        if (root / "pytest.ini").exists():
            specs.append(("Python tests", DOCKER_IMAGE_PYTHON, ["python", "-m", "pytest", "-q"]))

    if (root / "package.json").exists():
        specs.append(("Node syntax/build", DOCKER_IMAGE_NODE, ["npm", "run", "build", "--if-present"]))
        specs.append(("Node tests", DOCKER_IMAGE_NODE, ["npm", "test", "--if-present"]))

    if not specs:
        specs.append(("Git diff check", "none", ["git", "diff", "--check"]))

    return specs


async def _docker_available() -> bool:
    code, _, _, _, _ = await _run(["docker", "version", "--format", "{{.Server.Version}}"], timeout=12)
    return code == 0


async def _run_docker_command(
    root: Path,
    label: str,
    image: str,
    command: list[str],
) -> ValidationCommandResult:
    if image == "none":
        code, stdout, stderr, duration, status = await _run(command, cwd=root)
        return ValidationCommandResult(
            command=label,
            status=status,
            exit_code=code,
            duration_ms=duration,
            stdout=stdout,
            stderr=stderr,
        )

    argv = [
        "docker", "run", "--rm",
        "--network", "none",
        "--memory", DOCKER_MEMORY,
        "--cpus", DOCKER_CPUS,
        "--pids-limit", "256",
        "--security-opt", "no-new-privileges",
        "--cap-drop", "ALL",
        "--user", "65534:65534",
        "-e", "HOME=/tmp",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m",
        "-v", f"{root}:/workspace:rw",
        "-w", "/workspace",
        image,
        *command,
    ]
    code, stdout, stderr, duration, status = await _run(argv, timeout=COMMAND_TIMEOUT_SECONDS)
    return ValidationCommandResult(
        command=label,
        status=status,
        exit_code=code,
        duration_ms=duration,
        stdout=stdout,
        stderr=stderr,
    )


async def validate_patches(
    repository_url: str,
    patches: list[PatchFile],
) -> ValidationResponse:
    ref = parse_github_repository_url(repository_url)

    if not _safe_patch_paths(patches):
        return ValidationResponse(
            repository=ref.full_name,
            sandbox="not_started",
            status="rejected",
            patch=PatchApplicationResult(
                status="rejected",
                files=[],
                message="Patch paths failed traversal/safety validation.",
            ),
            commands=[],
            passed=False,
            safe_to_propose_pr=False,
            notes=["No commands were executed."],
        )

    docker_ok = await _docker_available()

    with tempfile.TemporaryDirectory(prefix="forgeai-validation-") as temp_dir:
        root = Path(temp_dir) / "repo"
        clone_code, _, clone_err, _, clone_status = await _run(
            ["git", "clone", "--depth", "1", "--", _repo_url(repository_url), str(root)],
            timeout=60,
        )
        if clone_code != 0:
            return ValidationResponse(
                repository=ref.full_name,
                sandbox="docker" if docker_ok else "host-fallback",
                status="clone_failed",
                patch=PatchApplicationResult(
                    status="not_applied",
                    files=[],
                    message=_trim(clone_err) or clone_status,
                ),
                commands=[],
                passed=False,
                safe_to_propose_pr=False,
                notes=["Repository clone failed; patch validation did not run."],
            )

        patch_path = Path(temp_dir) / "proposal.patch"
        patch_text = "\n".join(item.unified_diff.rstrip() for item in patches) + "\n"
        patch_path.write_text(patch_text, encoding="utf-8")

        check_code, _, check_err, _, _ = await _run(
            ["git", "apply", "--check", "--", str(patch_path)],
            cwd=root,
            timeout=30,
        )
        if check_code != 0:
            return ValidationResponse(
                repository=ref.full_name,
                sandbox="docker" if docker_ok else "host-fallback",
                status="patch_invalid",
                patch=PatchApplicationResult(
                    status="invalid",
                    files=[item.path for item in patches],
                    message=_trim(check_err) or "git apply --check rejected the patch.",
                ),
                commands=[],
                passed=False,
                safe_to_propose_pr=False,
                notes=["The proposed unified diff could not be applied cleanly."],
            )

        apply_code, _, apply_err, _, _ = await _run(
            ["git", "apply", "--", str(patch_path)],
            cwd=root,
            timeout=30,
        )
        if apply_code != 0:
            return ValidationResponse(
                repository=ref.full_name,
                sandbox="docker" if docker_ok else "host-fallback",
                status="patch_apply_failed",
                patch=PatchApplicationResult(
                    status="failed",
                    files=[item.path for item in patches],
                    message=_trim(apply_err),
                ),
                commands=[],
                passed=False,
                safe_to_propose_pr=False,
                notes=["Patch check passed but application unexpectedly failed."],
            )

        results: list[ValidationCommandResult] = []
        specs = _validation_specs(root)

        if docker_ok:
            for label, image, command in specs:
                results.append(await _run_docker_command(root, label, image, command))
            sandbox = "docker"
        else:
            # Without Docker, only non-executing Git validation is permitted.
            code, stdout, stderr, duration, status = await _run(["git", "diff", "--check"], cwd=root)
            results.append(
                ValidationCommandResult(
                    command="Git diff check (Docker unavailable)",
                    status=status,
                    exit_code=code,
                    duration_ms=duration,
                    stdout=stdout,
                    stderr=stderr,
                )
            )
            sandbox = "host-safe-fallback"

        commands_passed = bool(results) and all(item.status == "passed" for item in results)
        full_sandbox_validation = docker_ok and commands_passed

        notes = [
            "Patch was applied only inside a temporary validation clone.",
            "Validation containers run without network access or Linux capabilities and can write only inside the disposable repository clone.",
        ]
        if not docker_ok:
            notes.append(
                "Docker was unavailable, so ForgeAI performed only git diff safety validation; this is not sufficient for PR approval."
            )
        elif any(item.status == "failed" for item in results):
            notes.append("At least one sandbox validation command failed.")
        if docker_ok and any(
            "node_modules" in (item.stderr + item.stdout).lower()
            or "module not found" in (item.stderr + item.stdout).lower()
            for item in results
        ):
            notes.append(
                "Network-disabled validation does not install dependencies; dependency-related failures may require a prebuilt validation image."
            )

        return ValidationResponse(
            repository=ref.full_name,
            sandbox=sandbox,
            status="passed" if full_sandbox_validation else "failed",
            patch=PatchApplicationResult(
                status="applied",
                files=[item.path for item in patches],
                message="Patch applied cleanly in the temporary validation workspace.",
            ),
            commands=results,
            passed=full_sandbox_validation,
            safe_to_propose_pr=full_sandbox_validation,
            notes=notes,
        )
