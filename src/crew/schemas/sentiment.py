# SPDX-License-Identifier: MIT
"""SentimentOutput — market-sentiment and analyst-expectation analysis.

Keyword-based content validators (expectation terms, banned terms, directional
checks, framing checks, news shift filtering) have been removed to let LLM
output pass through.  The strict versions are preserved in ``_base.py`` /
``_constants.py`` for future re-enablement.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.crew.schemas._base import (
    coerce_summary_text,
    normalize_payload_lists,
    normalize_sentiment_signal,
    strip_bracket_prefix,
    strip_count_patterns,
    strip_explanatory_tail,
)
from src.crew.schemas._items import CitationItem


class SentimentOutput(BaseModel):
    """Structured output for the market-sentiment analysis task."""

    summary: str = Field(min_length=1)
    sentiment_signal: Literal["Positive", "Neutral", "Negative"]
    analyst_consensus: str = ""
    key_points: list[str] = Field(default_factory=list)
    news: list[CitationItem] = Field(default_factory=list)
    citations: list[CitationItem] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_sentiment_payload(cls, value: object) -> object:
        """[model_validator mode=before] Coerce summary, consensus, and infer sentiment_signal.

        Stage: runs on the raw dict before any field parsing.
        Behaviour: falls back summary/consensus to defaults if empty, infers
        sentiment_signal from polarity markers in the combined text.  Never raises.
        """
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        normalize_payload_lists(cls, payload)

        payload["summary"] = coerce_summary_text(
            payload.get("summary"),
            fallback="Market expectations are stable with mixed sentiment pressure.",
        )

        payload["analyst_consensus"] = coerce_summary_text(
            payload.get("analyst_consensus"), fallback=""
        )

        payload["sentiment_signal"] = normalize_sentiment_signal(payload.get("sentiment_signal"))
        return payload

    # ── Field validators ───────────────────────────────────────────────────

    @field_validator("summary")
    @classmethod
    def _validate_summary(cls, value: str) -> str:
        """[field_validator] Strip whitespace.

        Stage: runs per-field after parsing.
        """
        return str(value).strip()

    @field_validator("analyst_consensus")
    @classmethod
    def _validate_analyst_consensus(cls, value: str) -> str:
        """[field_validator] Format cleanup only — strip bracket prefixes, count patterns, truncate.

        Stage: runs per-field after parsing.
        Behaviour: strips ``[POSITIVE] -`` prefixes, removes numeric count
        patterns, truncates to 90 chars.  Returns empty string if input is empty.
        """
        text = str(value).strip()
        if not text:
            return text
        text = strip_bracket_prefix(text)
        text = strip_count_patterns(text)
        if not text:
            return ""
        if len(text) > 90:
            text = strip_explanatory_tail(text)
            if len(text) > 90:
                text = text[:90].rstrip(" ,;:-")
        if "\n" in text:
            text = text.replace("\n", " ").strip()
        return text

    @field_validator("key_points")
    @classmethod
    def _validate_key_points(cls, values: list[str]) -> list[str]:
        """[field_validator] Cap key points at 4 items.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        return values[:4]

    @field_validator("news")
    @classmethod
    def _validate_news_length(cls, values: list[CitationItem]) -> list[CitationItem]:
        """[field_validator] Cap news items at 5.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        return values[:5]
