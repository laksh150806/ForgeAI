from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

import httpx
from fastapi import HTTPException

from app.schemas.sentry_adapter import (
    SentryAdapterStatus,
    SentrySyncRequest,
    SentrySyncResponse,
)
from app.schemas.telemetry import TelemetryEvent
from app.services.runtime_provider import persist_provider_events


SENTRY_API = "https://sentry.io"
_SHA_RE = re.compile(r"(?<![0-9a-fA-F])([0-9a-fA-F]{7,64})(?![0-9a-fA-F])")


def adapter_status() -> SentryAdapterStatus:
    organization = os.getenv("SENTRY_ORG") or None
    project = os.getenv("SENTRY_PROJECT") or None
    environment = os.getenv("SENTRY_ENVIRONMENT") or None
    token_configured = bool(os.getenv("SENTRY_AUTH_TOKEN"))
    return SentryAdapterStatus(
        configured=bool(organization and project and token_configured),
        organization=organization,
        project=project,
        environment=environment,
        token_configured=token_configured,
        ingestion_mode="project-error-events-full",
    )


def _resolved_config(payload: SentrySyncRequest) -> tuple[str, str, str, str | None]:
    token = os.getenv("SENTRY_AUTH_TOKEN")
    organization = payload.organization or os.getenv("SENTRY_ORG")
    project = payload.project or os.getenv("SENTRY_PROJECT")
    environment = payload.environment or os.getenv("SENTRY_ENVIRONMENT")

    if not token:
        raise HTTPException(
            status_code=503,
            detail="Sentry adapter is not configured. Set SENTRY_AUTH_TOKEN on the ForgeAI API service.",
        )
    if not organization:
        raise HTTPException(
            status_code=422,
            detail="Sentry organization slug is required in the request or SENTRY_ORG.",
        )
    if not project:
        raise HTTPException(
            status_code=422,
            detail="Sentry project slug is required in the request or SENTRY_PROJECT.",
        )
    return token, organization, project, environment


def _dt(value: object) -> datetime | None:
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _tag_value(event: dict, key: str) -> str | None:
    raw = event.get("tags")
    if not isinstance(raw, list):
        return None
    for item in raw:
        if isinstance(item, dict):
            if item.get("key") == key and isinstance(item.get("value"), str):
                return item["value"]
        elif isinstance(item, (list, tuple)) and len(item) >= 2 and item[0] == key:
            value = item[1]
            if isinstance(value, str):
                return value
    return None


def _release_value(event: dict) -> str | None:
    release = event.get("release")
    if isinstance(release, str) and release:
        return release
    if isinstance(release, dict):
        for key in ("version", "shortVersion"):
            value = release.get(key)
            if isinstance(value, str) and value:
                return value
    return _tag_value(event, "release")


def release_commit_sha(event: dict) -> str | None:
    release = _release_value(event)
    if not release:
        return None
    match = _SHA_RE.search(release)
    return match.group(1) if match else None


def _exception_values(event: dict) -> list[dict]:
    entries = event.get("entries")
    if not isinstance(entries, list):
        return []
    values: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("type") != "exception":
            continue
        data = entry.get("data")
        raw_values = data.get("values") if isinstance(data, dict) else None
        if isinstance(raw_values, list):
            values.extend(item for item in raw_values if isinstance(item, dict))
    return values


def _frame_text(frame: dict) -> str | None:
    function = frame.get("function") or frame.get("symbol") or "<unknown>"
    filename = (
        frame.get("filename")
        or frame.get("absPath")
        or frame.get("abs_path")
        or frame.get("module")
        or "<unknown>"
    )
    line = frame.get("lineNo") or frame.get("lineno") or frame.get("line")
    column = frame.get("colNo") or frame.get("colno")
    location = str(filename)
    if line is not None:
        location += f":{line}"
        if column is not None:
            location += f":{column}"
    return f"at {function} ({location})"


def extract_stack_trace(event: dict, max_frames: int = 40) -> str:
    lines: list[str] = []
    for exception in _exception_values(event):
        exc_type = exception.get("type")
        exc_value = exception.get("value")
        heading = ": ".join(
            str(item) for item in (exc_type, exc_value)
            if item not in (None, "")
        )
        if heading:
            lines.append(heading[:1000])

        stacktrace = exception.get("stacktrace")
        frames = stacktrace.get("frames") if isinstance(stacktrace, dict) else None
        if isinstance(frames, list):
            for frame in frames[-max_frames:]:
                if isinstance(frame, dict):
                    text = _frame_text(frame)
                    if text:
                        lines.append(text)
    return "\n".join(lines)[:7000]


def _event_rows(raw: object) -> list[dict]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        data = raw.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    return []


def normalize_sentry_events(
    raw: object,
    *,
    organization: str,
    project: str,
    environment: str | None,
) -> list[TelemetryEvent]:
    events: list[TelemetryEvent] = []
    for item in _event_rows(raw):
        event_id = str(item.get("eventID") or item.get("eventId") or item.get("id") or "")
        if not event_id:
            continue

        observed_at = (
            _dt(item.get("dateCreated"))
            or _dt(item.get("dateReceived"))
            or _dt(item.get("datetime"))
            or _dt(item.get("timestamp"))
            or datetime.now(timezone.utc)
        )
        level = str(item.get("level") or "error").lower()
        title = (
            item.get("title")
            or item.get("message")
            or item.get("culprit")
            or "Sentry error event"
        )
        title_text = str(title).strip()[:3000]
        stack_trace = extract_stack_trace(item)
        message = title_text
        if stack_trace and stack_trace not in title_text:
            message = f"{title_text}\n{stack_trace}"[:8000]

        issue_id = item.get("groupID") or item.get("groupId") or item.get("issueID")
        release = _release_value(item)
        event_environment = _tag_value(item, "environment") or environment
        web_url = item.get("web_url") or item.get("webUrl") or item.get("url")

        events.append(
            TelemetryEvent(
                event_id=uuid5(
                    NAMESPACE_URL,
                    f"sentry-event:{organization}:{project}:{event_id}",
                ),
                observed_at=observed_at,
                source="sentry",
                event_type="error",
                severity=level if level else "error",
                service=project,
                message=message,
                deploy_sha=release_commit_sha(item),
                metadata={
                    "sentry_event_id": event_id,
                    "sentry_issue_id": str(issue_id) if issue_id is not None else None,
                    "sentry_release": release,
                    "sentry_environment": event_environment,
                    "sentry_culprit": item.get("culprit"),
                    "sentry_event_url": web_url,
                    "stack_trace": stack_trace or None,
                },
            )
        )
    return events


def _next_cursor(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        if 'rel="next"' not in part or 'results="true"' not in part:
            continue
        match = re.search(r'cursor="([^"]+)"', part)
        if match:
            return match.group(1)
    return None


async def sync_sentry(payload: SentrySyncRequest) -> SentrySyncResponse:
    token, organization, project, environment = _resolved_config(payload)
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=payload.lookback_minutes)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "ForgeAI/SentryAdapter",
    }
    timeout = httpx.Timeout(25.0)
    events: list[TelemetryEvent] = []
    cursor: str | None = None

    org = quote(organization, safe="")
    proj = quote(project, safe="")
    path = f"/api/0/projects/{org}/{proj}/events/"

    async with httpx.AsyncClient(base_url=SENTRY_API, headers=headers, timeout=timeout) as client:
        while len(events) < payload.event_limit:
            params: dict[str, object] = {
                "full": "true",
                "start": start.isoformat(),
                "end": now.isoformat(),
                "per_page": min(10, payload.event_limit - len(events)),
            }
            if environment:
                params["environment"] = environment
            if cursor:
                params["cursor"] = cursor

            response = await client.get(path, params=params)
            if response.status_code in {401, 403}:
                raise HTTPException(
                    status_code=502,
                    detail="Sentry API rejected access. Check SENTRY_AUTH_TOKEN scopes and organization/project access.",
                )
            if response.status_code == 404:
                raise HTTPException(
                    status_code=502,
                    detail="Sentry organization/project was not found or is not visible to the configured token.",
                )
            if response.status_code == 429:
                raise HTTPException(status_code=429, detail="Sentry API rate limit reached.")
            if response.is_error:
                raise HTTPException(
                    status_code=502,
                    detail=f"Sentry API returned {response.status_code} while fetching project events.",
                )

            page_events = normalize_sentry_events(
                response.json(),
                organization=organization,
                project=project,
                environment=environment,
            )
            events.extend(page_events)

            next_cursor = _next_cursor(response.headers.get("Link"))
            if not next_cursor or not page_events:
                break
            cursor = next_cursor

    events = events[: payload.event_limit]
    result = await persist_provider_events(
        events=events,
        repository_url=str(payload.repository_url) if payload.repository_url else None,
        service=project,
        lookback_minutes=payload.lookback_minutes,
        max_events=payload.event_limit,
        reconstruct=payload.reconstruct_timeline,
    )

    return SentrySyncResponse(
        organization=organization,
        project=project,
        environment=environment,
        error_events=len(events),
        accepted_events=result.accepted_events,
        storage=result.storage,
        ingestion_mode="project-error-events-full",
        timeline=result.timeline,
    )
