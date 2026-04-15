"""Analysis pipeline behaviour when the crew fails (no real LLM calls)."""

from __future__ import annotations

import asyncio
import types

from src.core.config.enums import StatusType
from src.crew.pipeline import AnalysisPipeline


def test_analysis_pipeline_marks_failure_when_kickoff_raises(monkeypatch):
    crew_obj = types.SimpleNamespace(
        tasks=[types.SimpleNamespace(name="validate_data_sanity")],
        task_callback=None,
    )

    async def kickoff_async(**_kw):
        raise RuntimeError("simulated crew failure")

    crew_obj.kickoff_async = kickoff_async

    class StockAnalysisCrewMock:
        def crew(self):
            return crew_obj

    monkeypatch.setattr("src.crew.crew.StockAnalysisCrew", StockAnalysisCrewMock)

    async def collect():
        pipeline = AnalysisPipeline("AAPL")
        entries = []
        async for e in pipeline.run():
            entries.append(e)
        return pipeline, entries

    pipeline, entries = asyncio.run(collect())

    assert pipeline.success is False
    failed_msgs = [e.message for e in entries if e.status_type == StatusType.FAILED]
    assert failed_msgs
    assert any("ref:" in (m or "") for m in failed_msgs)
