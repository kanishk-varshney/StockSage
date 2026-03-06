"""Shared normalisation helpers used by schema validators.

Pure functions that multiple schema modules call to keep normalisation
logic DRY without hiding domain-specific semantics.
"""

from __future__ import annotations

import re
from typing import Any

_BRACKET_PREFIX_RE = re.compile(r"^\s*\[.*?\]\s*[-–—]?\s*")
_COUNT_PATTERN_RE = re.compile(
    r"\b\d+\s*(?:out of|/|of)\s*\d+\b"
    r"|\b\d+\s+(?:analyst|rating|recommendation|target|estimate)s?\b",
    re.IGNORECASE,
)

from src.crew.schemas._constants import DATA_SANITY_REQUIRED_FILES

# ── Summary / text coercion ────────────────────────────────────────────────────

_SUMMARY_FALLBACK_KEYS = (
    "summary",
    "message",
    "conclusion",
    "headline",
    "analysis",
    "status",
    "result",
)


def coerce_summary_text(raw: object, *, fallback: str) -> str:
    """Coerce a possibly malformed summary payload into a usable string."""
    if isinstance(raw, str):
        text = raw.strip()
        return text if text else fallback

    if isinstance(raw, dict):
        for key in _SUMMARY_FALLBACK_KEYS:
            candidate = raw.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return fallback

    if raw is None:
        return fallback

    text = str(raw).strip()
    return text if text and text not in {"{}", "[]"} else fallback


# ── Symbol extraction ──────────────────────────────────────────────────────────


def extract_symbol_from_text(text: str) -> str | None:
    """Best-effort extraction of a 1-6 letter stock ticker from *text*."""
    match = re.search(r"\b([A-Z]{1,6})\b", text.upper())
    return match.group(1) if match else None


# ── Data-sanity file checks ───────────────────────────────────────────────────


def deterministic_data_sanity_file_statuses(
    symbol: str,
) -> tuple[list[str], list[str]]:
    """Return validated / missing file lists by checking the filesystem."""
    from src.core.config.data_contracts import DATA_DIR

    symbol_dir = DATA_DIR / symbol.upper()
    validated: list[str] = []
    missing: list[str] = []
    for file_name in DATA_SANITY_REQUIRED_FILES:
        if (symbol_dir / file_name).exists():
            validated.append(f"{file_name} -> ok")
        else:
            missing.append(f"{file_name} -> missing")
    return validated, missing


# ── Sentiment normalisation ────────────────────────────────────────────────────


def normalize_sentiment_signal(raw_signal: object) -> str:
    """Map a raw sentiment signal to a canonical Literal, defaulting to Neutral."""
    key = str(raw_signal or "").strip().lower()
    if key in ("positive", "neutral", "negative"):
        return key.capitalize()
    return "Neutral"


# ── Generic text helpers ───────────────────────────────────────────────────────


def strip_explanatory_tail(text: str) -> str:
    """Truncate text at the first explanatory conjunction (because, therefore, …)."""
    lowered = text.lower()
    for marker in (
        " because ",
        " therefore ",
        " which means ",
        " so that ",
        " explain ",
    ):
        idx = lowered.find(marker)
        if idx > 0:
            return text[:idx].strip(" .;:-")
    return text.strip()


def strip_bracket_prefix(text: str) -> str:
    """Remove leading bracket tags like ``[POSITIVE] -``."""
    return _BRACKET_PREFIX_RE.sub("", text).strip()


def strip_count_patterns(text: str) -> str:
    """Remove numeric analyst-count patterns (e.g. "3 out of 5", "12 analysts")."""
    text = _COUNT_PATTERN_RE.sub("", text)
    return re.sub(r"\s{2,}", " ", text).strip()
