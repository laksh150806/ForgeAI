from __future__ import annotations

import json
import os

import psycopg
from psycopg.rows import dict_row

from app.schemas.observability import WorkflowRunResponse


def database_url() -> str | None:
    return os.getenv("DATABASE_URL") or None


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


async def save_run(run: WorkflowRunResponse) -> bool:
    url = database_url()
    if not url:
        return False

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
    return True


async def recent_runs(limit: int = 20) -> list[dict]:
    url = database_url()
    if not url:
        return []

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
