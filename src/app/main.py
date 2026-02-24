"""FastAPI application for StockSage UI."""

import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import sys
import threading

# Ensure we can import from src.core
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.processing import StockProcessor
from src.app.utils.formatters import format_log_entry

app = FastAPI(title="StockSage")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Mount static files
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page."""
    return templates.TemplateResponse("index.html", {"request": request})


HEARTBEAT_INTERVAL_SECONDS = 10
SSE_RETRY_MS = 3000


async def stream_logs(symbol: str):
    """Stream log entries as Server-Sent Events with heartbeats."""
    queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
    done = asyncio.Event()
    loop = asyncio.get_running_loop()

    def safe_put(item: tuple[str, str]) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, item)
        except RuntimeError:
            # Request context may have been torn down after client disconnect.
            pass

    def producer() -> None:
        try:
            for log_entry in StockProcessor(symbol).run():
                log_html = format_log_entry(log_entry)
                safe_put(("message", log_html))
        except Exception as exc:
            safe_put(("stream_error", f"Analysis failed: {exc}"))
        finally:
            try:
                loop.call_soon_threadsafe(done.set)
            except RuntimeError:
                pass

    threading.Thread(target=producer, daemon=True).start()

    # Hint client reconnect delay for transient disconnects.
    yield f"retry: {SSE_RETRY_MS}\n\n"

    try:
        while True:
            try:
                event_type, payload = await asyncio.wait_for(
                    queue.get(),
                    timeout=HEARTBEAT_INTERVAL_SECONDS,
                )
            except asyncio.TimeoutError:
                # Keep-alive comment frame so proxies don't treat stream as idle.
                yield ": ping\n\n"
            else:
                if event_type == "stream_error":
                    yield f"event: stream_error\ndata: {payload}\n\n"
                    break
                yield f"data: {payload}\n\n"

            if done.is_set() and queue.empty():
                break
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        yield f"event: stream_error\ndata: Stream interrupted: {exc}\n\n"

    # Send completion event
    yield "event: complete\ndata: \n\n"


@app.get("/stream")
async def stream_symbol_logs(request: Request, symbol: str):
    """Stream log entries as Server-Sent Events."""
    return StreamingResponse(
        stream_logs(symbol),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering for nginx
        }
    )
