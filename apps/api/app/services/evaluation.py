from __future__ import annotations

import time

from app.schemas.evaluation import (
    BenchmarkCase,
    BenchmarkCaseResult,
    BenchmarkMetrics,
    BenchmarkResponse,
)
from app.services.code_intelligence import search_repository_code
from app.services.observability import execute_workflow


def retrieval_scores(
    ranked_files: list[str],
    expected_files: list[str],
    top_k: int,
) -> tuple[bool, float, float]:
    expected = set(expected_files)
    if not expected:
        return False, 0.0, 0.0

    top1_hit = bool(ranked_files and ranked_files[0] in expected)
    retrieved = ranked_files[:top_k]
    recall = len(expected.intersection(retrieved)) / len(expected)

    reciprocal_rank = 0.0
    for index, path in enumerate(ranked_files, start=1):
        if path in expected:
            reciprocal_rank = 1.0 / index
            break

    return top1_hit, round(recall, 4), round(reciprocal_rank, 4)


def symbol_match(result_symbols: list[str], expected_symbols: list[str]) -> bool | None:
    if not expected_symbols:
        return None
    actual = {item.lower() for item in result_symbols}
    return any(symbol.lower() in actual for symbol in expected_symbols)


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def aggregate_metrics(results: list[BenchmarkCaseResult], top_k: int) -> BenchmarkMetrics:
    if not results:
        return BenchmarkMetrics(
            cases=0,
            top1_accuracy=0.0,
            topk_recall=0.0,
            mean_reciprocal_rank=0.0,
            average_latency_ms=0.0,
        )

    symbol_values = [item.symbol_hit for item in results if item.symbol_hit is not None]
    patch_values = [item.patch_generated for item in results if item.patch_generated is not None]
    validation_values = [item.validation_passed for item in results if item.validation_passed is not None]
    gate_values = [item.gate_correct for item in results if item.gate_correct is not None]

    return BenchmarkMetrics(
        cases=len(results),
        top1_accuracy=_mean([1.0 if item.top1_hit else 0.0 for item in results]),
        topk_recall=_mean([item.topk_recall for item in results]),
        mean_reciprocal_rank=_mean([item.reciprocal_rank for item in results]),
        symbol_accuracy=_mean([1.0 if value else 0.0 for value in symbol_values]) if symbol_values else None,
        average_latency_ms=round(
            sum(item.latency_ms for item in results) / len(results),
            2,
        ),
        patch_generation_rate=_mean([1.0 if value else 0.0 for value in patch_values]) if patch_values else None,
        validation_pass_rate=_mean([1.0 if value else 0.0 for value in validation_values]) if validation_values else None,
        pr_gate_accuracy=_mean([1.0 if value else 0.0 for value in gate_values]) if gate_values else None,
    )


async def evaluate_case(
    case: BenchmarkCase,
    top_k: int,
    run_full_pipeline: bool,
) -> BenchmarkCaseResult:
    started = time.perf_counter()
    search = await search_repository_code(
        repository_url=str(case.repository_url),
        task=case.task,
        limit=max(top_k, 8),
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    ranked_files: list[str] = []
    symbols: list[str] = []
    for evidence in search.results:
        if evidence.path not in ranked_files:
            ranked_files.append(evidence.path)
        symbols.extend(symbol.name for symbol in evidence.symbols)

    top1_hit, recall, rr = retrieval_scores(
        ranked_files,
        case.expected_files,
        top_k,
    )

    patch_generated = None
    validation_passed = None
    pr_gate_open = None
    gate_correct = None

    if run_full_pipeline:
        workflow = await execute_workflow(
            repository_url=str(case.repository_url),
            task=case.task,
            generate_patch=True,
            validate_patch=True,
        )
        patch_generated = bool(workflow.metrics.patch_count)
        validation_passed = bool(workflow.validation and workflow.validation.passed)
        pr_gate_open = workflow.metrics.pr_gate_open
        if case.expected_gate_open is not None:
            gate_correct = pr_gate_open == case.expected_gate_open

    return BenchmarkCaseResult(
        id=case.id,
        repository=search.repository,
        retrieval_mode=search.retrieval_mode,
        latency_ms=latency_ms,
        ranked_files=ranked_files[:10],
        top1_hit=top1_hit,
        topk_recall=recall,
        reciprocal_rank=rr,
        symbol_hit=symbol_match(symbols, case.expected_symbols),
        patch_generated=patch_generated,
        validation_passed=validation_passed,
        pr_gate_open=pr_gate_open,
        gate_correct=gate_correct,
    )


async def run_benchmark(
    cases: list[BenchmarkCase],
    top_k: int = 3,
    run_full_pipeline: bool = False,
) -> BenchmarkResponse:
    results: list[BenchmarkCaseResult] = []
    for case in cases:
        results.append(
            await evaluate_case(
                case=case,
                top_k=top_k,
                run_full_pipeline=run_full_pipeline,
            )
        )

    return BenchmarkResponse(
        metrics=aggregate_metrics(results, top_k),
        results=results,
    )
