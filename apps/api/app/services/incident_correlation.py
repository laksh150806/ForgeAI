from __future__ import annotations

from collections import Counter

from fastapi import HTTPException
from datetime import datetime, timezone
from pathlib import PurePosixPath

from app.schemas.incident import (
    IncidentCorrelationRequest,
    IncidentCorrelationResponse,
    SuspectCommit,
)
from app.services.code_intelligence import query_tokens, search_repository_code
from app.services.git_repository import GitCommitSnapshot, public_repository_checkout, recent_commit_history
from app.services.investigation_agent import investigate_repository
from app.schemas.impact import ImpactAnalysisRequest
from app.services.impact_analysis import analyze_impact


def _runtime_text(payload: IncidentCorrelationRequest) -> str:
    parts = [payload.incident]
    if payload.evidence.error_message:
        parts.append(payload.evidence.error_message)
    if payload.evidence.stack_trace:
        parts.append(payload.evidence.stack_trace)
    parts.extend(payload.evidence.logs)
    return "\n".join(parts)


def _confidence(score: float) -> float:
    if score <= 0:
        return 0.0
    return round(min(0.98, 0.35 + (score / (score + 10.0)) * 0.6), 2)


def score_commit_candidate(
    commit: GitCommitSnapshot,
    runtime_text: str,
    query_terms: list[str],
    evidence_paths: set[str],
    deploy_sha: str | None,
    recency_index: int,
    lookback: int,
) -> tuple[float, list[str], list[str]]:
    lowered_runtime = runtime_text.lower()
    commit_tokens = Counter(query_tokens(
        f"{commit.subject}\n{' '.join(commit.changed_files)}\n{commit.patch[:12000]}"
    ))
    matched_terms = sorted(
        term for term in set(query_terms)
        if term in commit_tokens
    )

    score = min(7.5, len(matched_terms) * 0.9)
    reasons: list[str] = []

    if matched_terms:
        reasons.append(
            "Runtime evidence overlaps commit terms: "
            + ", ".join(matched_terms[:8])
            + "."
        )

    exact_runtime_files: list[str] = []
    for path in commit.changed_files:
        path_lower = path.lower()
        filename = PurePosixPath(path).name.lower()
        if path_lower in lowered_runtime or (len(filename) > 3 and filename in lowered_runtime):
            exact_runtime_files.append(path)

    if exact_runtime_files:
        score += min(6.0, 3.0 * len(exact_runtime_files))
        reasons.append(
            "Runtime evidence directly names changed file(s): "
            + ", ".join(exact_runtime_files[:3])
            + "."
        )

    retrieved_overlap = [path for path in commit.changed_files if path in evidence_paths]
    if retrieved_overlap:
        score += min(6.0, 2.5 * len(retrieved_overlap))
        reasons.append(
            "Changed files overlap ForgeAI's code-level evidence: "
            + ", ".join(retrieved_overlap[:3])
            + "."
        )

    if deploy_sha and (
        commit.sha == deploy_sha
        or commit.sha.startswith(deploy_sha)
        or deploy_sha.startswith(commit.sha[:7])
    ):
        score += 12.0
        reasons.append("The incident explicitly references this deploy/commit SHA.")

    recency_bonus = max(0.0, 1.0 - (recency_index / max(lookback, 1)))
    if recency_bonus:
        score += recency_bonus
        reasons.append("Recent commits receive a small recency prior.")

    return round(score, 3), matched_terms, reasons


async def correlate_incident(
    payload: IncidentCorrelationRequest,
) -> IncidentCorrelationResponse:
    repository_url = str(payload.repository_url)
    runtime_text = _runtime_text(payload)
    terms = query_tokens(runtime_text)

    search = await search_repository_code(
        repository_url=repository_url,
        task=runtime_text,
        limit=payload.code_limit,
    )
    evidence_paths = {item.path for item in search.results}

    depth = max(payload.lookback_commits + 2, 12)
    async with public_repository_checkout(repository_url, depth=depth) as (ref, root, _):
        history = await recent_commit_history(root, limit=payload.lookback_commits)
        head_sha = history[0].sha if history else ""

    ranked: list[SuspectCommit] = []
    for index, commit in enumerate(history):
        score, matching_terms, reasons = score_commit_candidate(
            commit=commit,
            runtime_text=runtime_text,
            query_terms=terms,
            evidence_paths=evidence_paths,
            deploy_sha=payload.evidence.deploy_sha,
            recency_index=index,
            lookback=payload.lookback_commits,
        )
        ranked.append(
            SuspectCommit(
                sha=commit.sha,
                short_sha=commit.sha[:8],
                subject=commit.subject,
                authored_at=datetime.fromtimestamp(
                    commit.authored_at_epoch,
                    tz=timezone.utc,
                ),
                changed_files=commit.changed_files[:20],
                score=score,
                confidence=_confidence(score),
                matching_terms=matching_terms[:12],
                reasons=reasons or ["No strong correlation signal was found for this commit."],
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    top_candidates = ranked[:5]
    suspected = top_candidates[0] if top_candidates and top_candidates[0].score > 1.0 else None

    impact = None
    if suspected is not None:
        try:
            impact = await analyze_impact(
                ImpactAnalysisRequest(
                    repository_url=payload.repository_url,
                    commit_sha=suspected.sha,
                    runtime_text=runtime_text,
                    stack_trace=payload.evidence.stack_trace,
                    lookback_commits=payload.lookback_commits,
                    max_depth=3,
                )
            )
        except HTTPException:
            impact = None

        if impact is not None and impact.blast_radius_score > 0:
            graph_bonus = min(5.0, impact.blast_radius_score / 20.0)
            suspected.score = round(suspected.score + graph_bonus, 3)
            suspected.confidence = _confidence(suspected.score)
            suspected.reasons.append(
                f"Static graph impact adds {graph_bonus:.2f} points: "
                f"blast radius {impact.blast_radius_score:.1f}/100 across "
                f"{len(impact.affected_entrypoints)} affected entrypoint(s)."
            )

    investigation = await investigate_repository(
        repository_url=repository_url,
        task=runtime_text,
        limit=payload.code_limit,
        search_result=search,
    )

    return IncidentCorrelationResponse(
        repository=ref.full_name,
        incident=payload.incident,
        head_sha=head_sha,
        correlation_mode="git-history+runtime-evidence+code-retrieval+blast-radius",
        suspected_commit=suspected,
        candidates=top_candidates,
        investigation=investigation,
        impact=impact,
    )
