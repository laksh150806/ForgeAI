from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

import httpx
from fastapi import HTTPException

from app.schemas.render_adapter import RenderAdapterStatus, RenderSyncRequest, RenderSyncResponse
from app.schemas.telemetry import TelemetryEvent, TelemetryTimelineRequest
from app.services.telemetry_store import save_events
from app.services.telemetry_timeline import reconstruct_timeline


RENDER_API = "https://api.render.com/v1"


def adapter_status() -> RenderAdapterStatus:
    service_id = os.getenv("RENDER_SERVICE_ID") or None
    workspace_id = os.getenv("RENDER_WORKSPACE_ID") or None
    api_key_configured = bool(os.getenv("RENDER_API_KEY"))
    return RenderAdapterStatus(
        configured=bool(service_id and workspace_id and api_key_configured),
        service_id=service_id,
        workspace_id=workspace_id,
        api_key_configured=api_key_configured,
    )


def _resolved_config(payload: RenderSyncRequest) -> tuple[str, str, str]:
    api_key = os.getenv("RENDER_API_KEY")
    service_id = payload.service_id or os.getenv("RENDER_SERVICE_ID")
    workspace_id = payload.workspace_id or os.getenv("RENDER_WORKSPACE_ID")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Render adapter is not configured. Set RENDER_API_KEY on the ForgeAI API service.",
        )
    if not service_id:
        raise HTTPException(
            status_code=422,
            detail="Render service ID is required in the request or RENDER_SERVICE_ID.",
        )
    if not workspace_id:
        raise HTTPException(
            status_code=422,
            detail="Render workspace ID is required in the request or RENDER_WORKSPACE_ID.",
        )
    return api_key, service_id, workspace_id


def _dt(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _deploy_objects(payload: object) -> list[dict]:
    if not isinstance(payload, list):
        return []
    output: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        nested = item.get("deploy")
        output.append(nested if isinstance(nested, dict) else item)
    return output


def _log_labels(item: dict) -> dict[str, str]:
    labels: dict[str, str] = {}
    raw = item.get("labels")
    if isinstance(raw, list):
        for label in raw:
            if isinstance(label, dict):
                name = label.get("name")
                value = label.get("value")
                if isinstance(name, str) and isinstance(value, str):
                    labels[name] = value
    return labels


def normalize_render_deploys(raw: object, service_id: str) -> list[TelemetryEvent]:
    events: list[TelemetryEvent] = []
    for deploy in _deploy_objects(raw):
        deploy_id = str(deploy.get("id") or "")
        if not deploy_id:
            continue

        status = str(deploy.get("status") or "unknown")
        observed_at = (
            _dt(deploy.get("finishedAt"))
            or _dt(deploy.get("updatedAt"))
            or _dt(deploy.get("startedAt"))
            or _dt(deploy.get("createdAt"))
            or datetime.now(timezone.utc)
        )

        commit = deploy.get("commit")
        commit_sha = None
        commit_message = None
        if isinstance(commit, dict):
            commit_sha = commit.get("id") if isinstance(commit.get("id"), str) else None
            commit_message = commit.get("message") if isinstance(commit.get("message"), str) else None

        failed = status in {"build_failed", "update_failed", "canceled", "cancelled"}
        message = f"Render deploy {deploy_id} finished with status {status}"
        if commit_message:
            message += f": {commit_message.splitlines()[0][:240]}"

        events.append(
            TelemetryEvent(
                event_id=uuid5(NAMESPACE_URL, f"render-deploy:{service_id}:{deploy_id}:{status}"),
                observed_at=observed_at,
                source="render",
                event_type="failure" if failed else "deploy",
                severity="error" if failed else "info",
                service=service_id,
                message=message,
                deploy_sha=commit_sha,
                metadata={
                    "render_deploy_id": deploy_id,
                    "render_status": status,
                    "trigger": deploy.get("trigger"),
                },
            )
        )
    return events


def normalize_render_logs(raw: object, service_id: str) -> list[TelemetryEvent]:
    if not isinstance(raw, dict):
        return []
    logs = raw.get("logs")
    if not isinstance(logs, list):
        return []

    events: list[TelemetryEvent] = []
    for item in logs:
        if not isinstance(item, dict):
            continue
        log_id = str(item.get("id") or "")
        message = str(item.get("message") or "").strip()
        observed_at = _dt(item.get("timestamp"))
        if not log_id or not message or not observed_at:
            continue

        labels = _log_labels(item)
        level = labels.get("level", "info").lower()
        log_type = labels.get("type", "app").lower()
        lowered = message.lower()
        is_error = (
            level in {"error", "critical", "fatal"}
            or "traceback" in lowered
            or "exception" in lowered
            or " error " in f" {lowered} "
        )

        events.append(
            TelemetryEvent(
                event_id=uuid5(NAMESPACE_URL, f"render-log:{service_id}:{log_id}"),
                observed_at=observed_at,
                source="render",
                event_type="error" if is_error else "log",
                severity="error" if is_error else level,
                service=service_id,
                message=message[:8000],
                deploy_sha=None,
                metadata={
                    "render_log_id": log_id,
                    "render_log_type": log_type,
                    "render_labels": labels,
                },
            )
        )
    return events


async def sync_render(payload: RenderSyncRequest) -> RenderSyncResponse:
    api_key, service_id, workspace_id = _resolved_config(payload)
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=payload.lookback_minutes)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "ForgeAI/RenderAdapter",
    }
    timeout = httpx.Timeout(25.0)

    async with httpx.AsyncClient(base_url=RENDER_API, headers=headers, timeout=timeout) as client:
        deploy_response = await client.get(
            f"/services/{service_id}/deploys",
            params={"limit": payload.deploy_limit},
        )
        logs_response = await client.get(
            "/logs",
            params={
                "ownerId": workspace_id,
                "resource": service_id,
                "startTime": start.isoformat(),
                "endTime": now.isoformat(),
                "direction": "forward",
                "limit": payload.log_limit,
            },
        )

    for response, label in ((deploy_response, "deploys"), (logs_response, "logs")):
        if response.status_code in {401, 403}:
            raise HTTPException(
                status_code=502,
                detail=f"Render API rejected access while fetching {label}. Check RENDER_API_KEY permissions.",
            )
        if response.status_code == 429:
            raise HTTPException(
                status_code=429,
                detail=f"Render API rate limit reached while fetching {label}.",
            )
        if response.is_error:
            raise HTTPException(
                status_code=502,
                detail=f"Render API returned {response.status_code} while fetching {label}.",
            )

    deploy_events = [
        event
        for event in normalize_render_deploys(deploy_response.json(), service_id)
        if event.observed_at >= start
    ]
    log_events = normalize_render_logs(logs_response.json(), service_id)
    events_by_id = {str(event.event_id): event for event in [*deploy_events, *log_events]}
    events = sorted(events_by_id.values(), key=lambda event: event.observed_at)

    storage = await save_events(events) if events else ("postgres" if os.getenv("DATABASE_URL") else "memory")

    timeline = None
    if payload.reconstruct_timeline and payload.repository_url:
        timeline = await reconstruct_timeline(
            TelemetryTimelineRequest(
                repository_url=payload.repository_url,
                service=service_id,
                lookback_minutes=payload.lookback_minutes,
                max_events=min(500, max(payload.log_limit + payload.deploy_limit, 20)),
                lookback_commits=20,
                code_limit=6,
            )
        )

    return RenderSyncResponse(
        service_id=service_id,
        workspace_id=workspace_id,
        deploy_events=len(deploy_events),
        log_events=len(log_events),
        accepted_events=len(events),
        storage=storage,
        timeline=timeline,
    )
