from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from app.schemas.observability import WorkflowRunResponse


_MEMORY_LIMIT = 50
_memory_runs: deque[dict] = deque(maxlen=_MEMORY_LIMIT)


def database_url() -> str | None:
    value = os.getenv("DATABASE_URL") or None
    if not value:
        return None

    # Supabase connections should always use TLS. The shared session pooler is the
    # recommended free-tier option when the application host needs IPv4 connectivity.
    if "supabase.com" in value and "sslmode=" not in value:
        separator = "&" if "?" in value else "?"
        value = f"{value}{separator}sslmode=require"

    return value


async def _ensure_schema(connection: psycopg.AsyncConnection) -> None:
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS forgeai_runs (
            run_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            repository TEXT NOT NULL,
            task TEXT NOT NULL,
            status TEXT NOT NULL,
            total_duration_ms INTEGER NOT NULL,
            payload JSONB NOT NULL
        )
        """
    )
    await connection.execute(
        """
        CREATE INDEX IF NOT EXISTS forgeai_runs_created_at_idx
        ON forgeai_runs (created_at DESC)
        """
    )


def _remember(run: WorkflowRunResponse) -> None:
    _memory_runs.appendleft(
        {
            "run_id": run.run_id,
            "created_at": datetime.now(timezone.utc),
            "repository": run.repository,
            "task": run.task,
            "status": run.status,
            "total_duration_ms": run.metrics.total_duration_ms,
            "payload": run.model_dump(mode="json"),
        }
    )


async def save_run(run: WorkflowRunResponse) -> str:
    _remember(run)

    url = database_url()
    if not url:
        return "memory"

    async with await psycopg.AsyncConnection.connect(url, autocommit=True) as connection:
        await _ensure_schema(connection)
        await connection.execute(
            """
            INSERT INTO forgeai_runs (
                run_id, repository, task, status, total_duration_ms, payload
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (run_id) DO UPDATE SET
                repository = EXCLUDED.repository,
                task = EXCLUDED.task,
                status = EXCLUDED.status,
                total_duration_ms = EXCLUDED.total_duration_ms,
                payload = EXCLUDED.payload
            """,
            (
                run.run_id,
                run.repository,
                run.task,
                run.status,
                run.metrics.total_duration_ms,
                json.dumps(run.model_dump(mode="json")),
            ),
        )
    return "postgres"


async def recent_runs(limit: int = 20) -> list[dict]:
    url = database_url()
    if not url:
        return [
            {key: value for key, value in item.items() if key != "payload"}
            for item in list(_memory_runs)[:limit]
        ]

    async with await psycopg.AsyncConnection.connect(
        url,
        autocommit=True,
        row_factory=dict_row,
    ) as connection:
        await _ensure_schema(connection)
        cursor = await connection.execute(
            """
            SELECT run_id, created_at, repository, task, status, total_duration_ms
            FROM forgeai_runs
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_run(run_id: str) -> dict | None:
    for item in _memory_runs:
        if item["run_id"] == run_id:
            return item["payload"]

    url = database_url()
    if not url:
        return None

    async with await psycopg.AsyncConnection.connect(
        url,
        autocommit=True,
        row_factory=dict_row,
    ) as connection:
        await _ensure_schema(connection)
        cursor = await connection.execute(
            "SELECT payload FROM forgeai_runs WHERE run_id = %s",
            (run_id,),
        )
        row = await cursor.fetchone()
        return dict(row)["payload"] if row else None


async def database_ready() -> bool:
    url = database_url()
    if not url:
        return True

    try:
        async with await psycopg.AsyncConnection.connect(
            url,
            autocommit=True,
            connect_timeout=4,
        ) as connection:
            await connection.execute("SELECT 1")
        return True
    except Exception:
        return False
