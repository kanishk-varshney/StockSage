"""FastAPI application for StockSage UI."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import sys
import asyncio

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


async def stream_logs(symbol: str):
    """Stream log entries as Server-Sent Events."""
    for log_entry in StockProcessor(symbol).run():
        log_html = format_log_entry(log_entry)
        # SSE format: data: <content>\n\n
        yield f"data: {log_html}\n\n"
        await asyncio.sleep(0.1)  # Small delay for smooth streaming
    
    # Send completion event
    yield "event: complete\ndata: \n\n"


@app.get("/stream")
async def stream_symbol_logs(request: Request, symbol: str):
    """Stream log entries as Server-Sent Events."""
    return StreamingResponse(
        stream_logs(symbol),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering for nginx
        }
    )
