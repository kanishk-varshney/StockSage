import asyncio

from src.app import main as app_main
from src.core.config.enums import ProcessingStage, StatusType
from src.core.config.models import LogEntry


async def _collect_stream(symbol: str) -> list[str]:
    chunks: list[str] = []
    async for chunk in app_main.stream_logs(symbol):
        chunks.append(chunk)
    return chunks


def test_stream_logs_emits_complete_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(app_main, "OUTPUT_DIR_PATH", tmp_path)

    class FakeProcessor:
        def __init__(self, symbol: str):
            self.symbol = symbol

        async def run(self):
            yield LogEntry(
                stage=ProcessingStage.STARTING,
                status_type=StatusType.IN_PROGRESS,
                symbol=self.symbol,
                message="Starting",
            )

    monkeypatch.setattr(app_main, "StockProcessor", FakeProcessor)
    chunks = asyncio.run(_collect_stream("AAPL"))

    assert chunks[0].startswith("retry:")
    assert any("event: complete" in chunk for chunk in chunks)
    cache_messages = app_main._load_stream_cache("AAPL")
    assert len(cache_messages) == 1
    assert "data-stage=\"starting\"" in cache_messages[0]


def test_stream_logs_sanitizes_errors(monkeypatch, tmp_path):
    monkeypatch.setattr(app_main, "OUTPUT_DIR_PATH", tmp_path)

    class BoomProcessor:
        def __init__(self, symbol: str):
            self.symbol = symbol

        async def run(self):
            raise RuntimeError("sensitive-internal-error")
            yield  # pragma: no cover

    monkeypatch.setattr(app_main, "StockProcessor", BoomProcessor)
    chunks = asyncio.run(_collect_stream("MSFT"))
    combined = "".join(chunks)

    assert "event: stream_error" in combined
    assert "Reference:" in combined
    assert "sensitive-internal-error" not in combined
