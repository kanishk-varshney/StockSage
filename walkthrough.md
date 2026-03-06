# StockSage Walkthrough: Fast UI Iteration + Production Safety

This guide is the single source of truth for how to iterate quickly on UI/UX in dev mode without waiting 5-10 minutes for full model analysis, while keeping production behavior safe and unchanged.

---

## 1) Runtime Modes and Guarantees

- `STOCKSAGE_APP_MODE=dev`
  - Analyze uses fast stream mode (mock by default).
  - Downloading/progress steps are still shown end-to-end.
  - Uses cached previous run output for the same symbol when available.
- `STOCKSAGE_APP_MODE=prod` (or unset/invalid)
  - Analyze uses the real pipeline (`/stream`).
  - Full download + analysis + model calls run as normal.

Important guarantees:
- If `STOCKSAGE_APP_MODE` is missing, empty, or invalid, app defaults to `prod`.
- UI templates/CSS/JS rendering path is shared between dev and prod.
- Dev mode changes only the stream source/speed, not UI structure.

---

## 2) End-to-End Flow

```mermaid
flowchart LR
analyzeClick[AnalyzeButton] --> runtimeConfig[ServerInjectedRuntimeConfig]
runtimeConfig -->|prod| liveEndpoint[/stream]
runtimeConfig -->|dev+mock| mockEndpoint[/stream/mock]
liveEndpoint --> sseFrames[SSE data frames]
mockEndpoint --> sseFrames
sseFrames --> formatterHTML[format_log_entry HTML blocks]
formatterHTML --> sharedFrontendRender[shared main.js render pipeline]
sharedFrontendRender --> uiCards[Cards Progress Verdict]
```

---

## 3) File Map (What to Edit for UI Work)

- UI shell and structure: `src/app/templates/index.html`
- UI styles: `src/app/static/css/style.css`
- SSE render behavior/progress/card ordering: `src/app/static/js/main.js`
- Card HTML generation and card internals: `src/app/utils/formatters.py`
- Runtime mode + mock/live endpoints: `src/app/main.py`
- Environment mode settings: `src/core/config/config.py`

If you are changing look-and-feel, you usually only need:
- `index.html`
- `style.css`
- `formatters.py`
- sometimes `main.js` for ordering/progress behaviors

---

## 4) Fast Dev Iteration (No UI Debug Controls)

### A) .env setup

In `.env`:

```bash
STOCKSAGE_APP_MODE=dev
STOCKSAGE_DEV_STREAM_MODE=mock
```

Notes:
- `STOCKSAGE_DEV_STREAM_MODE` supports `mock` and `live`.
- In `dev+mock`, UI updates appear quickly and still show realistic staged logs.

### B) How mock stream works

- Endpoint: `/stream/mock`
- It first tries to load cached previous stream output for symbol from:
  - `.market_data/<SYMBOL>/.ui_stream_cache.json`
- If cache exists:
  - Replays cached frames quickly (full step sequence visible).
- If cache does not exist:
  - Falls back to deterministic mock payloads with full stage flow.

### C) How cache gets created

- Every successful real run through `/stream` stores stream HTML frames in:
  - `.market_data/<SYMBOL>/.ui_stream_cache.json`
- That cache is reused in dev mock mode for fast iteration.

---

## 5) 2-Minute UI Iteration Loop

1. Set `.env` to dev mock mode.
2. Start app normally.
3. Run one symbol (e.g., `AAPL`) and review UI immediately (seconds).
4. Edit UI files (`formatters.py`, `style.css`, `index.html`).
5. Refresh and rerun same symbol.
6. Repeat until layout and UX are correct.

When ready for real behavior:
1. Set `.env` to production:
   - `STOCKSAGE_APP_MODE=prod`
2. Restart app.
3. Run full real analysis to validate final end-to-end behavior.

---

## 6) Production Validation Checklist

- `.env` does not set `STOCKSAGE_APP_MODE=dev`.
- Runtime config in browser resolves to `streamMode: live`.
- Analyze requests go to `/stream` (not `/stream/mock`).
- Full download and model analysis run end-to-end.
- UI output matches dev-validated styling and structure.

---

## 7) Troubleshooting

### Dev mode still feels slow
- Check `.env` has:
  - `STOCKSAGE_APP_MODE=dev`
  - `STOCKSAGE_DEV_STREAM_MODE=mock`
- Restart app after env changes.
- Confirm browser request is `/stream/mock`.

### Mock mode not using previous symbol run
- Check cache file exists:
  - `.market_data/<SYMBOL>/.ui_stream_cache.json`
- If missing, run one real analysis once in prod/live mode to seed cache.

### UI mismatch between dev and prod
- Ensure UI edits are only in shared files (`index.html`, `style.css`, `formatters.py`, `main.js`).
- Ensure no dev-only branch modifies HTML structure.

### Progress appears stuck
- Check SSE stream request remains open.
- Confirm stream frames continue arriving.
- Verify analysis step labels are still matched by `main.js`.

---

## 8) Recommended Working Rules

- Keep all debug/fast mode controls out of visible UI.
- Keep mode switching exclusively via `.env`.
- Keep card rendering deterministic in `formatters.py`.
- Keep polarity rules strict:
  - Green = positive
  - Red = negative
  - Yellow = caution/watchout

This setup is designed specifically for fast UI/UX iteration now, with safe promotion to real production behavior by only changing env mode.

---

## 9) Agentic Output Iteration Loop (Crew + Schemas)

Use this loop when refining agent/task prompts and structured outputs before pipeline/UI integration.

1. Run local crew smoke test:
   - `./.venv/bin/python test_crew.py`
2. Confirm task order and progress in console:
   - `START/DONE` lines show per-task run order.
   - ETA hints are shown after the first completed task.
3. Validate structured output parsing:
   - Ensure each task prints schema-aligned JSON under `TASK OUTPUTS`.
   - Fix prompt/schema mismatches first (before UI formatting changes).
4. Re-run after each small prompt/schema update.
5. Only after stable schema output, move to UI formatting iteration.

Tracing notes:
- Crew tracing is enabled in `src/crew/crew.py` (`tracing=True`).
- Inspect traces via your configured CrewAI tracing backend/viewer in your local environment.
- Keep one symbol constant (for example `AAPL`) during prompt/schema iteration for comparable runs.

