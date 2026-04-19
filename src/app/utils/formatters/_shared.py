# SPDX-License-Identifier: MIT
"""Shared helpers, constants, and utilities used by all card renderers."""

import html
import re

from src.core.config.enums import StatusType  # noqa: F401 — re-exported for card modules
from src.core.config.models import LogEntry  # noqa: F401 — re-exported for card modules

# ── Substage routing ─────────────────────────────────────────

_ANALYSIS_SUBSTAGES = {
    "validating_data_sanity",
    "analyzing_valuation_ratios",
    "analyzing_price_performance",
    "analyzing_financial_health",
    "analyzing_market_sentiment",
    "reviewing_analysis",
    "generating_investment_report",
}

_ANALYSIS_TITLES = {
    "validating_data_sanity": "Data Quality",
    "analyzing_valuation_ratios": "Valuation",
    "analyzing_price_performance": "Price Performance &amp; Risk",
    "analyzing_financial_health": "Financial Health",
    "analyzing_market_sentiment": "Market Sentiment",
    "reviewing_analysis": "Quality Review",
    "generating_investment_report": "Final Analysis",
}

_ANALYSIS_ICONS = {
    "validating_data_sanity": "&#x1F50D;",
    "analyzing_valuation_ratios": "&#x1F4C8;",
    "analyzing_price_performance": "&#x1F4C8;",
    "analyzing_financial_health": "&#x1F4B2;",
    "analyzing_market_sentiment": "&#x1F4F0;",
    "reviewing_analysis": "&#x2705;",
    "generating_investment_report": "&#x1F3AF;",
}


def _is_analysis_entry(log_entry: LogEntry) -> bool:
    return log_entry.substage is not None and log_entry.substage.value in _ANALYSIS_SUBSTAGES


def _ws_text(raw: str) -> str:
    """Strip leading/trailing whitespace only — preserve original case and details."""
    return raw.strip()


_STRUCTURED_SUMMARY_PREFIX = "Structured Summary:"


def _extract_ws_summary(raw: str) -> str:
    """Extract the LLM-written summary sentence from serialized output.

    Looks for 'Structured Summary: ...' and returns the text up to the first
    newline.  Returns '' if the prefix is not found.
    """
    idx = raw.find(_STRUCTURED_SUMMARY_PREFIX)
    if idx == -1:
        return ""
    after = raw[idx + len(_STRUCTURED_SUMMARY_PREFIX) :]
    line = after.split("\n", 1)[0].strip()
    return html.escape(line, quote=True)


# ── Text parsing helpers ─────────────────────────────────────

_SECTION_HEADER_RE = re.compile(r"^(?:\*{0,2})?([A-Z][A-Z0-9 &'?/\-_]{3,})(?::)?(?:\*{0,2})?$")
_METRIC_LINE_RE = re.compile(
    r"^\s*[*\-\d.)]*\s*([A-Za-z][A-Za-z0-9/ ()&%\-]{2,60})\s*[:\-]\s*([^\n]+?)\s*$"
)
_VERDICT_INLINE_RE = re.compile(
    r"VERDICT:\s*(STRONG\s*BUY|BUY|HOLD|SELL|STRONG\s*SELL|INCONCLUSIVE)\s*\|?\s*Confidence:\s*(High|Medium|Low|N/A)",
    re.IGNORECASE,
)


def _clean_line(line: str) -> str:
    line = line.strip().strip('"').strip("'")
    line = re.sub(r"^[\-\*\d.)\s]+", "", line)
    line = line.replace("**", "")
    return re.sub(r"\s+", " ", line).strip()


def _parse_kv(text: str, key: str) -> str:
    """Extract value for a Key: Value line, case-insensitive."""
    m = re.search(rf"(?:^|\n)\s*{re.escape(key)}\s*:\s*([^\n]+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _parse_kv_all(text: str, key: str, limit: int = 4) -> list[str]:
    """Extract all values for repeated Key: Value lines."""
    results: list[str] = []
    for m in re.finditer(rf"(?:^|\n)\s*{re.escape(key)}\s*:\s*([^\n]+)", text, re.IGNORECASE):
        val = m.group(1).strip()
        if val:
            results.append(val)
            if len(results) >= limit:
                break
    return results


def _parse_kv_split(text: str, key: str) -> tuple[str, str]:
    """Extract value|note pair from a 'Key: value | note' line."""
    raw = _parse_kv(text, key)
    if " | " in raw:
        parts = raw.split(" | ", 1)
        return parts[0].strip(), parts[1].strip()
    return raw, ""


def _parse_sections(text: str) -> dict[str, list[str]]:
    """Split raw text into named sections."""
    sections: dict[str, list[str]] = {}
    current = "OTHER"
    for raw_line in text.splitlines():
        line = _clean_line(raw_line)
        if not line:
            continue
        if _SECTION_HEADER_RE.match(line) and len(line) <= 40:
            current = line.strip(": ").upper()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _parse_metric(line: str) -> tuple[str, str, str] | None:
    m = _METRIC_LINE_RE.match(line)
    if not m:
        return None
    label = m.group(1).strip()
    raw_val = m.group(2).strip()
    raw_val = re.sub(r"\[source:\s*[^\]]+\]", "", raw_val, flags=re.IGNORECASE).strip()
    value, note = raw_val, ""
    for sep in (" | ", " — ", " - "):
        if sep in raw_val:
            left, right = raw_val.split(sep, 1)
            value = left.strip()
            note = right.strip()
            break
    return label, value, note


def _extract_verdict(text: str) -> tuple[str, str, str]:
    """Return (verdict, confidence, cleaned_text)."""
    m = _VERDICT_INLINE_RE.search(text)
    if m:
        v = re.sub(r"\s+", " ", m.group(1).strip().upper())
        c = m.group(2).strip().capitalize()
        cleaned = text[: m.start()] + text[m.end() :]
        return v, c, cleaned.strip()
    return "INCONCLUSIVE", "N/A", text


def _esc(s: str) -> str:
    return html.escape(s)


def _materialize_todos(text: str) -> str:
    """Render hidden TODO comments as visible one-line TODO UI rows."""
    return re.sub(
        r"<!--\s*TODO:\s*(.*?)\s*-->",
        r'<p class="todo-missing">TODO: \1</p>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )


# ── Verdict / badge color helpers ────────────────────────────


def _verdict_colors(verdict: str) -> tuple[str, str]:
    """Return (bg_gradient_class, text_class) for a verdict."""
    v = verdict.upper()
    if "INCONCLUSIVE" in v:
        return "bg-gray-200 border border-gray-300", "text-gray-600"
    if "BUY" in v:
        return "bg-gradient-to-r from-green-500 to-emerald-600", "text-white"
    if "SELL" in v:
        return "bg-gradient-to-r from-red-500 to-rose-600", "text-white"
    return "bg-gradient-to-r from-amber-400 to-amber-600", "text-white"


def _verdict_dot_color(verdict: str) -> str:
    v = verdict.upper()
    if "INCONCLUSIVE" in v:
        return "bg-gray-400"
    if "BUY" in v:
        return "bg-green-400"
    if "SELL" in v:
        return "bg-red-400"
    return "bg-amber-400"


def _verdict_icon(verdict: str) -> str:
    v = verdict.upper()
    if "INCONCLUSIVE" in v:
        return "&#x2753;"
    if "BUY" in v:
        return "&#x1F680;"
    if "SELL" in v:
        return "&#x1F6A8;"
    return "&#x1F4C8;"


def _badge_classes(label: str) -> str:
    """Return Tailwind classes for a status badge."""
    low = label.lower()
    if low in (
        "yes",
        "positive",
        "strong",
        "outperforming",
        "stable",
        "low",
        "cheap",
        "confirmed",
        "healthy",
        "good",
    ):
        return "bg-green-100 text-green-700 border border-green-300"
    if low in (
        "no",
        "negative",
        "weak",
        "underperforming",
        "high",
        "expensive",
        "risky",
        "not ideal",
        "unfavorable",
    ):
        return "bg-red-100 text-red-700 border border-red-300"
    return "bg-yellow-100 text-yellow-700 border border-yellow-300"


def _badge_icon(label: str) -> str:
    low = label.lower()
    if low in ("yes", "positive", "strong", "outperforming", "stable"):
        return '<svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
    if low in ("no", "negative", "weak", "underperforming", "expensive"):
        return '<svg class="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
    if low in ("mixed", "moderate", "fair"):
        return '<svg class="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>'
    return '<svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'


def _info_icon(tooltip: str = "") -> str:
    svg = '<svg class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
    if tooltip:
        return f'<span class="help-icon-wrapper" data-tooltip="{html.escape(tooltip, quote=True)}">{svg}</span>'
    return svg


# ── Best Suited / Not Ideal templates ────────────────────────

_SUITED_TEMPLATES = {
    "HOLD": [
        "Existing shareholders with long-term conviction",
        "Patient investors willing to wait for catalysts",
        "Those seeking to maintain diversified positions",
    ],
    "BUY": [
        "Growth investors seeking upside potential",
        "Long-term investors building a portfolio",
        "Those comfortable with moderate risk",
    ],
    "STRONG BUY": [
        "Aggressive growth investors",
        "Conviction buyers with strong risk appetite",
        "Long-term compounders seeking alpha",
    ],
    "SELL": [
        "Risk-averse investors protecting capital",
        "Those reallocating to better opportunities",
        "Tactical traders adjusting positions",
    ],
    "STRONG SELL": [
        "Risk-averse investors seeking safety",
        "Capital preservation focused portfolios",
        "Those with better alternative investments",
    ],
}

_NOT_IDEAL_TEMPLATES = {
    "HOLD": [
        "New investors seeking better entry points",
        "Value hunters looking for undervalued stocks",
        "Growth investors seeking momentum",
    ],
    "BUY": [
        "Risk-averse investors seeking safety",
        "Short-term traders expecting quick gains",
        "Income investors seeking high dividends",
    ],
    "STRONG BUY": [
        "Conservative investors with low risk tolerance",
        "Short-term traders who can't handle drawdowns",
        "Income-focused investors",
    ],
    "SELL": [
        "Long-term holders with conviction",
        "Contrarian investors buying dips",
        "Passive index-only investors",
    ],
    "STRONG SELL": [
        "Long-term bulls with conviction",
        "Contrarian value investors",
        "Passive holders ignoring fundamentals",
    ],
}

# ── Card wrapper ─────────────────────────────────────────────

_CARD_OPEN = '<div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 log-analysis"'
_CARD_CLOSE = "</div>"


def _card(body: str, data_section: str = "") -> str:
    ds = f' data-section="{data_section}"' if data_section else ""
    return f"{_CARD_OPEN}{ds}>{_materialize_todos(body)}{_CARD_CLOSE}"
