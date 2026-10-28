from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

import httpx
from fastapi import HTTPException

from app.schemas.github_runtime_adapter import (
    GitHubRuntimeStatus,
    GitHubRuntimeSyncRequest,
    GitHubRuntimeSyncResponse,
)
from app.schemas.telemetry import TelemetryEvent
from app.services.github_client import parse_github_repository_url
from app.services.runtime_provider import RuntimeProviderSyncResult, persist_provider_events


GITHUB_API = "https://api.github.com"
_SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")
_FAILURE_CONCLUSIONS = {"failure", "timed_out", "startup_failure"}
_DEPLOY_FAILURE_STATES = {"error", "failure"}
_MAX_JOB_SUMMARIES = 3
_MAX_STEP_SUMMARIES = 2


def adapter_status() -> GitHubRuntimeStatus:
    return GitHubRuntimeStatus(
        token_configured=bool(os.getenv("GITHUB_TOKEN")),
        public_repository_reads=True,
        ingestion_mode="deployments+actions-summary",
    )


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None
            else parsed.astimezone(timezone.utc))


def _sha(value: object) -> str | None:
    return value if isinstance(value, str) and _SHA.fullmatch(value) else None


def _identifier(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    result = str(value).strip()
    return result if result else None


def _event_id(*parts: object):
    return uuid5(NAMESPACE_URL, "github-runtime:" + ":".join(str(p) for p in parts))


def _text(value: object, limit: int = 300) -> str:
    return str(value)[:limit] if isinstance(value, (str, int)) else ""


def normalize_github_deployments(
    deployments: list[dict],
    statuses: dict[str, dict | None],
    *,
    repository: str,
    service: str,
    since: datetime,
) -> list[TelemetryEvent]:
    events: list[TelemetryEvent] = []
    for deployment in deployments:
        if not isinstance(deployment, dict):
            continue
        deployment_id = _identifier(deployment.get("id"))
        if not deployment_id:
            continue
        status = statuses.get(deployment_id)
        status = status if isinstance(status, dict) else {}
        observed_at = (
            _timestamp(status.get("created_at"))
            or _timestamp(status.get("updated_at"))
            or _timestamp(deployment.get("created_at"))
        )
        if not observed_at or observed_at < since:
            continue
        state = _text(status.get("state") or "requested", 30).lower()
        if state == "success":
            event_type, severity = "deploy", "info"
        elif state in _DEPLOY_FAILURE_STATES:
            event_type, severity = "failure", "error"
        else:
            # A queued deployment is NOT proof that the code was released.
            event_type, severity = "workflow", "info"
        environment = _text(deployment.get("environment") or "unknown", 100)
        status_id = _identifier(status.get("id")) or "request"
        sha = _sha(deployment.get("sha"))
        events.append(
            TelemetryEvent(
                event_id=_event_id(repository, service, "deployment", deployment_id, status_id),
                observed_at=observed_at,
                source="github",
                event_type=event_type,
                severity=severity,
                service=service,
                message=(
                    f"GitHub deployment {deployment_id} to {environment}: {state}."
                    + (f" {_text(status.get('description'), 500)}" if status.get("description") else "")
                )[:8000],
                deploy_sha=sha,
                metadata={
                    "repository": repository,
                    "github_deployment_id": deployment_id,
                    "github_deployment_status_id": status_id if status else None,
                    "github_status": state,
                    "github_environment": environment,
                    "github_ref": _text(deployment.get("ref"), 200) or None,
                    "github_url": _text(status.get("target_url") or deployment.get("url"), 500) or None,
                },
            )
        )
    return events


def summarize_failed_jobs(jobs: list[dict]) -> list[dict]:
    summaries = []
    for job in jobs:
        if not isinstance(job, dict) or job.get("conclusion") not in _FAILURE_CONCLUSIONS:
            continue
        steps = job.get("steps") if isinstance(job.get("steps"), list) else []
        failed_steps = [
            _text(step.get("name"), 180)
            for step in steps
            if isinstance(step, dict) and step.get("conclusion") in _FAILURE_CONCLUSIONS
        ][:_MAX_STEP_SUMMARIES]
        summaries.append({
            "job_id": _identifier(job.get("id")),
            "job": _text(job.get("name"), 180),
            "conclusion": _text(job.get("conclusion"), 30),
            "failed_steps": failed_steps,
        })
        if len(summaries) >= _MAX_JOB_SUMMARIES:
            break
    return summaries


def normalize_github_runs(
    runs: list[dict],
    failed_jobs: dict[str, list[dict]],
    *,
    repository: str,
    service: str,
    since: datetime,
) -> list[TelemetryEvent]:
    events: list[TelemetryEvent] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        run_id = _identifier(run.get("id"))
        if not run_id:
            continue
        observed_at = (
            _timestamp(run.get("updated_at"))
            or _timestamp(run.get("run_started_at"))
            or _timestamp(run.get("created_at"))
        )
        if not observed_at or observed_at < since:
            continue
        conclusion = _text(run.get("conclusion") or "pending", 30).lower()
        status = _text(run.get("status") or "unknown", 30).lower()
        failed = conclusion in _FAILURE_CONCLUSIONS
        summaries = summarize_failed_jobs(failed_jobs.get(run_id, [])) if failed else []
        name = _text(run.get("name") or "GitHub workflow", 180)
        summary = "; ".join(
            f"{item['job']} ({item['conclusion']})"
            + (": " + ", ".join(item["failed_steps"]) if item["failed_steps"] else "")
            for item in summaries
        )
        message = f"GitHub Actions {name}: {conclusion} ({status})."
        if summary:
            message += f" Failed jobs: {summary}"
        attempt = run.get("run_attempt") if isinstance(run.get("run_attempt"), int) else 1
        events.append(
            TelemetryEvent(
                event_id=_event_id(repository, service, "run", run_id, attempt),
                observed_at=observed_at,
                source="github",
                event_type="ci_failure" if failed else "workflow",
                severity="error" if failed else "info",
                service=service,
                message=message[:8000],
                deploy_sha=_sha(run.get("head_sha")),
                metadata={
                    "repository": repository,
                    "github_workflow_run_id": run_id,
                    "github_run_attempt": attempt,
                    "github_workflow_id": _identifier(run.get("workflow_id")),
                    "github_workflow_name": name,
                    "github_status": status,
                    "github_conclusion": conclusion,
                    "github_branch": _text(run.get("head_branch"), 200) or None,
                    "github_url": _text(run.get("html_url"), 500) or None,
                    "github_failed_jobs": summaries,
                },
            )
        )
    return events


async def _get(client: httpx.AsyncClient, path: str, *, params: dict | None = None):
    try:
        response = await client.get(path, params=params)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="GitHub runtime API is temporarily unreachable.") from exc

    if response.status_code == 429 or (
        response.status_code == 403 and response.headers.get("x-ratelimit-remaining") == "0"
    ):
        raise HTTPException(status_code=429, detail="GitHub API rate limit reached. Retry later or configure GITHUB_TOKEN server-side.")
    if response.status_code in (401, 403, 404):
        raise HTTPException(
            status_code=502,
            detail="GitHub runtime API access denied or repository unavailable. Check repository visibility and read permissions.",
        )
    if response.is_error:
        raise HTTPException(status_code=502, detail=f"GitHub runtime API returned HTTP {response.status_code}.")
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="GitHub runtime API returned malformed JSON.") from exc


async def sync_github_runtime(payload: GitHubRuntimeSyncRequest) -> GitHubRuntimeSyncResponse:
    ref = parse_github_repository_url(str(payload.repository_url))
    repository = ref.full_name
    service = payload.service or repository
    since = datetime.now(timezone.utc) - timedelta(minutes=payload.lookback_minutes)
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ForgeAI/GitHubRuntimeAdapter",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    path = "/repos/" + quote(ref.owner, safe="") + "/" + quote(ref.name, safe="")

    async with httpx.AsyncClient(
        base_url=GITHUB_API, headers=headers, timeout=httpx.Timeout(20.0),
    ) as client:
        repository_info = await _get(client, path)
        branch = repository_info.get("default_branch") if isinstance(repository_info, dict) else None
        if not isinstance(branch, str) or not branch:
            raise HTTPException(status_code=502, detail="GitHub repository default branch was not returned.")

        deployments = await _get(client, path + "/deployments", params={"per_page": payload.deployment_limit})
        runs_payload = await _get(
            client, path + "/actions/runs",
            params={"branch": branch, "per_page": payload.workflow_limit},
        )
        if not isinstance(deployments, list) or not isinstance(runs_payload, dict):
            raise HTTPException(status_code=502, detail="Unexpected GitHub runtime response format.")
        runs = runs_payload.get("workflow_runs")
        if not isinstance(runs, list):
            raise HTTPException(status_code=502, detail="GitHub Actions workflow runs were not returned.")

        statuses: dict[str, dict | None] = {}
        for deployment in deployments[:payload.deployment_limit]:
            if not isinstance(deployment, dict):
                continue
            deployment_id = _identifier(deployment.get("id"))
            if not deployment_id:
                continue
            data = await _get(
                client, path + "/deployments/" + quote(deployment_id, safe="") + "/statuses",
                params={"per_page": 1},
            )
            if not isinstance(data, list):
                raise HTTPException(status_code=502, detail="Unexpected GitHub deployment statuses format.")
            statuses[deployment_id] = data[0] if data and isinstance(data[0], dict) else None

        failed_jobs: dict[str, list[dict]] = {}
        failed_run_budget = payload.failed_job_limit
        for run in runs[:payload.workflow_limit]:
            if not isinstance(run, dict) or run.get("conclusion") not in _FAILURE_CONCLUSIONS:
                continue
            if failed_run_budget <= 0:
                break
            if not (at := _timestamp(run.get("updated_at") or run.get("created_at"))) or at < since:
                continue
            run_id = _identifier(run.get("id"))
            if not run_id:
                continue
            data = await _get(
                client, path + "/actions/runs/" + quote(run_id, safe="") + "/jobs",
                params={"per_page": 50},
            )
            if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
                raise HTTPException(status_code=502, detail="Unexpected GitHub Actions job response format.")
            failed_jobs[run_id] = data["jobs"][:50]
            failed_run_budget -= 1

    deploy_events = normalize_github_deployments(
        deployments[:payload.deployment_limit], statuses,
        repository=repository, service=service, since=since,
    )
    workflow_events = normalize_github_runs(
        runs[:payload.workflow_limit], failed_jobs,
        repository=repository, service=service, since=since,
    )
    if payload.dry_run:
        # Read-only live verification: exercise real provider polling and normalization
        # without touching the telemetry store, database, or correlation pipeline.
        result = RuntimeProviderSyncResult(
            accepted_events=0, storage="dry-run", timeline=None,
        )
    else:
        result = await persist_provider_events(
            events=deploy_events + workflow_events,
            repository_url=str(payload.repository_url),
            service=service,
            lookback_minutes=payload.lookback_minutes,
            max_events=payload.deployment_limit + payload.workflow_limit,
            reconstruct=payload.reconstruct_timeline,
        )
    return GitHubRuntimeSyncResponse(
        repository=repository,
        branch=branch,
        service=service,
        deployment_events=len(deploy_events),
        workflow_events=len(workflow_events),
        ci_failure_events=sum(event.event_type == "ci_failure" for event in workflow_events),
        failed_jobs_summarized=sum(
            len(event.metadata["github_failed_jobs"]) for event in workflow_events
        ),
        accepted_events=result.accepted_events,
        storage=result.storage,
        timeline=result.timeline,
    )
