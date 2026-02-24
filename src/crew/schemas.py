"""Pydantic schemas for structured Crew task outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


_VERDICT_ALIASES = {
    "STRONG BUY": "STRONG BUY",
    "BUY": "BUY",
    "HOLD": "HOLD",
    "SELL": "SELL",
    "STRONG SELL": "STRONG SELL",
}


class MetricItem(BaseModel):
    label: str
    value: str
    note: str = ""
    source: str = ""


class CitationItem(BaseModel):
    title: str = ""
    publisher: str = ""
    url: str = ""


class ValuationOutput(BaseModel):
    summary: str = Field(min_length=1)
    metrics: list[MetricItem] = Field(default_factory=list)
    implications: list[str] = Field(default_factory=list)
    citations: list[CitationItem] = Field(default_factory=list)


class PerformanceOutput(BaseModel):
    summary: str = Field(min_length=1)
    metrics: list[MetricItem] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    citations: list[CitationItem] = Field(default_factory=list)


class FinancialHealthOutput(BaseModel):
    summary: str = Field(min_length=1)
    metrics: list[MetricItem] = Field(default_factory=list)
    growth_signals: list[str] = Field(default_factory=list)
    caution_signals: list[str] = Field(default_factory=list)
    citations: list[CitationItem] = Field(default_factory=list)


class SentimentOutput(BaseModel):
    summary: str = Field(min_length=1)
    sentiment_signal: Literal["Positive", "Neutral", "Negative"]
    analyst_consensus: str = ""
    key_points: list[str] = Field(default_factory=list)
    news: list[CitationItem] = Field(default_factory=list)
    citations: list[CitationItem] = Field(default_factory=list)


class ReviewOutput(BaseModel):
    summary: str = Field(min_length=1)
    data_accuracy: list[str] = Field(default_factory=list)
    watchouts: list[str] = Field(default_factory=list)
    confirmed_findings: list[str] = Field(default_factory=list)


class FinalReportOutput(BaseModel):
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    watch_next: list[str] = Field(default_factory=list)
    advice: list[str] = Field(default_factory=list)
    verdict: Literal["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]
    confidence: Literal["High", "Medium", "Low"]
    citations: list[CitationItem] = Field(default_factory=list)

    @field_validator("verdict", mode="before")
    @classmethod
    def _normalize_verdict(cls, value: str) -> str:
        normalized = str(value).strip().upper().replace("-", " ")
        normalized = " ".join(normalized.split())
        if normalized in _VERDICT_ALIASES:
            return _VERDICT_ALIASES[normalized]
        return normalized

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value: str) -> str:
        normalized = str(value).strip().capitalize()
        return normalized
