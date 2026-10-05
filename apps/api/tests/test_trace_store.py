from app.services.trace_store import database_url


def test_database_url_absent_by_default(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database_url() is None


def test_database_url_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/test")
    assert database_url() == "postgresql://example/test"
