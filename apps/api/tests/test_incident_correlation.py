from app.schemas.incident import IncidentCorrelationRequest, RuntimeEvidence
from app.services.git_repository import GitCommitSnapshot
from app.services.incident_correlation import score_commit_candidate


def _commit(sha: str, subject: str, files: list[str], patch: str = "") -> GitCommitSnapshot:
    return GitCommitSnapshot(
        sha=sha,
        authored_at_epoch=1_700_000_000,
        subject=subject,
        changed_files=files,
        patch=patch,
    )


def test_explicit_deploy_sha_is_strong_signal():
    commit = _commit(
        "abcdef1234567890",
        "refactor checkout handler",
        ["apps/api/app/services/checkout.py"],
    )
    score, _, reasons = score_commit_candidate(
        commit=commit,
        runtime_text="checkout returns 500",
        query_terms=["checkout"],
        evidence_paths=set(),
        deploy_sha="abcdef12",
        recency_index=4,
        lookback=10,
    )

    assert score >= 12
    assert any("deploy/commit SHA" in reason for reason in reasons)


def test_runtime_and_retrieval_overlap_rank_changed_file():
    commit = _commit(
        "1234567890abcdef",
        "fix payment timeout",
        ["apps/api/app/services/payments.py"],
        "+async def capture_payment():\n+    raise PaymentTimeout()",
    )
    score, matched, reasons = score_commit_candidate(
        commit=commit,
        runtime_text="PaymentTimeout in apps/api/app/services/payments.py during capture_payment",
        query_terms=["payment", "timeout", "payments", "capture"],
        evidence_paths={"apps/api/app/services/payments.py"},
        deploy_sha=None,
        recency_index=0,
        lookback=10,
    )

    assert score > 6
    assert "payments" in matched
    assert any("directly names changed file" in reason for reason in reasons)
    assert any("code-level evidence" in reason for reason in reasons)


def test_incident_request_bounds_history():
    payload = IncidentCorrelationRequest(
        repository_url="https://github.com/laksh150806/ForgeAI",
        incident="Production requests return 500 after deploy.",
        evidence=RuntimeEvidence(error_message="Internal Server Error"),
        lookback_commits=12,
    )

    assert payload.lookback_commits == 12
