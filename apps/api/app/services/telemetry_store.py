from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timedelta, timezone
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.schemas.telemetry import TelemetryEvent
from app.services.trace_store import database_url


_MEMORY_LIMIT = 500
_memory_events: deque[dict] = deque(maxlen=_MEMORY_LIMIT)


async def _ensure_schema(connection: psycopg.AsyncConnection) -> None:
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS forgeai_telemetry_events (
            event_id UUID PRIMARY KEY,
            observed_at TIMESTAMPTZ NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            source TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            service TEXT,
            message TEXT NOT NULL,
            deploy_sha TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    await connection.execute(
        """
        CREATE INDEX IF NOT EXISTS forgeai_telemetry_observed_at_idx
        ON forgeai_telemetry_events (observed_at DESC)
        """
    )
    await connection.execute(
        """
        CREATE INDEX IF NOT EXISTS forgeai_telemetry_service_observed_idx
        ON forgeai_telemetry_events (service, observed_at DESC)
        """
    )


def _remember(event: TelemetryEvent) -> None:
    _memory_events.appendleft(event.model_dump(mode="python"))


async def save_events(events: list[TelemetryEvent]) -> str:
    for event in events:
        _remember(event)

    url = database_url()
    if not url:
        return "memory"

    async with await psycopg.AsyncConnection.connect(url, autocommit=True) as connection:
        await _ensure_schema(connection)
        for event in events:
            await connection.execute(
                """
                INSERT INTO forgeai_telemetry_events (
                    event_id, observed_at, source, event_type, severity,
                    service, message, deploy_sha, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (event_id) DO UPDATE SET
                    observed_at = EXCLUDED.observed_at,
                    source = EXCLUDED.source,
                    event_type = EXCLUDED.event_type,
                    severity = EXCLUDED.severity,
                    service = EXCLUDED.service,
                    message = EXCLUDED.message,
                    deploy_sha = EXCLUDED.deploy_sha,
                    metadata = EXCLUDED.metadata
                """,
                (
                    event.event_id,
                    event.observed_at,
                    event.source,
                    event.event_type,
                    event.severity,
                    event.service,
                    event.message,
                    event.deploy_sha,
                    json.dumps(event.metadata),
                ),
            )
    return "postgres"


async def recent_events(
    *,
    lookback_minutes: int,
    service: str | None,
    limit: int,
) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    url = database_url()

    if not url:
        rows = [
            item for item in _memory_events
            if item["observed_at"] >= since
            and (service is None or item.get("service") == service)
        ]
        return sorted(rows, key=lambda row: row["observed_at"])[:limit]

    async with await psycopg.AsyncConnection.connect(
        url,
        autocommit=True,
        row_factory=dict_row,
    ) as connection:
        await _ensure_schema(connection)
        if service is None:
            cursor = await connection.execute(
                """
                SELECT event_id, observed_at, source, event_type, severity,
                       service, message, deploy_sha, metadata
                FROM forgeai_telemetry_events
                WHERE observed_at >= %s
                ORDER BY observed_at ASC
                LIMIT %s
                """,
                (since, limit),
            )
        else:
            cursor = await connection.execute(
                """
                SELECT event_id, observed_at, source, event_type, severity,
                       service, message, deploy_sha, metadata
                FROM forgeai_telemetry_events
                WHERE observed_at >= %s AND service = %s
                ORDER BY observed_at ASC
                LIMIT %s
                """,
                (since, service, limit),
            )
        return [dict(row) for row in await cursor.fetchall()]
