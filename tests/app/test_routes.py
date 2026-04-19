from fastapi.testclient import TestClient

from src.app import main as app_main
from src.app.main import app
from src.core.config.enums import ProcessingStage, StatusType


class _StubProcessor:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    async def run(self):
        from src.core.config.models import LogEntry

        yield LogEntry(
            stage=ProcessingStage.COMPLETE,
            substage=None,
            status_type=StatusType.COMPLETED,
            message="stub",
        )


def test_index_route_returns_html():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_stream_route_sets_sse_headers(monkeypatch):
    monkeypatch.setattr(app_main, "StockProcessor", _StubProcessor)
    client = TestClient(app)
    with client.stream("GET", "/stream", params={"symbol": "AAPL"}) as response:
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")
        assert response.headers.get("cache-control") == "no-cache, no-transform"
        assert response.headers.get("x-accel-buffering") == "no"


def test_stream_mock_route_sets_sse_headers():
    client = TestClient(app)
    with client.stream("GET", "/stream/mock", params={"symbol": "AAPL", "delay_ms": 1}) as response:
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")
        assert response.headers.get("cache-control") == "no-cache, no-transform"
        assert response.headers.get("x-accel-buffering") == "no"
