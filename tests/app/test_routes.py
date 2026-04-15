from fastapi.testclient import TestClient

from src.app.main import app


def test_index_route_returns_html():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_stream_route_sets_sse_headers():
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
