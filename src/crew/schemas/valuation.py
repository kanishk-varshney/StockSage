# SPDX-License-Identifier: MIT
"""ValuationOutput — ratio-based valuation analysis.

Keyword-based content validators (banned terms, stance markers, CSV source
enforcement) have been removed to let LLM output pass through.  The strict
versions are preserved in ``_base.py`` / ``_constants.py`` for future
re-enablement.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from src.crew.schemas._base import coerce_summary_text, normalize_payload_lists
from src.crew.schemas._items import CitationItem, MetricItem


class ValuationOutput(BaseModel):
    """Structured output for the valuation-ratios analysis task."""

    summary: str = Field(min_length=1)
    metrics: list[MetricItem] = Field(default_factory=list)
    implications: list[str] = Field(default_factory=list)
    citations: list[CitationItem] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_valuation_payload(cls, value: object) -> object:
        """[model_validator mode=before] Coerce summary and cap metrics.

        Stage: runs on the raw dict before any field parsing.
        Behaviour: falls back summary to a neutral default if empty, caps metrics
        at 5.  Never raises.
        """
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        normalize_payload_lists(cls, payload)
        payload["summary"] = coerce_summary_text(
            payload.get("summary"),
            fallback="Valuation appears fair based on available inputs.",
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

    @field_validator("implications")
    @classmethod
    def _validate_implications_length(cls, values: list[str]) -> list[str]:
        """[field_validator] Cap implications at 4 items.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        return values[:4]
