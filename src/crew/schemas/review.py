# SPDX-License-Identifier: MIT
"""ReviewOutput — cross-agent consistency review.

Keyword-based content validators (banned terms, scope terms, mismatch terms,
explanation terms) have been removed to let LLM output pass through.  The strict
versions are preserved in ``_base.py`` / ``_constants.py`` for future
re-enablement.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.crew.schemas._base import (
    coerce_summary_text,
    normalize_payload_lists,
    strip_explanatory_tail,
)


class ReviewOutput(BaseModel):
    """Structured output for the analysis-review task."""

    summary: str = Field(min_length=1)
    confidence_adjustment: Literal["Increase", "Unchanged", "Reduce"] = "Unchanged"
    data_accuracy: list[str] = Field(default_factory=list)
    watchouts: list[str] = Field(default_factory=list)
    confirmed_findings: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_review_payload(cls, value: object) -> object:
        """[model_validator mode=before] Coerce summary, strip explanatory tails from watchouts.

        Stage: runs on the raw dict before any field parsing.
        Behaviour: falls back summary to a neutral default if empty, strips
        explanatory tails from watchout items, and caps at 5.  Never raises.
        """
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        normalize_payload_lists(cls, payload)
        payload["summary"] = coerce_summary_text(
            payload.get("summary"),
            fallback="No material inconsistencies found.",
        )

        watchouts_raw = payload.get("watchouts")
        if isinstance(watchouts_raw, list):
            normalized: list[str] = []
            for item in watchouts_raw:
                text = strip_explanatory_tail(str(item).strip())
                if text:
                    normalized.append(text)
            payload["watchouts"] = normalized[:5]

        return payload

    @field_validator("confidence_adjustment", mode="before")
    @classmethod
    def _normalize_confidence_adjustment(cls, value: str) -> str:
        text = str(value).strip().lower()
        if text in ("increased", "reduced"):
            text = text[:-1]
        return text.capitalize()

    @field_validator("summary")
    @classmethod
    def _validate_summary(cls, value: str) -> str:
        """[field_validator] Strip whitespace.

        Stage: runs per-field after parsing.
        """
        return str(value).strip()

    @field_validator("data_accuracy")
    @classmethod
    def _validate_data_accuracy_length(cls, values: list[str]) -> list[str]:
        """[field_validator] Strip explanatory tails, cap at 5.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        cleaned = []
        for item in values:
            text = strip_explanatory_tail(str(item).strip())
            if text:
                cleaned.append(text)
        return cleaned[:5]

    @field_validator("watchouts")
    @classmethod
    def _validate_watchouts_length(cls, values: list[str]) -> list[str]:
        """[field_validator] Strip explanatory tails, cap at 5.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        cleaned = []
        for item in values:
            text = strip_explanatory_tail(str(item).strip())
            if text:
                cleaned.append(text)
        return cleaned[:5]

    @field_validator("confirmed_findings")
    @classmethod
    def _validate_confirmed_findings_size(cls, values: list[str]) -> list[str]:
        """[field_validator] Cap confirmed findings at 3 items.

        Stage: runs per-field after parsing.
        Behaviour: silently truncates; never raises.
        """
        return values[:3]

    @model_validator(mode="after")
    def _clear_findings_on_issues(self) -> ReviewOutput:
        """[model_validator mode=after] Clear confirmed_findings when issues exist.

        Stage: runs after all fields are validated.
        Behaviour: clears confirmed_findings if data_accuracy or watchouts are
        present (can't confirm findings and flag issues simultaneously).
        """
        if (self.data_accuracy or self.watchouts) and self.confirmed_findings:
            self.confirmed_findings = []
        return self
