from __future__ import annotations

from app.schemas.investigation import (
    InvestigationHypothesis,
    InvestigationResponse,
)
from app.services.code_intelligence import search_repository_code


def _confidence(scores: list[float]) -> float:
    if not scores:
        return 0.0
    top = scores[0]
    if len(scores) == 1:
        return min(0.92, 0.45 + top / 25)
    gap = max(0.0, top - scores[1])
    return round(min(0.95, 0.42 + min(top / 35, 0.35) + min(gap / 20, 0.18)), 2)


async def investigate_repository(
    repository_url: str,
    task: str,
    limit: int = 6,
) -> InvestigationResponse:
    search = await search_repository_code(
        repository_url=repository_url,
        task=task,
        limit=limit,
    )

    evidence = search.results
    scores = [item.score for item in evidence]
    confidence = _confidence(scores)

    if evidence:
        lead = evidence[0]
        symbol_names = [symbol.name for symbol in lead.symbols[:3]]
        symbol_text = ", ".join(symbol_names) if symbol_names else "the top-ranked code region"
        summary = (
            f"The most likely implementation surface is {lead.path}, "
            f"especially around {symbol_text}."
        )

        rationale = [
            f"{lead.path} ranked highest for the task with score {lead.score:.2f}.",
            *lead.reasons[:2],
        ]
        if len(evidence) > 1:
            rationale.append(
                "Supporting evidence also appears in "
                + ", ".join(item.path for item in evidence[1:4])
                + "."
            )
    else:
        summary = "ForgeAI could not identify a strong code-level hypothesis from the indexed repository."
        rationale = [
            "No source chunk produced a positive relevance score for the task.",
            "The task may need more specific error text, symbols, or runtime evidence.",
        ]

    actions = [
        "Inspect the top-ranked symbols and their callers before editing code.",
        "Add or locate a regression test that reproduces the reported behavior.",
        "Confirm the suspected control flow with runtime logs or a failing test before patching.",
    ]
    if not evidence:
        actions.insert(0, "Provide a stack trace, error message, or more specific task description.")

    return InvestigationResponse(
        repository=search.repository,
        task=task,
        retrieval_mode=getattr(search, "retrieval_mode", "lexical"),
        hypothesis=InvestigationHypothesis(
            summary=summary,
            confidence=confidence,
            rationale=rationale,
        ),
        evidence=evidence,
        suggested_next_actions=actions,
    )
