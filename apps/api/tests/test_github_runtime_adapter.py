import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.github_runtime_adapter import GitHubRuntimeSyncRequest
from app.services import github_runtime_adapter as adapter
from app.services.runtime_provider import RuntimeProviderSyncResult
from app.services.telemetry_timeline import _is_failure, nearest_preceding_deploy
from app.schemas.telemetry import TelemetryTimelineEvent


SINCE = datetime(2026, 10, 1, tzinfo=timezone.utc)
SHA = "a" * 40


def test_public_status_never_exposes_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "testing-never-return-this")
    response = TestClient(app).get("/api/v1/integrations/github-runtime/status")
    assert response.status_code == 200
    data = response.json()
    assert data["token_configured"] is True
    assert data["public_repository_reads"] is True
    assert data["ingestion_mode"] == "deployments+actions-summary"
    assert "testing-never-return-this" not in response.text


def test_normalize_success_and_failure_deployments_and_stable_ids():
    deployments = [
        {"id": 17, "sha": SHA, "environment": "production", "created_at": "2026-10-10T10:00:00Z"},
        {"id": 18, "sha": "refs/heads/main", "environment": "staging", "created_at": "2026-10-10T10:00:00Z"},
    ]
    statuses = {
        "17": {"id": 80, "state": "success", "created_at": "2026-10-10T10:01:00Z"},
        "18": {"id": 81, "state": "failure", "created_at": "2026-10-10T10:02:00Z"},
    }
    args = dict(repository="org/repo", service="api", since=SINCE)
    first = adapter.normalize_github_deployments(deployments, statuses, **args)
    second = adapter.normalize_github_deployments(deployments, statuses, **args)
    assert len(first) == 2
    assert first[0].event_type == "deploy"
    assert first[0].deploy_sha == SHA
    assert first[1].event_type == "failure"
    assert first[1].severity == "error"
    assert first[1].deploy_sha is None
    assert [e.event_id for e in first] == [e.event_id for e in second]
    other_service = adapter.normalize_github_deployments(
        deployments, statuses, repository="org/repo", service="another-api", since=SINCE,
    )
    assert first[0].event_id != other_service[0].event_id


def test_pending_deployment_is_not_a_completed_deploy():
    events = adapter.normalize_github_deployments(
        [{"id": 7, "sha": SHA, "created_at": "2026-10-10T10:00:00Z"}],
        {"7": {"id": 77, "state": "in_progress", "created_at": "2026-10-10T10:03:00Z"}},
        repository="org/repo", service="api", since=SINCE,
    )
    assert events[0].event_type == "workflow"


def test_failed_workflow_job_step_summary_and_ci_not_a_deploy():
    runs = [{
        "id": 123, "run_attempt": 2, "head_sha": SHA,
        "name": "API CI", "status": "completed", "conclusion": "failure",
        "updated_at": "2026-10-10T11:01:00Z", "html_url": "https://github.com/org/repo/actions/runs/123",
    }]
    jobs = {"123": [{
        "id": 5, "name": "Tests", "conclusion": "failure",
        "steps": [{"name": "pytest", "conclusion": "failure"}, {"name": "checkout", "conclusion": "success"}],
    }]}
    kwargs = dict(repository="org/repo", service="api", since=SINCE)
    first = adapter.normalize_github_runs(runs, jobs, **kwargs)[0]
    second = adapter.normalize_github_runs(runs, jobs, **kwargs)[0]
    assert first.event_type == "ci_failure"
    assert first.deploy_sha == SHA
    assert first.metadata["github_failed_jobs"][0]["failed_steps"] == ["pytest"]
    assert "Tests (failure): pytest" in first.message
    assert first.event_id == second.event_id
    changed_service = adapter.normalize_github_runs(
        runs, jobs, repository="org/repo", service="other-api", since=SINCE,
    )[0]
    assert first.event_id != changed_service.event_id
    timeline_event = TelemetryTimelineEvent.model_validate(first.model_dump())
    assert _is_failure(timeline_event)
    assert nearest_preceding_deploy([timeline_event], timeline_event.observed_at) is None


def test_bounded_sync_uses_public_api_shared_pipeline_and_no_logs(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    now = datetime.now(timezone.utc).isoformat()
    requests = []

    def handler(request):
        requests.append((request.url.path, dict(request.url.params), request.headers.get("authorization")))
        p = request.url.path
        if p == "/repos/org/repo":
            data = {"default_branch": "main"}
        elif p == "/repos/org/repo/deployments":
            data = [{"id": 3, "sha": SHA, "environment": "production", "created_at": now}]
        elif p == "/repos/org/repo/deployments/3/statuses":
            data = [{"id": 4, "state": "success", "created_at": now}]
        elif p == "/repos/org/repo/actions/runs":
            data = {"workflow_runs": [
                {"id": 5, "run_attempt": 1, "name": "CI", "status": "completed",
                 "conclusion": "failure", "updated_at": now, "head_sha": SHA}
            ]}
        elif p == "/repos/org/repo/actions/runs/5/jobs":
            data = {"jobs": [{"id": 8, "name": "test", "conclusion": "failure",
                              "steps": [{"name": "pytest", "conclusion": "failure"}]}]}
        else:
            raise AssertionError(p)
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient
    monkeypatch.setattr(adapter.httpx, "AsyncClient",
                        lambda **kwargs: original(transport=transport, **kwargs))
    captured = {}

    async def persist(**kwargs):
        captured.update(kwargs)
        return RuntimeProviderSyncResult(accepted_events=len(kwargs["events"]), storage="memory", timeline=None)

    monkeypatch.setattr(adapter, "persist_provider_events", persist)
    request = GitHubRuntimeSyncRequest(
        repository_url="https://github.com/org/repo", service="my-api",
        deployment_limit=1, workflow_limit=1, failed_job_limit=1, reconstruct_timeline=False,
    )
    result = asyncio.run(adapter.sync_github_runtime(request))
    assert result.accepted_events == 2
    assert result.ci_failure_events == 1
    assert result.failed_jobs_summarized == 1
    assert captured["service"] == "my-api"
    assert captured["reconstruct"] is False
    assert {e.event_type for e in captured["events"]} == {"deploy", "ci_failure"}
    assert len(requests) == 5
    assert all(auth is None for _, _, auth in requests)
    assert dict(requests[1][1])["per_page"] == "1"
    assert dict(requests[2][1])["branch"] == "main"
    assert all("/logs" not in p for p, _, _ in requests)


def test_dry_run_polls_normalizes_but_never_persists(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    def handler(request):
        path = request.url.path
        if path == "/repos/org/repo":
            payload = {"default_branch": "main"}
        elif path == "/repos/org/repo/deployments":
            payload = []
        elif path == "/repos/org/repo/actions/runs":
            payload = {"workflow_runs": [{
                "id": 15, "name": "CI", "conclusion": "success",
                "status": "completed", "updated_at": now, "head_sha": SHA,
            }]}
        else:
            raise AssertionError(path)
        return httpx.Response(200, json=payload)
    original = httpx.AsyncClient
    monkeypatch.setattr(adapter.httpx, "AsyncClient",
                        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    async def forbidden_persist(**kwargs):
        raise AssertionError("dry-run must never enter shared persistent pipeline")
    monkeypatch.setattr(adapter, "persist_provider_events", forbidden_persist)
    data = asyncio.run(adapter.sync_github_runtime(GitHubRuntimeSyncRequest(
        repository_url="https://github.com/org/repo", dry_run=True,
        deployment_limit=1, workflow_limit=1, failed_job_limit=0,
    )))
    assert data.workflow_events == 1
    assert data.accepted_events == 0
    assert data.storage == "dry-run"
    assert data.timeline is None


def test_api_errors_are_sanitized_and_sync_url_is_validated(monkeypatch):
    def handler(request):
        return httpx.Response(403, json={"message": "secret downstream text"})
    original = httpx.AsyncClient
    monkeypatch.setattr(adapter.httpx, "AsyncClient",
                        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    try:
        asyncio.run(adapter.sync_github_runtime(GitHubRuntimeSyncRequest(
            repository_url="https://github.com/org/repo", reconstruct_timeline=False,
        )))
        assert False, "expected GitHub permission failure"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 502
        assert "secret downstream text" not in str(exc)

    response = TestClient(app).post("/api/v1/integrations/github-runtime/sync", json={
        "repository_url": "https://example.com/org/repo", "reconstruct_timeline": False,
    })
    assert response.status_code == 422
