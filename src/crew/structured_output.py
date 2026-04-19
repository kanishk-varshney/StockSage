# SPDX-License-Identifier: MIT
"""Structured-output schema registry, validation, and serializers."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from src.crew.schemas import (
    DataSanityOutput,
    FinalReportOutput,
    FinancialHealthOutput,
    PerformanceOutput,
    ReviewOutput,
    SentimentOutput,
    ValuationOutput,
)

TASK_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "validate_data_sanity": DataSanityOutput,
    "analyze_valuation_ratios": ValuationOutput,
    "analyze_price_performance": PerformanceOutput,
    "analyze_financial_health": FinancialHealthOutput,
    "analyze_market_sentiment": SentimentOutput,
    "review_analysis": ReviewOutput,
    "generate_investment_report": FinalReportOutput,
}


def output_model_for_task(task_name: str) -> type[BaseModel] | None:
    """Return the Pydantic model class for *task_name*, or ``None``."""
    return TASK_OUTPUT_MODELS.get(task_name)


def _hydrate_missing_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Backfill the ``summary`` key when the LLM omits it.

    Probes common alternative keys (overview, conclusion, verdict, etc.) and
    falls back to a generic placeholder to prevent ``min_length`` failures.
    """
    if payload.get("summary") and str(payload.get("summary")).strip():
        return payload

    for key in ("overview", "conclusion", "verdict", "thesis", "analysis", "headline"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            payload["summary"] = value.strip()
            return payload

    payload["summary"] = "Summary not provided by model."
    return payload


def validate_task_output(task_name: str | None, task_output: Any) -> BaseModel | None:
    """Attempt to produce a validated Pydantic model from a CrewAI ``TaskOutput``.

    Tries three strategies in order:

    1. ``task_output.pydantic`` -- already parsed by CrewAI's ``output_pydantic``.
    2. ``task_output.json_dict`` -- raw JSON dict; hydrates missing summary then
       validates.
    3. ``task_output.raw`` -- raw LLM text; strips code fences, parses JSON, then
       validates.

    Returns ``None`` when the task has no registered model or when all strategies
    fail.
    """
    if not task_name:
        return None
    model_cls = output_model_for_task(task_name)
    if model_cls is None:
        return None

    pydantic_obj = getattr(task_output, "pydantic", None)
    if isinstance(pydantic_obj, model_cls):
        return pydantic_obj
    if isinstance(pydantic_obj, BaseModel):
        try:
            return model_cls.model_validate(pydantic_obj.model_dump())
        except (ValidationError, Exception):
            pass

    json_dict = getattr(task_output, "json_dict", None)
    if isinstance(json_dict, dict):
        try:
            return model_cls.model_validate(_hydrate_missing_summary(dict(json_dict)))
        except (ValidationError, Exception):
            pass

    raw = getattr(task_output, "raw", "")
    if isinstance(raw, str) and raw.strip():
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            return model_cls.model_validate_json(text)
        except (ValidationError, Exception):
            pass
        try:
            maybe_dict = json.loads(text)
            if isinstance(maybe_dict, dict):
                maybe_dict = _hydrate_missing_summary(maybe_dict)
            return model_cls.model_validate(maybe_dict)
        except (json.JSONDecodeError, ValidationError, Exception):
            pass

    return None


# ── Serialization helpers ──────────────────────────────────────────────────────


def _serialize_metrics(metrics: list[Any]) -> list[str]:
    """Format ``MetricItem`` objects: ``label: value | note [source: ...]``."""
    lines: list[str] = []
    for metric in metrics[:5]:
        source_suffix = f" [source: {metric.source}]" if getattr(metric, "source", "") else ""
        note_suffix = f" | {metric.note}" if getattr(metric, "note", "") else ""
        lines.append(f"{metric.label}: {metric.value}{note_suffix}{source_suffix}")
    return lines


def _serialize_citations(citations: list[Any], *, label: str = "Source") -> list[str]:
    """Format ``CitationItem`` objects: ``label: title | publisher | url``."""
    lines: list[str] = []
    for item in citations[:4]:
        title = getattr(item, "title", "").strip() or "reference"
        publisher = getattr(item, "publisher", "").strip() or "source"
        url = getattr(item, "url", "").strip()
        if url:
            lines.append(f"{label}: {title} | {publisher} | {url}")
    return lines


def serialize_structured_output(task_name: str | None, model: BaseModel) -> str:
    """Convert a validated Pydantic output model into multi-line plaintext.

    Each schema type formats its fields with labelled prefixes
    (e.g. ``Structured Summary:``, ``Risk Note:``, ``VERDICT:``).
    Returns an empty string for unrecognised model types.
    """
    if isinstance(model, DataSanityOutput):
        lines = [
            f"Structured Summary: {model.summary}",
            f"Gate Status: {model.gate_status}",
            f"Market Context: {model.market_context}",
            f"Company Type: {model.company_type}",
        ]
        lines.extend(f"Validated File: {item}" for item in model.validated_files[:10])
        lines.extend(
            f"Missing/Invalid File: {item}" for item in model.missing_or_invalid_files[:10]
        )
        lines.extend(f"Critical Issue: {item}" for item in model.critical_issues[:10])
        lines.extend(f"Warning: {item}" for item in model.warnings[:10])
        lines.extend(
            f"Ratio Applicability: {item.name} -> {item.status}"
            + (f" | {item.reason}" if item.reason else "")
            for item in model.ratio_applicability[:20]
        )
        lines.extend(
            f"Valuation Model Applicability: {item.name} -> {item.status}"
            + (f" | {item.reason}" if item.reason else "")
            for item in model.valuation_model_applicability[:20]
        )
        return "\n".join(lines)

    if isinstance(model, ValuationOutput):
        lines = [f"Structured Summary: {model.summary}", *_serialize_metrics(model.metrics)]
        lines.extend(f"Implication: {line}" for line in model.implications[:3])
        lines.extend(_serialize_citations(model.citations))
        return "\n".join(lines)

    if isinstance(model, PerformanceOutput):
        lines = [f"Structured Summary: {model.summary}", *_serialize_metrics(model.metrics)]
        lines.extend(f"Risk Note: {line}" for line in model.risk_notes[:3])
        lines.extend(_serialize_citations(model.citations))
        return "\n".join(lines)

    if isinstance(model, FinancialHealthOutput):
        lines = [f"Structured Summary: {model.summary}", *_serialize_metrics(model.metrics)]
        lines.extend(f"Growth Signal: {line}" for line in model.growth_signals[:3])
        lines.extend(f"Caution Signal: {line}" for line in model.caution_signals[:3])
        lines.extend(_serialize_citations(model.citations))
        return "\n".join(lines)

    if isinstance(model, SentimentOutput):
        lines = [
            f"Structured Summary: {model.summary}",
            f"Sentiment Signal: {model.sentiment_signal}",
        ]
        if model.analyst_consensus:
            lines.append(f"Analyst Consensus: {model.analyst_consensus}")
        lines.extend(f"Sentiment Point: {line}" for line in model.key_points[:4])
        lines.extend(_serialize_citations(model.news, label="News"))
        lines.extend(_serialize_citations(model.citations))
        return "\n".join(lines)

    if isinstance(model, ReviewOutput):
        lines = [
            f"Structured Summary: {model.summary}",
            f"Confidence Adjustment: {model.confidence_adjustment}",
        ]
        lines.extend(f"Data Accuracy: {line}" for line in model.data_accuracy[:3])
        lines.extend(f"Watchout: {line}" for line in model.watchouts[:3])
        lines.extend(f"Confirmed: {line}" for line in model.confirmed_findings[:3])
        return "\n".join(lines)

    if isinstance(model, FinalReportOutput):
        lines = [
            f"Structured Summary: {model.summary}",
            *[f"Strength: {line}" for line in model.strengths[:4]],
            *[f"Risk: {line}" for line in model.risks[:4]],
            *[f"Watch: {line}" for line in model.watch_next[:3]],
            *[f"Best Suited For: {line}" for line in model.best_suited_for[:3]],
            *[f"Not Ideal For: {line}" for line in model.not_ideal_for[:3]],
            f"Guidance For Existing Holders: {model.guidance_for_existing_holders}",
            f"Guidance For New Buyers: {model.guidance_for_new_buyers}",
            f"VERDICT: {model.verdict or 'INCONCLUSIVE'} | Confidence: {model.confidence or 'N/A'}",
            *_serialize_citations(model.citations),
        ]
        return "\n".join(lines)

    return ""
