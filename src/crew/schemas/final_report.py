"""FinalReportOutput — investment decision and recommendation.

Keyword-based content validators (banned terms, metric restatement filtering,
catalyst filtering, guidance tone checks) have been removed to let LLM output
pass through.  The strict versions are preserved in ``_base.py`` /
``_constants.py`` for future re-enablement.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.crew.schemas._base import (
    coerce_summary_text,
    strip_explanatory_tail,
)
from src.crew.schemas._constants import CONFIDENCE_FROM_ADJUSTMENT
from src.crew.schemas._items import CitationItem


class FinalReportOutput(BaseModel):
    """Structured output for the investment-report generation task."""

    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    watch_next: list[str] = Field(default_factory=list)
    best_suited_for: list[str] = Field(default_factory=list)
    not_ideal_for: list[str] = Field(default_factory=list)
    guidance_for_existing_holders: str = ""
    guidance_for_new_buyers: str = ""
    verdict: Literal["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]
    confidence: Literal["High", "Medium", "Low"]
    citations: list[CitationItem] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _map_final_guidance_aliases(cls, value: object) -> object:
        """[model_validator mode=before] Map aliases, coerce summary, backfill guidance and confidence.

        Stage: runs on the raw dict before any field parsing.
        Behaviour: maps ``key_reasons`` -> ``strengths`` and ``key_risks`` -> ``risks``
        aliases, falls back summary and guidance fields to neutral defaults,
        and derives ``confidence`` from ``confidence_adjustment`` when absent.
        Never raises.
        """
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        payload["summary"] = coerce_summary_text(
            payload.get("summary"),
            fallback="At current prices, risk-reward appears balanced.",
        )

        if "key_reasons" in payload and "strengths" not in payload:
            payload["strengths"] = payload.get("key_reasons")
        if "key_risks" in payload and "risks" not in payload:
            payload["risks"] = payload.get("key_risks")

        payload["guidance_for_existing_holders"] = coerce_summary_text(
            payload.get("guidance_for_existing_holders"),
            fallback="Existing holders: maintain current exposure unless "
            "risk profile changes.",
        )
        payload["guidance_for_new_buyers"] = coerce_summary_text(
            payload.get("guidance_for_new_buyers"),
            fallback="New buyers: stage entries according to risk tolerance "
            "and volatility.",
        )

        if "confidence" not in payload:
            adjustment = (
                str(payload.get("confidence_adjustment", "")).strip().lower()
            )
            payload["confidence"] = CONFIDENCE_FROM_ADJUSTMENT.get(
                adjustment, "Medium"
            )

        return payload

    # ── Field validators ───────────────────────────────────────────────────

    @field_validator("summary")
    @classmethod
    def _validate_summary(cls, value: str) -> str:
        """[field_validator] Strip whitespace.

        Stage: runs per-field after parsing.
        """
        return str(value).strip()

    @field_validator("best_suited_for", "not_ideal_for")
    @classmethod
    def _validate_suitability_lists(cls, values: list[str]) -> list[str]:
        """[field_validator] Strip explanatory tails, cap at 3.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        return _strip_and_cap(values, max_items=3)

    @field_validator("strengths")
    @classmethod
    def _validate_strengths(cls, values: list[str]) -> list[str]:
        """[field_validator] Strip explanatory tails, cap at 4.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        return _strip_and_cap(values, max_items=4)

    @field_validator("risks")
    @classmethod
    def _validate_risks(cls, values: list[str]) -> list[str]:
        """[field_validator] Strip explanatory tails, cap at 4.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        return _strip_and_cap(values, max_items=4)

    @field_validator("watch_next")
    @classmethod
    def _validate_watch_next(cls, values: list[str]) -> list[str]:
        """[field_validator] Cap at 3 items.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        return _strip_and_cap(values, max_items=3)

    @field_validator("guidance_for_existing_holders", "guidance_for_new_buyers")
    @classmethod
    def _validate_guidance_fields(cls, value: str) -> str:
        """[field_validator] Strip whitespace.

        Stage: runs per-field after parsing.
        """
        return str(value).strip()

    @field_validator("verdict", mode="before")
    @classmethod
    def _normalize_verdict(cls, value: str) -> str:
        normalized = str(value).strip().upper().replace("-", " ")
        return " ".join(normalized.split())

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value: str) -> str:
        """[field_validator mode=before] Capitalise confidence level to match Literal.

        Stage: runs per-field before type coercion.
        """
        return str(value).strip().capitalize()


def _strip_and_cap(values: list[str], *, max_items: int) -> list[str]:
    """Strip explanatory tails and cap list size."""
    cleaned: list[str] = []
    for item in values:
        text = strip_explanatory_tail(str(item).strip())
        if text:
            cleaned.append(text)
        if len(cleaned) >= max_items:
            break
    return cleaned
