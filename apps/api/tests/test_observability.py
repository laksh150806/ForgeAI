import asyncio

from app.schemas.observability import TraceStage
from app.services.observability import _trace_stage


async def _success():
    return {"value": 7}


def test_trace_stage_records_success() -> None:
    stages: list[TraceStage] = []

    async def exercise():
        return await _trace_stage(
            stages,
            "demo",
            _success,
            lambda item: {"value": item["value"]},
        )

    result = asyncio.run(exercise())
    assert result["value"] == 7
    assert stages[0].status == "passed"
    assert stages[0].details["value"] == 7
    assert stages[0].duration_ms >= 0
