import asyncio
import sys
import types

from src.core.config.enums import ProcessingStage, StatusType, SubStage
from src.core.config.models import LogEntry, ValidationResult
from src.core.processing import processor as proc


async def _collect_processor(symbol: str) -> list[LogEntry]:
    entries: list[LogEntry] = []
    async for entry in proc.StockProcessor(symbol).run():
        entries.append(entry)
    return entries


def test_processor_stops_after_validation_failure(monkeypatch):
    monkeypatch.setattr(
        proc,
        "validate_symbol",
        lambda _symbol: ValidationResult(is_valid=False, error_message="bad symbol"),
    )

    class GuardDownloadPipeline:
        def __init__(self, _symbol: str):
            raise AssertionError("download should not run for invalid symbols")

    monkeypatch.setattr(proc, "DownloadPipeline", GuardDownloadPipeline)
    entries = asyncio.run(_collect_processor("BAD"))

    assert any(
        e.stage == ProcessingStage.VALIDATING
        and e.substage == SubStage.VALIDATING_SYMBOL
        and e.status_type == StatusType.FAILED
        for e in entries
    )
    assert all(e.stage != ProcessingStage.DOWNLOADING_DATA for e in entries)


def test_processor_happy_path_runs_to_complete(monkeypatch):
    monkeypatch.setattr(proc, "validate_symbol", lambda _symbol: ValidationResult(is_valid=True))

    class StockDataStub:
        @staticmethod
        def is_valid() -> bool:
            return True

    class FakeDownloadPipeline:
        def __init__(self, symbol: str):
            self.symbol = symbol
            self.stock_data = StockDataStub()

        def run(self):
            yield LogEntry(
                stage=ProcessingStage.DOWNLOADING_DATA,
                substage=SubStage.DOWNLOADING_COMPANY_PROFILE,
                status_type=StatusType.SUCCESS,
                symbol=self.symbol,
                message="ok",
            )

    monkeypatch.setattr(proc, "DownloadPipeline", FakeDownloadPipeline)

    class FakeAnalysisPipeline:
        def __init__(self, symbol: str):
            self.symbol = symbol
            self.success = True

        async def run(self):
            yield LogEntry(
                stage=ProcessingStage.ANALYZING,
                substage=SubStage.GENERATING_INVESTMENT_REPORT,
                status_type=StatusType.SUCCESS,
                symbol=self.symbol,
                message="report",
            )

    fake_crew_pipeline_module = types.SimpleNamespace(AnalysisPipeline=FakeAnalysisPipeline)
    monkeypatch.setitem(sys.modules, "src.crew.pipeline", fake_crew_pipeline_module)

    entries = asyncio.run(_collect_processor("AAPL"))

    assert entries[-1].stage == ProcessingStage.COMPLETE
    assert entries[-1].status_type != StatusType.FAILED
    assert any(e.stage == ProcessingStage.ANALYZING for e in entries)
