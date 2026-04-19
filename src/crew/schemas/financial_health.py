# SPDX-License-Identifier: MIT
"""FinancialHealthOutput — balance-sheet and growth health check."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from src.crew.schemas._base import coerce_summary_text, normalize_payload_lists
from src.crew.schemas._items import CitationItem, MetricItem


class FinancialHealthOutput(BaseModel):
    """Structured output for the financial-health analysis task."""

    summary: str = Field(min_length=1)
    metrics: list[MetricItem] = Field(default_factory=list)
    growth_signals: list[str] = Field(default_factory=list)
    caution_signals: list[str] = Field(default_factory=list)
    citations: list[CitationItem] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_payload(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        normalize_payload_lists(cls, payload)
        payload["summary"] = coerce_summary_text(
            payload.get("summary"),
            fallback="Financial health appears stable with mixed signals.",
        )
        return payload

    @field_validator("summary")
    @classmethod
    def _strip_summary(cls, value: str) -> str:
        return str(value).strip()

    @field_validator("metrics")
    @classmethod
    def _cap_metrics(cls, values: list[MetricItem]) -> list[MetricItem]:
        return values[:5]

    @field_validator("growth_signals")
    @classmethod
    def _cap_growth(cls, values: list[str]) -> list[str]:
        return values[:3]

    @field_validator("caution_signals")
    @classmethod
    def _cap_caution(cls, values: list[str]) -> list[str]:
        return values[:3]
