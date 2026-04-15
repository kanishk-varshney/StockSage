# StockSage Architecture

## Runtime Flow

1. `src/app/main.py` receives `/stream?symbol=...` request.
2. `src/core/processing/processor.py` executes validate → download → analyze.
3. `src/core/processing/download_pipeline.py` fetches data and persists CSV files.
4. `src/crew/pipeline.py` runs CrewAI tasks and merges deterministic facts.
5. `src/app/utils/formatters/` converts log entries into UI-safe HTML blocks (one module per analysis card).
6. SSE stream pushes entries to browser (`src/app/static/js/main.js`).

## Module Boundaries

- `src/app`: web layer (FastAPI, templates, static assets, formatting).
- `src/core`: config, validation, data fetching/storage, processing orchestration.
- `src/crew`: CrewAI definitions, tools, facts, output validation/serialization.

## Persistence Contract

- Data root: `.market_data/<SYMBOL>/`
- Contract constants: `src/core/config/data_contracts.py`
- Storage implementation: `src/core/market/storage.py`

## Operational Notes

- Non-critical download failures (e.g., news/trends) are logged and flow continues.
- Analysis failures are surfaced through stage failure entries and SSE termination event.
