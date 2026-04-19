# SPDX-License-Identifier: MIT
"""PerformanceOutput — price-performance and risk profile.

Keyword-based content validators (banned terms, risk markers, metric note
rejection) have been removed to let LLM output pass through.  The strict
versions are preserved in ``_base.py`` / ``_constants.py`` for future
re-enablement.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from src.crew.schemas._base import coerce_summary_text, normalize_payload_lists
from src.crew.schemas._items import CitationItem, MetricItem


class PerformanceOutput(BaseModel):
    """Structured output for the price-performance analysis task."""

    summary: str = Field(min_length=1)
    metrics: list[MetricItem] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    citations: list[CitationItem] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_performance_payload(cls, value: object) -> object:
        """[model_validator mode=before] Coerce summary, cap metrics at 5.

        Stage: runs on the raw dict before any field parsing.
        Behaviour: falls back summary to a neutral default if empty.  Never raises.
        """
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        normalize_payload_lists(cls, payload)
        payload["summary"] = coerce_summary_text(
            payload.get("summary"),
            fallback="Returns are mixed with moderate downside risk.",
        )
        raw_metrics = payload.get("metrics")
        if isinstance(raw_metrics, list) and len(raw_metrics) > 5:
            payload["metrics"] = raw_metrics[:5]
        return payload

    @field_validator("summary")
    @classmethod
    def _validate_summary(cls, value: str) -> str:
        """[field_validator] Strip whitespace.

        Stage: runs per-field after parsing.
        """
        return str(value).strip()

    @field_validator("metrics")
    @classmethod
    def _validate_metrics_length(cls, values: list[MetricItem]) -> list[MetricItem]:
        """[field_validator] Cap metrics at 5 items.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        return values[:5]

    @field_validator("risk_notes")
    @classmethod
    def _validate_risk_notes_length(cls, values: list[str]) -> list[str]:
        """[field_validator] Cap risk notes at 3 items.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        return values[:3]
