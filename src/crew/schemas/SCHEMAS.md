# Schemas Reference

Structured Pydantic output schemas for every Crew task output. Each schema runs a
**two-phase validation pipeline** on the raw LLM response:

1. **Pre-normalisation** — coerce empty/missing fields, map aliases, cap list sizes
2. **Field & post validators** — structural checks only (length caps, format cleanup, type coercion)

> **Note:** Keyword-based content validators (banned terms, direction markers,
> scope-term filters) have been **removed** to let LLM output pass through without
> false-positive rejections. The strict versions are preserved in `_base.py` and
> `_constants.py` for future re-enablement.

```
Raw LLM dict
  │
  ▼
┌──────────────────────────────┐
│  ① Pre-normalisation         │  model_validator(mode="before")
│     Coerce, alias, cap sizes │  Runs BEFORE Pydantic builds the object.
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  ② Field & post validators   │  field_validator + model_validator(mode="after")
│     Structural checks only   │  Length caps, format cleanup, alias normalization.
└──────────────────────────────┘
```

---

## Table of Contents

| # | Section |
|---|---------|
| 1 | [File Layout](#1-file-layout) |
| 2 | [Shared Building Blocks](#2-shared-building-blocks) |
| 3 | [DataSanityOutput](#3-datasanityoutput) |
| 4 | [ValuationOutput](#4-valuationoutput) |
| 5 | [PerformanceOutput](#5-performanceoutput) |
| 6 | [FinancialHealthOutput](#6-financialhealthoutput) |
| 7 | [SentimentOutput](#7-sentimentoutput) |
| 8 | [ReviewOutput](#8-reviewoutput) |
| 9 | [FinalReportOutput](#9-finalreportoutput) |

---

## 1. File Layout

```
schemas/
├── __init__.py            Re-exports every public schema
├── _constants.py          All regex patterns, term tuples, alias maps (backup for strict mode)
├── _items.py              Shared item models (MetricItem, CitationItem, ApplicabilityItem)
├── _base.py               Shared normalisation helpers (backup for strict mode validators)
├── data_sanity.py         DataSanityOutput
├── valuation.py           ValuationOutput
├── performance.py         PerformanceOutput
├── financial_health.py    FinancialHealthOutput
├── sentiment.py           SentimentOutput
├── review.py              ReviewOutput
└── final_report.py        FinalReportOutput
```

**Convention:** Files prefixed with `_` are internal — not imported directly.
All public schemas are available from `src.crew.schemas`.

---

## 2. Shared Building Blocks

### 2a. `_items.py` — Shared Item Models

Three small models reused across multiple output schemas. No validators — pure data containers.

#### `ApplicabilityItem`

> Used by: **DataSanityOutput** (`ratio_applicability`, `valuation_model_applicability`)

| Field | Type | Description |
|---|---|---|
| `name` | `str` (min 1) | Ratio or model name |
| `status` | `"VALID" \| "SOFT_BLOCKED" \| "HARD_BLOCKED"` | Applicability verdict |
| `reason` | `str` | Why it is blocked (optional) |
| `evidence` | `list[str]` | Evidence entries (free-form) |

#### `MetricItem`

> Used by: **ValuationOutput**, **PerformanceOutput**, **FinancialHealthOutput**

| Field | Type | Description |
|---|---|---|
| `label` | `str` | Metric name (e.g. "Trailing P/E") |
| `value` | `str` | Actual value (e.g. "25.3") |
| `note` | `str` | Comparative insight (e.g. "vs sector median 19.2 — 32% premium") |
| `source` | `str` | Data source (e.g. "company_info.csv") |

#### `CitationItem`

> Used by: **SentimentOutput**, **PerformanceOutput**, **FinancialHealthOutput**, **ValuationOutput**, **FinalReportOutput**

| Field | Type | Description |
|---|---|---|
| `title` | `str` | Article headline |
| `publisher` | `str` | Source publisher |
| `url` | `str` | Link |

### 2b. `_constants.py` & `_base.py` — Strict Mode Backup

These files contain all regex patterns, banned-term tuples, alias maps, and assertion
functions from the previous strict validation mode. They are **not currently called**
by any schema but are preserved for future re-enablement.

| File | Contents |
|---|---|
| `_constants.py` | Term tuples (`FH_DIRECTION_MARKERS`, `VALUATION_SUMMARY_BANNED`, etc.), regex patterns, alias maps |
| `_base.py` | `assert_single_sentence()`, `assert_no_banned_terms()`, `assert_has_any_marker()`, `filter_by_allowed_terms()`, `strip_metric_notes_and_filter()`, etc. |

Still actively used by schemas:
- `coerce_summary_text()` — summary fallback coercion
- `normalize_sentiment_signal()` — polarity inference
- `strip_explanatory_tail()` — format cleanup
- `strip_bracket_prefix()`, `strip_count_patterns()` — sentiment format cleanup
- `deterministic_data_sanity_file_statuses()` — filesystem truth for data sanity
- `extract_symbol_from_text()` — ticker extraction
- Growth/caution signal coercion maps from `_constants.py`
- Alias maps (`VERDICT_ALIASES`, `CONFIDENCE_ADJUSTMENT_ALIASES`, `CONFIDENCE_FROM_ADJUSTMENT`)

---

## 3. DataSanityOutput

> **File:** `data_sanity.py`
> **Purpose:** Validates data completeness before any analysis begins. Acts as a gate.

### Fields

| Field | Type | Description |
|---|---|---|
| `summary` | `str` (min 1) | Counts sentence, e.g. `"2 hard blocks, 0 soft blocks identified"` |
| `gate_status` | `"PASS" \| "PASS_WITH_SKIPS" \| "FAIL"` | Overall data-gate verdict |
| `market_context` | `"US" \| "India"` | Market classification |
| `company_type` | `"Bank" \| "Financial" \| "Non-Financial"` | Company classification |
| `validated_files` | `list[str]` | Files confirmed present (`file_name -> ok`) |
| `missing_or_invalid_files` | `list[str]` | Files absent or corrupt (`file_name -> missing`) |
| `critical_issues` | `list[str]` | File-level critical problems |
| `warnings` | `list[str]` | File-level non-critical warnings |
| `ratio_applicability` | `list[ApplicabilityItem]` | 13 ratios: VALID / SOFT_BLOCKED / HARD_BLOCKED |
| `valuation_model_applicability` | `list[ApplicabilityItem]` | 4 models: DCF, DDM, Graham, Relative |

### Validation Pipeline

| Phase | Validator | What It Does |
|---|---|---|
| ① Before | `_normalize_common_data_sanity_shapes` | Coerces summary to counts format, derives gate_status from block counts, overrides file lists with filesystem truth, normalises issue format |
| ② Field | `_validate_counts_only_summary` | Summary must match `N hard blocks, M soft blocks identified` |
| ② Field | `_validate_file_status_format` | `validated_files` / `missing_or_invalid_files` entries must match `file_name -> status` |
| ② Field | `_validate_file_level_issue_scope` | `critical_issues` / `warnings` must be file-level, match `file_name -> issue` |
| ③ After | `_validate_gate_status_consistency` | Gate status must match block counts; issues must not duplicate applicability items |

> **Note:** DataSanityOutput retains all structural validators because its output
> is deterministic (filesystem checks, block counts) — not LLM-generated prose.

---

## 4. ValuationOutput

> **File:** `valuation.py`
> **Purpose:** Ratio-based valuation — is the stock cheap, fair, or expensive?

### Fields

| Field | Type | Description |
|---|---|---|
| `summary` | `str` (min 1) | Valuation stance (e.g. "trades at a 30% PE premium but PEG suggests growth underpriced") |
| `metrics` | `list[MetricItem]` | Up to 5 ratios with actual values and comparative notes |
| `implications` | `list[str]` | Up to 4 pricing conclusions |
| `citations` | `list[CitationItem]` | Sources |

### Validation Pipeline

| Phase | Validator | What It Does |
|---|---|---|
| ① Before | `_normalize_valuation_payload` | Coerces summary (fallback if empty), caps metrics at 5 |
| ② Field | `_validate_summary` | Strips whitespace |
| ② Field | `_validate_metrics_length` | Caps at 5 |
| ② Field | `_validate_implications_length` | Caps at 4 |

---

## 5. PerformanceOutput

> **File:** `performance.py`
> **Purpose:** Price performance and risk profile — returns, volatility, drawdowns vs benchmarks.

### Fields

| Field | Type | Description |
|---|---|---|
| `summary` | `str` (min 1) | Return and risk summary (e.g. "returned +18.3% over 1Y, outperforming S&P by 6pp") |
| `metrics` | `list[MetricItem]` | Up to 5 computed metrics with benchmark comparisons |
| `risk_notes` | `list[str]` | Up to 3 risk observations with actual numbers |
| `citations` | `list[CitationItem]` | Sources |

### Validation Pipeline

| Phase | Validator | What It Does |
|---|---|---|
| ① Before | `_normalize_performance_payload` | Coerces summary, caps metrics at 5 |
| ② Field | `_validate_summary` | Strips whitespace |
| ② Field | `_validate_metrics_length` | Caps at 5 |
| ② Field | `_validate_risk_notes_length` | Caps at 3 |

---

## 6. FinancialHealthOutput

> **File:** `financial_health.py`
> **Purpose:** Business health — revenue growth, margins, leverage, cash flow quality.

### Fields

| Field | Type | Description |
|---|---|---|
| `summary` | `str` (min 1) | Health direction (e.g. "strong health with 8% revenue growth and $112B FCF") |
| `metrics` | `list[MetricItem]` | Up to 5 health metrics with actual numbers and trends |
| `growth_signals` | `list[str]` | Up to 3 directional tokens (improving / stable / deteriorating) with evidence |
| `caution_signals` | `list[str]` | Up to 3 data-backed risk concerns |
| `citations` | `list[CitationItem]` | Sources |

### Validation Pipeline

| Phase | Validator | What It Does |
|---|---|---|
| ① Before | `_normalize_financial_health_payload` | Coerces summary, caps metrics at 5, maps growth signals to canonical tokens (improving/deteriorating/stable), maps caution signals to risk labels |
| ② Field | `_validate_summary` | Strips whitespace |
| ② Field | `_validate_metrics_length` | Caps at 5 |
| ② Field | `_validate_growth_signals_length` | Caps at 3 |
| ② Field | `_validate_caution_signals_length` | Caps at 3 |

---

## 7. SentimentOutput

> **File:** `sentiment.py`
> **Purpose:** Market expectations — analyst consensus %, insider/institutional actions, expectation mismatches.

### Fields

| Field | Type | Description |
|---|---|---|
| `summary` | `str` (min 1) | Expectation state (e.g. "72% Buy consensus with net insider selling creating mismatch") |
| `sentiment_signal` | `"Positive" \| "Neutral" \| "Negative"` | Canonical signal |
| `analyst_consensus` | `str` | Directional statement with numbers (e.g. "72% Buy / 23% Hold / 5% Sell") |
| `key_points` | `list[str]` | Up to 4 data-backed observations |
| `news` | `list[CitationItem]` | Up to 5 expectation-shifting news items |
| `citations` | `list[CitationItem]` | Sources |

### Validation Pipeline

| Phase | Validator | What It Does |
|---|---|---|
| ① Before | `_normalize_sentiment_payload` | Coerces summary/consensus, infers sentiment_signal from polarity markers in combined text |
| ② Field | `_validate_summary` | Strips whitespace |
| ② Field | `_validate_analyst_consensus` | Format cleanup: strips `[TAG] -` prefixes, removes count patterns, truncates to 90 chars |
| ② Field | `_validate_key_points` | Caps at 4 |
| ② Field | `_validate_news_length` | Caps at 5 |
| ③ After | `_reconcile_sentiment_signal` | Re-infers signal from final text and corrects if inconsistent |

---

## 8. ReviewOutput

> **File:** `review.py`
> **Purpose:** Cross-agent consistency check — flags numerical mismatches, contradictions, data sanity violations.

### Fields

| Field | Type | Description |
|---|---|---|
| `summary` | `str` (min 1) | Review outcome (e.g. "All agents consistent" or "PE mismatch between agents") |
| `confidence_adjustment` | `"Increase" \| "Unchanged" \| "Reduce"` | Whether analyses agree or conflict |
| `data_accuracy` | `list[str]` | Up to 5 mismatch observations |
| `watchouts` | `list[str]` | Up to 5 methodology concerns |
| `confirmed_findings` | `list[str]` | Up to 3 confirmed agreements (cleared if issues found) |

### Validation Pipeline

| Phase | Validator | What It Does |
|---|---|---|
| ① Before | `_normalize_review_payload` | Coerces summary, strips explanatory tails from watchouts, caps at 5 |
| ② Field | `_normalize_confidence_adjustment` | Maps aliases: "increase" → "Increase", "unchanged" → "Unchanged", "reduce" → "Reduce" |
| ② Field | `_validate_summary` | Strips whitespace |
| ② Field | `_validate_data_accuracy_length` | Strips tails, caps at 5 |
| ② Field | `_validate_watchouts_length` | Strips tails, caps at 5 |
| ② Field | `_validate_confirmed_findings_size` | Caps at 3 |
| ③ After | `_clear_findings_on_issues` | Clears confirmed_findings if data_accuracy or watchouts are present |

---

## 9. FinalReportOutput

> **File:** `final_report.py`
> **Purpose:** Investment decision — verdict, strengths, risks, catalysts, suitability, and actionable guidance.

### Fields

| Field | Type | Description |
|---|---|---|
| `summary` | `str` (min 1) | Investment conclusion |
| `strengths` | `list[str]` | Up to 4 key strengths (from upstream agents) |
| `risks` | `list[str]` | Up to 4 key risks (from upstream agents) |
| `watch_next` | `list[str]` | Up to 3 upcoming catalysts |
| `best_suited_for` | `list[str]` | Up to 3 investor-profile fits |
| `not_ideal_for` | `list[str]` | Up to 3 investor-profile anti-fits |
| `guidance_for_existing_holders` | `str` | Actionable guidance for current holders |
| `guidance_for_new_buyers` | `str` | Actionable guidance for prospective buyers |
| `verdict` | `"STRONG BUY" \| "BUY" \| "HOLD" \| "SELL" \| "STRONG SELL"` | Final verdict |
| `confidence` | `"High" \| "Medium" \| "Low"` | Confidence (must match reviewer) |
| `citations` | `list[CitationItem]` | Sources |

### Validation Pipeline

| Phase | Validator | What It Does |
|---|---|---|
| ① Before | `_map_final_guidance_aliases` | Maps `key_reasons` → `strengths`, `key_risks` → `risks`, coerces summary/guidance, derives confidence from confidence_adjustment |
| ② Field | `_validate_summary` | Strips whitespace |
| ② Field | `_validate_suitability_lists` | Strips tails, caps at 3 |
| ② Field | `_validate_strengths` | Strips tails, caps at 4 |
| ② Field | `_validate_risks` | Strips tails, caps at 4 |
| ② Field | `_validate_watch_next` | Strips tails, caps at 3 |
| ② Field | `_validate_guidance_fields` | Strips whitespace |
| ② Field | `_normalize_verdict` | Uppercases, maps aliases (e.g. "STRONG-BUY" → "STRONG BUY") |
| ② Field | `_normalize_confidence` | Capitalises ("high" → "High") |

---

## Design Principles

| Principle | How It's Applied |
|---|---|
| **Coerce first, let through second** | Pre-normalisers fix what they can (aliases, missing fields, format). Field validators only cap sizes and clean formatting — they don't reject based on keywords |
| **Structural over semantic** | Validators enforce structure (list caps, type coercion, format patterns) not content quality. Content quality is driven by prompt engineering in tasks.yaml |
| **Insight-driven prompts** | Each task prompt specifies exact metrics to compute, exact comparisons to make, and exact insight format. The schema just ensures the output structure is valid |
| **Deterministic where possible** | DataSanityOutput uses filesystem checks and block counts — not LLM prose. Sentiment signal is inferred from polarity markers, not trusted from LLM |
| **Capped lists** | Every list field has a hard maximum to prevent verbose output |
| **Constants preserved** | All term lists, regex patterns, and strict-mode functions are preserved in `_constants.py` and `_base.py` for future re-enablement |
