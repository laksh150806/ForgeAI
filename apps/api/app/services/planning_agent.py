from __future__ import annotations

import os
from app.schemas.planning import (
    EngineeringPlan,
    PatchFile,
    PlanResponse,
    PlanStep,
)
from app.services.git_repository import public_repository_checkout
from app.services.github_client import GitHubClient, parse_github_repository_url
from app.services.investigation_agent import investigate_repository
from app.services.llm_patch import PatchModel


def _validation_commands(paths: list[str]) -> list[str]:
    commands: list[str] = []
    if any(path.endswith(".py") for path in paths):
        commands.extend(["pytest -q", "python -m compileall ."])
    if any(path.endswith((".ts", ".tsx", ".js", ".jsx")) for path in paths):
        commands.extend(["npm test --if-present", "npm run build --if-present"])
    if not commands:
        commands.append("Run the repository's existing test and build commands.")
    return list(dict.fromkeys(commands))


def build_plan(task: str, investigation) -> EngineeringPlan:
    evidence = investigation.evidence
    target_files = list(dict.fromkeys(item.path for item in evidence[:3]))

    steps: list[PlanStep] = []
    if target_files:
        steps.append(
            PlanStep(
                order=1,
                title="Confirm the failing control flow",
                description=(
                    "Read the highest-ranked implementation surfaces and verify the "
                    "investigation hypothesis against the current code before editing."
                ),
                files=target_files,
                verification="The suspected behavior is traceable to concrete symbols or branches.",
            )
        )
        steps.append(
            PlanStep(
                order=2,
                title="Apply the smallest corrective change",
                description=(
                    "Modify only the code required to address the task while preserving "
                    "existing public behavior outside the failing path."
                ),
                files=target_files[:2],
                verification="The diff is minimal, reviewable, and directly tied to the evidence.",
            )
        )
        steps.append(
            PlanStep(
                order=3,
                title="Add or update regression coverage",
                description=(
                    "Create or extend tests that fail before the correction and pass afterward."
                ),
                files=target_files,
                verification="A regression test demonstrates the reported behavior is fixed.",
            )
        )
    else:
        steps.append(
            PlanStep(
                order=1,
                title="Gather stronger evidence",
                description="No code surface ranked strongly enough to justify a patch.",
                files=[],
                verification="Obtain a stack trace, failing test, or more specific reproduction.",
            )
        )

    risks = [
        "The retrieved code may not capture runtime configuration or environment-specific behavior.",
        "A locally correct change can still cause regressions in callers not present in the top evidence.",
        "Generated patches must be reviewed and validated before any repository write.",
    ]

    return EngineeringPlan(
        summary=f"Evidence-backed plan for: {task}",
        confidence=investigation.hypothesis.confidence,
        target_files=target_files,
        steps=steps,
        risks=risks,
        validation_commands=_validation_commands(target_files),
    )


async def _load_patch_context(
    repository_url: str,
    paths: list[str],
) -> list[dict[str, str]]:
    # Public/demo repositories should not depend on GitHub's anonymous REST quota.
    # Reuse the shallow-clone path used by repository/code intelligence.
    if not os.getenv("GITHUB_TOKEN"):
        result: list[dict[str, str]] = []
        async with public_repository_checkout(repository_url) as (_ref, root, _branch):
            for path in paths[:3]:
                file_path = root / path
                try:
                    if file_path.is_file():
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        result.append({"path": path, "content": content[:18000]})
                except OSError:
                    continue
        return result

    ref = parse_github_repository_url(repository_url)
    client = GitHubClient()
    try:
        repository = await client.repository(ref)
        default_branch = repository.get("default_branch") or "main"
        result = []
        for path in paths[:3]:
            content = await client.file_content(ref, path, default_branch)
            if content is not None:
                result.append({"path": path, "content": content[:18000]})
        return result
    finally:
        await client.close()


async def create_engineering_plan(
    repository_url: str,
    task: str,
    generate_patch: bool = True,
    investigation_result=None,
) -> PlanResponse:
    investigation = investigation_result or await investigate_repository(
        repository_url=repository_url,
        task=task,
        limit=6,
    )
    plan = build_plan(task, investigation)

    patches: list[PatchFile] = []
    patch_status = "not_requested"

    if generate_patch and plan.target_files:
        context = await _load_patch_context(repository_url, plan.target_files)
        raw_patches = await PatchModel().propose(
            task=task,
            hypothesis=investigation.hypothesis.summary,
            files=context,
        )
        if raw_patches:
            allowed = {item["path"] for item in context}
            patches = [
                PatchFile(
                    path=item["path"],
                    rationale=item["rationale"],
                    unified_diff=item["unified_diff"],
                )
                for item in raw_patches
                if item["path"] in allowed
            ]
            patch_status = "generated" if patches else "model_output_rejected"
        else:
            patch_status = "model_unavailable"
    elif generate_patch:
        patch_status = "insufficient_evidence"

    return PlanResponse(
        repository=investigation.repository,
        task=task,
        plan=plan,
        patch_status=patch_status,
        patches=patches,
        approval_required=True,
    )
