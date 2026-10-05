from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from app.schemas.observability import (
    RunMetrics,
    TraceStage,
    WorkflowRunResponse,
)
from app.schemas.planning import PlanResponse
from app.schemas.validation import ValidationResponse
from app.services.code_intelligence import search_repository_code
from app.services.investigation_agent import investigate_repository
from app.services.planning_agent import create_engineering_plan
from app.services.sandbox_validation import validate_patches


async def _trace_stage(
    stages: list[TraceStage],
    name: str,
    operation: Callable[[], Awaitable[Any]],
    details_builder: Callable[[Any], dict[str, str | int | float | bool | None]] | None = None,
) -> Any:
    started = time.perf_counter()
    try:
        result = await operation()
        duration = int((time.perf_counter() - started) * 1000)
        details = details_builder(result) if details_builder else {}
        stages.append(
            TraceStage(
                name=name,
                status="passed",
                duration_ms=duration,
                details=details,
            )
        )
        return result
    except Exception as exc:
        duration = int((time.perf_counter() - started) * 1000)
        stages.append(
            TraceStage(
                name=name,
                status="failed",
                duration_ms=duration,
                error=str(exc)[:1000],
            )
        )
        raise


async def execute_workflow(
    repository_url: str,
    task: str,
    generate_patch: bool = True,
    validate_patch: bool = True,
) -> WorkflowRunResponse:
    run_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    stages: list[TraceStage] = []
    repository_name = repository_url
    retrieval_mode: str | None = None
    evidence_count = 0
    plan: PlanResponse | None = None
    validation: ValidationResponse | None = None

    try:
        search = await _trace_stage(
            stages,
            "retrieval",
            lambda: search_repository_code(repository_url, task, limit=8),
            lambda result: {
                "retrieval_mode": result.retrieval_mode,
                "indexed_files": result.indexed_files,
                "indexed_chunks": result.indexed_chunks,
                "results": len(result.results),
            },
        )
        repository_name = search.repository
        retrieval_mode = search.retrieval_mode
        evidence_count = len(search.results)

        investigation = await _trace_stage(
            stages,
            "investigation",
            lambda: investigate_repository(repository_url, task, limit=6),
            lambda result: {
                "confidence": result.hypothesis.confidence,
                "evidence_count": len(result.evidence),
                "retrieval_mode": result.retrieval_mode,
            },
        )

        plan = await _trace_stage(
            stages,
            "planning_and_patch",
            lambda: create_engineering_plan(repository_url, task, generate_patch),
            lambda result: {
                "confidence": result.plan.confidence,
                "target_files": len(result.plan.target_files),
                "patch_status": result.patch_status,
                "patch_count": len(result.patches),
                "approval_required": result.approval_required,
            },
        )

        if validate_patch and plan.patches:
            validation = await _trace_stage(
                stages,
                "sandbox_validation",
                lambda: validate_patches(repository_url, plan.patches),
                lambda result: {
                    "passed": result.passed,
                    "sandbox": result.sandbox,
                    "commands": len(result.commands),
                    "safe_to_propose_pr": result.safe_to_propose_pr,
                },
            )
        elif validate_patch:
            stages.append(
                TraceStage(
                    name="sandbox_validation",
                    status="skipped",
                    duration_ms=0,
                    details={"reason": "no_patch_generated"},
                )
            )

        failed = sum(stage.status == "failed" for stage in stages)
        gate_open = bool(validation and validation.safe_to_propose_pr)
        if failed:
            status = "failed"
        elif validate_patch and not gate_open:
            status = "blocked"
        else:
            status = "completed"

        return WorkflowRunResponse(
            run_id=run_id,
            repository=repository_name,
            task=task,
            status=status,
            stages=stages,
            metrics=RunMetrics(
                total_duration_ms=int((time.perf_counter() - started) * 1000),
                stages_completed=sum(stage.status == "passed" for stage in stages),
                stages_failed=failed,
                retrieval_mode=retrieval_mode,
                evidence_count=evidence_count,
                patch_count=len(plan.patches) if plan else 0,
                validation_commands=len(validation.commands) if validation else 0,
                pr_gate_open=gate_open,
            ),
            plan=plan,
            validation=validation,
        )
    except Exception:
        return WorkflowRunResponse(
            run_id=run_id,
            repository=repository_name,
            task=task,
            status="failed",
            stages=stages,
            metrics=RunMetrics(
                total_duration_ms=int((time.perf_counter() - started) * 1000),
                stages_completed=sum(stage.status == "passed" for stage in stages),
                stages_failed=sum(stage.status == "failed" for stage in stages),
                retrieval_mode=retrieval_mode,
                evidence_count=evidence_count,
                patch_count=len(plan.patches) if plan else 0,
                validation_commands=len(validation.commands) if validation else 0,
                pr_gate_open=False,
            ),
            plan=plan,
            validation=validation,
        )
