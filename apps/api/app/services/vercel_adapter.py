from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

import httpx
from fastapi import HTTPException

from app.schemas.telemetry import TelemetryEvent
from app.schemas.vercel_adapter import VercelAdapterStatus, VercelSyncRequest, VercelSyncResponse
from app.services.runtime_provider import persist_provider_events


VERCEL_API = "https://api.vercel.com"


def adapter_status() -> VercelAdapterStatus:
    project_id = os.getenv("VERCEL_PROJECT_ID") or None
    team_id = os.getenv("VERCEL_TEAM_ID") or None
    token_configured = bool(os.getenv("VERCEL_TOKEN"))
    return VercelAdapterStatus(
        configured=bool(project_id and token_configured),
        project_id=project_id,
        team_id=team_id,
        token_configured=token_configured,
        runtime_logs_mode="generic-telemetry-or-log-drain",
    )


def _resolved_config(payload: VercelSyncRequest) -> tuple[str, str, str | None]:
    token = os.getenv("VERCEL_TOKEN")
    project_id = payload.project_id or os.getenv("VERCEL_PROJECT_ID")
    team_id = payload.team_id or os.getenv("VERCEL_TEAM_ID")

    if not token:
        raise HTTPException(
            status_code=503,
            detail="Vercel adapter is not configured. Set VERCEL_TOKEN on the ForgeAI API service.",
        )
    if not project_id:
        raise HTTPException(
            status_code=422,
            detail="Vercel project ID is required in the request or VERCEL_PROJECT_ID.",
        )
    return token, project_id, team_id


def _ms_to_dt(value: object) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    if isinstance(value, str):
        try:
            numeric = float(value)
        except ValueError:
            return None
        return datetime.fromtimestamp(numeric / 1000, tz=timezone.utc)
    return None


def _deployments(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("deployments")
    return [item for item in rows if isinstance(item, dict)] if isinstance(rows, list) else []


def _git_sha(deploy: dict) -> str | None:
    meta = deploy.get("meta")
    if isinstance(meta, dict):
        for key in ("githubCommitSha", "gitlabCommitSha", "bitbucketCommitSha"):
            value = meta.get(key)
            if isinstance(value, str) and value:
                return value
    value = deploy.get("gitSource")
    if isinstance(value, dict):
        sha = value.get("sha")
        if isinstance(sha, str) and sha:
            return sha
    return None


def normalize_vercel_deployments(raw: object, project_id: str) -> list[TelemetryEvent]:
    events: list[TelemetryEvent] = []
    for deploy in _deployments(raw):
        deployment_id = str(deploy.get("uid") or deploy.get("id") or "")
        if not deployment_id:
            continue

        state = str(deploy.get("readyState") or deploy.get("state") or "unknown").upper()
        observed_at = (
            _ms_to_dt(deploy.get("ready"))
            or _ms_to_dt(deploy.get("buildingAt"))
            or _ms_to_dt(deploy.get("created"))
            or datetime.now(timezone.utc)
        )
        failed = state in {"ERROR", "CANCELED", "CANCELLED"}
        sha = _git_sha(deploy)
        target = deploy.get("target")
        url = deploy.get("url")
        message = f"Vercel deployment {deployment_id} reached {state}"
        if isinstance(target, str) and target:
            message += f" for {target}"
        if isinstance(url, str) and url:
            message += f" ({url})"

        events.append(
            TelemetryEvent(
                event_id=uuid5(
                    NAMESPACE_URL,
                    f"vercel-deploy:{project_id}:{deployment_id}:{state}",
                ),
                observed_at=observed_at,
                source="vercel",
                event_type="failure" if failed else "deploy",
                severity="error" if failed else "info",
                service=project_id,
                message=message,
                deploy_sha=sha,
                metadata={
                    "vercel_deployment_id": deployment_id,
                    "vercel_state": state,
                    "target": target,
                    "url": url,
                },
            )
        )
    return events


def normalize_vercel_build_events(
    raw: object,
    *,
    project_id: str,
    deployment_id: str,
    deploy_sha: str | None,
) -> list[TelemetryEvent]:
    if not isinstance(raw, list):
        return []

    events: list[TelemetryEvent] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        payload = item.get("payload")
        payload_dict = payload if isinstance(payload, dict) else {}
        text = (
            payload_dict.get("text")
            or item.get("text")
            or payload_dict.get("message")
            or item.get("message")
        )
        if not isinstance(text, str) or not text.strip():
            continue

        created = (
            _ms_to_dt(item.get("created"))
            or _ms_to_dt(payload_dict.get("created"))
            or datetime.now(timezone.utc)
        )
        type_name = str(item.get("type") or payload_dict.get("type") or "build").lower()
        lowered = text.lower()
        is_error = (
            "error" in type_name
            or "fatal" in type_name
            or "failed" in lowered
            or "error:" in lowered
            or "exception" in lowered
        )

        raw_id = item.get("id")
        event_key = str(raw_id) if raw_id is not None else f"{index}:{created.timestamp()}:{text[:80]}"
        events.append(
            TelemetryEvent(
                event_id=uuid5(
                    NAMESPACE_URL,
                    f"vercel-build:{project_id}:{deployment_id}:{event_key}",
                ),
                observed_at=created,
                source="vercel",
                event_type="error" if is_error else "build_log",
                severity="error" if is_error else "info",
                service=project_id,
                message=text[:8000],
                deploy_sha=deploy_sha,
                metadata={
                    "vercel_deployment_id": deployment_id,
                    "vercel_event_type": type_name,
                },
            )
        )
    return events


async def sync_vercel(payload: VercelSyncRequest) -> VercelSyncResponse:
    token, project_id, team_id = _resolved_config(payload)
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=payload.lookback_minutes)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "ForgeAI/VercelAdapter",
    }
    common_params: dict[str, object] = {
        "projectId": project_id,
        "limit": payload.deploy_limit,
    }
    if team_id:
        common_params["teamId"] = team_id

    timeout = httpx.Timeout(25.0)
    async with httpx.AsyncClient(base_url=VERCEL_API, headers=headers, timeout=timeout) as client:
        deployment_response = await client.get("/v6/deployments", params=common_params)

        if deployment_response.status_code in {401, 403}:
            raise HTTPException(
                status_code=502,
                detail="Vercel API rejected access. Check VERCEL_TOKEN and team/project scope.",
            )
        if deployment_response.status_code == 429:
            raise HTTPException(status_code=429, detail="Vercel API rate limit reached.")
        if deployment_response.is_error:
            raise HTTPException(
                status_code=502,
                detail=f"Vercel API returned {deployment_response.status_code} while listing deployments.",
            )

        deployment_events = [
            event
            for event in normalize_vercel_deployments(deployment_response.json(), project_id)
            if event.observed_at >= start
        ]

        build_events: list[TelemetryEvent] = []
        for deploy in _deployments(deployment_response.json()):
            deployment_id = str(deploy.get("uid") or deploy.get("id") or "")
            created = _ms_to_dt(deploy.get("created"))
            if not deployment_id or (created and created < start):
                continue

            params: dict[str, object] = {
                "limit": payload.event_limit_per_deploy,
                "follow": 0,
            }
            if team_id:
                params["teamId"] = team_id

            response = await client.get(
                f"/v3/deployments/{deployment_id}/events",
                params=params,
            )
            if response.status_code in {401, 403}:
                raise HTTPException(
                    status_code=502,
                    detail="Vercel API rejected deployment-event access. Check token scope.",
                )
            if response.status_code == 429:
                raise HTTPException(status_code=429, detail="Vercel API rate limit reached.")
            if response.is_error:
                continue

            build_events.extend(
                normalize_vercel_build_events(
                    response.json(),
                    project_id=project_id,
                    deployment_id=deployment_id,
                    deploy_sha=_git_sha(deploy),
                )
            )

    result = await persist_provider_events(
        events=[*deployment_events, *build_events],
        repository_url=str(payload.repository_url) if payload.repository_url else None,
        service=project_id,
        lookback_minutes=payload.lookback_minutes,
        max_events=(payload.deploy_limit * payload.event_limit_per_deploy) + payload.deploy_limit,
        reconstruct=payload.reconstruct_timeline,
    )

    return VercelSyncResponse(
        project_id=project_id,
        team_id=team_id,
        deployment_events=len(deployment_events),
        build_events=len(build_events),
        accepted_events=result.accepted_events,
        storage=result.storage,
        runtime_logs_mode="generic-telemetry-or-log-drain",
        timeline=result.timeline,
    )
