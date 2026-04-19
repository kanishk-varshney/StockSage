# Crew Output Guide

This doc explains what Crew produces during a run, what is intermediate, and what is final.

## 1) Input to Crew

Crew run input is:

- `symbol` (example: `AAPL`, `RELIANCE.NS`)

Crew reads data from CSVs under:

- `.market_data/<SYMBOL>/`

Main config sources:

- Agent/task definitions: `src/crew/config/agents.yaml`, `src/crew/config/tasks.yaml`
- Model/runtime config: `src/core/config/config.py` and `.env`
- Crew wiring: `src/crew/crew.py`

## 2) What happens during a run

Execution order (sequential):

1. `analyze_valuation_ratios`
2. `analyze_price_performance`
3. `analyze_financial_health`
4. `analyze_market_sentiment`
5. `review_analysis`
6. `generate_investment_report`

Each task can produce:

- Raw task output (full object/string from Crew task)
- Structured validated output (if schema validation passes)
- Normalized output text (cleaned text used downstream/UI)

## 3) What is intermediate vs final

Intermediate outputs:

- Per-task `rawTaskOutput`
- Per-task `structuredOutput`
- Per-task `normalizedOutputText`
- Run `events` (start, retries, etc.)

Final output (run-level):

- `rawResult` (full final Crew kickoff result object serialized)
- `success` flag
- `complete` flag
- `endedAt` timestamp

## 4) Where output is saved

### A) Complete Crew artifact (primary)

- Path: `.market_data/<SYMBOL>/.analysis_runs/<timestamp>.json`

This is the main artifact to inspect for agent behavior and full outputs.

### B) UI stream cache (secondary, for fast UI replay)

- Path: `.market_data/<SYMBOL>/.ui_stream_cache.json`

This stores rendered stream blocks for UI replay, not full raw Crew internals.

## 5) Key fields inside `.analysis_runs/*.json`

- `version`
- `symbol`
- `appMode`
- `devStreamMode`
- `llmModel`
- `startedAt`, `endedAt`
- `complete`, `success`
- `events[]`
- `tasks[]`
  - `taskName`
  - `substage`
  - `structuredValidated`
  - `rawTaskOutput`
  - `structuredOutput`
  - `normalizedOutputText`
- `rawResult`
- `error` (if failed)

## 6) Quick checks

To confirm a run finished correctly:

- `complete: true`
- `success: true`
- `tasks` contains all 6 expected tasks

To debug failures:

- Check `success: false`
- Check `error.message` and `error.traceback`
- Inspect `events` for retry/rate-limit behavior
