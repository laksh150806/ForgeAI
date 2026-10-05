from app.services.trace_store import database_url


def test_database_url_absent_by_default(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database_url() is None


def test_database_url_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/test")
    assert database_url() == "postgresql://example/test"


def test_memory_trace_store_round_trip(monkeypatch) -> None:
    import asyncio

    from app.schemas.observability import RunMetrics, WorkflowRunResponse
    from app.services import trace_store

    monkeypatch.delenv("DATABASE_URL", raising=False)
    trace_store._memory_runs.clear()

    run = WorkflowRunResponse(
        run_id="trace-test-1",
        repository="owner/repo",
        task="Find the failing path",
        status="completed",
        stages=[],
        metrics=RunMetrics(
            total_duration_ms=123,
            stages_completed=0,
            stages_failed=0,
        ),
    )

    assert asyncio.run(trace_store.save_run(run)) == "memory"
    rows = asyncio.run(trace_store.recent_runs(10))
    assert rows[0]["run_id"] == "trace-test-1"
    payload = asyncio.run(trace_store.get_run("trace-test-1"))
    assert payload["task"] == "Find the failing path"
    assert payload["status"] == "completed"
    assert payload["metrics"]["total_duration_ms"] == 123


def test_supabase_database_url_enforces_ssl(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres.project:secret@aws-0-region.pooler.supabase.com:5432/postgres",
    )
    value = database_url()
    assert "sslmode=require" in value


def test_database_url_keeps_existing_sslmode(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres.project:secret@aws-0-region.pooler.supabase.com:5432/postgres?sslmode=verify-full",
    )
    value = database_url()
    assert value.count("sslmode=") == 1
