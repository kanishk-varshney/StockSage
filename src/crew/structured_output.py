"""Structured-output policy, schema registry, and serializers."""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from pydantic import BaseModel, ValidationError

from src.crew.schemas import (
    FinalReportOutput,
    FinancialHealthOutput,
    PerformanceOutput,
    ReviewOutput,
    SentimentOutput,
    ValuationOutput,
)


class StructuredOutputPolicy(BaseModel):
    enabled: bool = True
    strict_validation: bool = True
    max_retry_attempts: int = 2
    retry_backoff_seconds: float = 1.25


STRUCTURED_OUTPUT_POLICY = StructuredOutputPolicy()

TASK_OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "analyze_valuation_ratios": ValuationOutput,
    "analyze_price_performance": PerformanceOutput,
    "analyze_financial_health": FinancialHealthOutput,
    "analyze_market_sentiment": SentimentOutput,
    "review_analysis": ReviewOutput,
    "generate_investment_report": FinalReportOutput,
}


def output_model_for_task(task_name: str) -> type[BaseModel] | None:
    if not STRUCTURED_OUTPUT_POLICY.enabled:
        return None
    return TASK_OUTPUT_MODELS.get(task_name)


def has_structured_schema(task_name: str | None) -> bool:
    return bool(task_name and output_model_for_task(task_name))


def should_retry_structured_error(exc: Exception) -> bool:
    if isinstance(exc, (JSONDecodeError, ValidationError)):
        return True
    text = str(exc).lower()
    return "jsondecodeerror" in text or "unterminated string" in text or "expecting value" in text


def validate_task_output(task_name: str | None, task_output: Any) -> BaseModel | None:
    if not task_name:
        return None
    model_cls = output_model_for_task(task_name)
    if model_cls is None:
        return None

    pydantic_obj = getattr(task_output, "pydantic", None)
    if isinstance(pydantic_obj, model_cls):
        return pydantic_obj
    if isinstance(pydantic_obj, BaseModel):
        return model_cls.model_validate(pydantic_obj.model_dump())

    json_dict = getattr(task_output, "json_dict", None)
    if isinstance(json_dict, dict):
        return model_cls.model_validate(json_dict)

    raw = getattr(task_output, "raw", "")
    if isinstance(raw, str) and raw.strip():
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            return model_cls.model_validate_json(text)
        except ValidationError:
            maybe_dict = json.loads(text)
            return model_cls.model_validate(maybe_dict)

    return None


def _serialize_metrics(metrics: list[Any]) -> list[str]:
    lines: list[str] = []
    for metric in metrics[:8]:
        source_suffix = f" [source: {metric.source}]" if getattr(metric, "source", "") else ""
        note_suffix = f" | {metric.note}" if getattr(metric, "note", "") else ""
        lines.append(f"{metric.label}: {metric.value}{note_suffix}{source_suffix}")
    return lines


def _serialize_citations(citations: list[Any], *, label: str = "Source") -> list[str]:
    lines: list[str] = []
    for item in citations[:4]:
        title = getattr(item, "title", "").strip() or "reference"
        publisher = getattr(item, "publisher", "").strip() or "source"
        url = getattr(item, "url", "").strip()
        if url:
            lines.append(f"{label}: {title} | {publisher} | {url}")
    return lines


def serialize_structured_output(task_name: str | None, model: BaseModel) -> str:
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
        lines = [f"Structured Summary: {model.summary}"]
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
            *[f"Advice: {line}" for line in model.advice[:3]],
            f"VERDICT: {model.verdict} | Confidence: {model.confidence}",
            *_serialize_citations(model.citations),
        ]
        return "\n".join(lines)

    return ""
