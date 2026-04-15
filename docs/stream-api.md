# SSE streaming API (`/stream`, `/stream/mock`)

StockSage exposes **Server-Sent Events** for live pipeline progress. The browser consumes HTML fragments in each event’s `data` field (not JSON), matching what `format_log_entry()` produces for the UI.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/stream?symbol=AAPL` | Live run: validate → download → Crew analysis. Uses `.ui_stream_cache.json` under the symbol’s data directory on success. |
| GET | `/stream/mock?symbol=AAPL&delay_ms=100` | Deterministic mock stream for UI/dev (`STOCKSAGE_APP_MODE=dev`). |

Headers (both): `Content-Type: text/event-stream`, `Cache-Control: no-cache, no-transform`, `Connection: keep-alive`, `X-Accel-Buffering: no`.

## Event framing

Every message follows the [SSE spec](https://html.spec.whatwg.org/multipage/server-sent-events.html): optional `event:` line, `data:` line(s), blank line terminator.

### Initial line

- `retry: 3000` — client reconnect hint (milliseconds).

### Default progress events

Most chunks are **unnamed events** (no `event:` line):

```text
data: <single-line HTML fragment>
```

The HTML is a flattened string (newlines removed). It includes attributes such as `data-stage` and `data-substage` derived from `LogEntry` (`ProcessingStage`, `SubStage`, `StatusType`) defined in `src/core/config/models.py`.

### Named events

| `event` | `data` | When |
|---------|--------|------|
| `stream_error` | Plain text, sanitized user message with `Reference: <id>` | Uncaught exception in the stream, or terminal `COMPLETE` + `FAILED` from the processor. |
| `complete` | Empty | Successful end of stream (no error path taken). |

## Logical payload model (reference)

There is no JSON schema for `data` today; integrators should treat payloads as **opaque HTML** or parse `data-*` attributes if needed. Conceptually each progress event corresponds to one `LogEntry`:

- `stage`: e.g. `starting`, `validating`, `downloading_data`, `analyzing`, `complete`
- `substage`: optional; e.g. `downloading_company_profile`, `analyzing_valuation_ratios`
- `status_type`: `in_progress`, `success`, or `failed`
- `message`: optional human-readable or HTML body

## Caching (live stream only)

On a successful run, the server may persist an ordered list of HTML `data` strings to:

`<output_dir>/<SYMBOL>/.ui_stream_cache.json`

Shape: `{"symbol": "AAPL", "messages": ["...", "..."]}`. Mock stream does not write this file.
