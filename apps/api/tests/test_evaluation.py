from app.schemas.evaluation import BenchmarkCaseResult
from app.services.evaluation import aggregate_metrics, retrieval_scores, symbol_match


def test_retrieval_scores_top1_and_recall() -> None:
    top1, recall, rr = retrieval_scores(
        ["auth.py", "routes.py", "tokens.py"],
        ["auth.py", "tokens.py"],
        top_k=3,
    )
    assert top1 is True
    assert recall == 1.0
    assert rr == 1.0


def test_retrieval_scores_rank_penalty() -> None:
    top1, recall, rr = retrieval_scores(
        ["other.py", "auth.py"],
        ["auth.py"],
        top_k=2,
    )
    assert top1 is False
    assert recall == 1.0
    assert rr == 0.5


def test_symbol_match_is_case_insensitive() -> None:
    assert symbol_match(["JWTMiddleware", "validate_token"], ["jwtmiddleware"]) is True
    assert symbol_match(["validate_token"], []) is None


def test_aggregate_metrics() -> None:
    results = [
        BenchmarkCaseResult(
            id="a",
            repository="o/r",
            retrieval_mode="lexical",
            latency_ms=100,
            ranked_files=["a.py"],
            top1_hit=True,
            topk_recall=1.0,
            reciprocal_rank=1.0,
            symbol_hit=True,
            patch_generated=True,
            validation_passed=True,
            pr_gate_open=True,
            gate_correct=True,
        ),
        BenchmarkCaseResult(
            id="b",
            repository="o/r",
            retrieval_mode="lexical",
            latency_ms=300,
            ranked_files=["b.py"],
            top1_hit=False,
            topk_recall=0.5,
            reciprocal_rank=0.5,
            symbol_hit=False,
            patch_generated=False,
            validation_passed=False,
            pr_gate_open=False,
            gate_correct=True,
        ),
    ]

    metrics = aggregate_metrics(results, top_k=3)
    assert metrics.top1_accuracy == 0.5
    assert metrics.topk_recall == 0.75
    assert metrics.mean_reciprocal_rank == 0.75
    assert metrics.average_latency_ms == 200
    assert metrics.pr_gate_accuracy == 1.0


def test_benchmark_can_reuse_one_repository_index_shape() -> None:
    from app.services.code_intelligence import CodeChunk, RepositoryCodeIndex

    index = RepositoryCodeIndex(
        repository="owner/repo",
        indexed_files=1,
        chunks=[
            CodeChunk(
                path="app/auth.py",
                language="Python",
                text="def validate_token(): pass",
                symbols=[],
                tokens=["validate", "token"],
            )
        ],
    )
    assert index.repository == "owner/repo"
    assert index.indexed_files == 1
    assert len(index.chunks) == 1



def test_aggregate_metrics_reports_impact_quality_separately() -> None:
    results = [
        BenchmarkCaseResult(
            id="impact-a",
            repository="o/r",
            retrieval_mode="lexical",
            latency_ms=120,
            ranked_files=["impact.py"],
            top1_hit=True,
            topk_recall=1.0,
            reciprocal_rank=1.0,
            symbol_hit=True,
            impact_changed_symbol_hit=True,
            impact_runtime_symbol_hit=True,
            impact_entrypoint_hit=True,
            blast_radius_score=62.5,
            impact_confidence=0.67,
        ),
        BenchmarkCaseResult(
            id="impact-b",
            repository="o/r",
            retrieval_mode="lexical",
            latency_ms=180,
            ranked_files=["incident.py"],
            top1_hit=True,
            topk_recall=1.0,
            reciprocal_rank=1.0,
            symbol_hit=True,
            impact_changed_symbol_hit=True,
            impact_runtime_symbol_hit=False,
            impact_entrypoint_hit=True,
            blast_radius_score=37.5,
            impact_confidence=0.48,
        ),
    ]

    metrics = aggregate_metrics(results, top_k=3)
    assert metrics.impact_cases == 2
    assert metrics.impact_changed_symbol_accuracy == 1.0
    assert metrics.impact_runtime_symbol_accuracy == 0.5
    assert metrics.impact_entrypoint_accuracy == 1.0
    assert metrics.average_blast_radius_score == 50.0


def test_impact_seed_cases_are_pinned_and_graph_labeled() -> None:
    from app.routes.evaluation import IMPACT_SEED_CASES

    assert len(IMPACT_SEED_CASES) == 2
    for case in IMPACT_SEED_CASES:
        assert case.impact_commit_sha == "3dd89c8b4ebebf24a70aef672f8c13846853eab8"
        assert case.impact_runtime_text
        assert case.expected_changed_symbols
        assert case.expected_runtime_symbols
        assert case.expected_affected_entrypoints
        assert case.impact_lookback_commits <= 100
