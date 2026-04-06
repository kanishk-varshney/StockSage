# Output Preview

This is a representative example of what a completed run can surface in the UI.

## Example recommendation block

```text
Company Name: Apple Inc.
Ticker: AAPL
Sector: Technology
Verdict: BUY
Confidence: High
Summary: Strong profitability, healthy cash generation, and manageable risk profile.
```

## Example SSE events

```text
retry: 3000
data: <div class="workspace-entry" data-status="in_progress" data-stage="starting">...</div>
data: <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 log-analysis"...>...</div>
event: complete
data:
```

Notes:
- Raw internal exceptions are intentionally not shown in browser events.
- Full run artifacts are stored locally under `.market_data/<SYMBOL>/.analysis_runs/`.
