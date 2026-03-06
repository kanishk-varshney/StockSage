"""Log formatting utilities — wireframe-matched Tailwind HTML rendering."""

import html
import re

from src.core.config.enums import StatusType
from src.core.config.models import LogEntry

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
    after = raw[idx + len(_STRUCTURED_SUMMARY_PREFIX):]
    line = after.split("\n", 1)[0].strip()
    return html.escape(line, quote=True)


# ── Text parsing helpers ─────────────────────────────────────

_SECTION_HEADER_RE = re.compile(r"^(?:\*{0,2})?([A-Z][A-Z0-9 &'?/\-_]{3,})(?::)?(?:\*{0,2})?$")
_METRIC_LINE_RE = re.compile(
    r"^\s*[*\-\d.)]*\s*([A-Za-z][A-Za-z0-9/ ()&%\-]{2,60})\s*[:\-]\s*([^\n]+?)\s*$"
)
_VERDICT_INLINE_RE = re.compile(
    r"VERDICT:\s*(STRONG\s*BUY|BUY|HOLD|SELL|STRONG\s*SELL)\s*\|?\s*Confidence:\s*(High|Medium|Low)",
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
        cleaned = text[:m.start()] + text[m.end():]
        return v, c, cleaned.strip()
    return "HOLD", "Medium", text


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
    if "BUY" in v:
        return "bg-gradient-to-r from-green-500 to-emerald-600", "text-white"
    if "SELL" in v:
        return "bg-gradient-to-r from-red-500 to-rose-600", "text-white"
    return "bg-gradient-to-r from-amber-400 to-amber-600", "text-white"


def _verdict_dot_color(verdict: str) -> str:
    v = verdict.upper()
    if "BUY" in v:
        return "bg-green-400"
    if "SELL" in v:
        return "bg-red-400"
    return "bg-amber-400"


def _verdict_icon(verdict: str) -> str:
    v = verdict.upper()
    if "BUY" in v:
        return "&#x1F680;"
    if "SELL" in v:
        return "&#x1F6A8;"
    return "&#x1F4C8;"


def _badge_classes(label: str) -> str:
    """Return Tailwind classes for a status badge."""
    low = label.lower()
    if low in (
        "yes", "positive", "strong", "outperforming", "stable", "low", "cheap", "confirmed", "healthy", "good"
    ):
        return "bg-green-100 text-green-700 border border-green-300"
    if low in (
        "no", "negative", "weak", "underperforming", "high", "expensive", "risky", "not ideal", "unfavorable"
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
_CARD_CLOSE = '</div>'


def _card(body: str, data_section: str = "") -> str:
    ds = f' data-section="{data_section}"' if data_section else ""
    return f'{_CARD_OPEN}{ds}>{_materialize_todos(body)}{_CARD_CLOSE}'


# ══════════════════════════════════════════════════════════════
# CARD RENDERERS — one per wireframe section
# ══════════════════════════════════════════════════════════════

# ── 1. Investment Report → Company Header + Quick Answers + Final Guidance ──

def _render_report_cards(raw: str, symbol: str) -> str:
    verdict, confidence, cleaned = _extract_verdict(raw)
    sections = _parse_sections(cleaned)

    name = _parse_kv(raw, "Company Name") or symbol
    ticker = _parse_kv(raw, "Ticker") or symbol
    sector = _parse_kv(raw, "Sector") or ""
    segment = _parse_kv(raw, "Segment") or ""
    price = _parse_kv(raw, "Price (USD)") or _parse_kv(raw, "Price") or ""
    mcap = _parse_kv(raw, "Market Cap") or ""
    cap_size = _parse_kv(raw, "Cap Size") or ""
    summary = _parse_kv(raw, "Structured Summary") or ""

    vbg, vtxt = _verdict_colors(verdict)
    dot_color = _verdict_dot_color(verdict)
    vicon = _verdict_icon(verdict)
    conf_cls = "border-yellow-400 text-yellow-700" if confidence.lower() == "medium" else (
        "border-green-400 text-green-700" if confidence.lower() == "high" else "border-red-400 text-red-700"
    )

    _agent_tag = re.compile(r"\s*\([^)]*analyst[^)]*\)", re.IGNORECASE)
    def _clean(items: list[str]) -> list[str]:
        return [_agent_tag.sub("", s).strip() for s in items]

    strengths = _clean(_parse_kv_all(raw, "Strength", limit=3))
    risks = _clean(_parse_kv_all(raw, "Risk", limit=3))
    suited = _clean(_parse_kv_all(raw, "Best Suited For", limit=2))

    tip_why = _esc("; ".join(strengths)) if strengths else "Strengths data not available."
    tip_who = _esc("; ".join(suited)) if suited else "Suitability data not available."
    tip_risk = _esc("; ".join(risks)) if risks else "Risk data not available."

    # ── Company Header Card ──
    company_header = f'''
    <div class="mb-3">
      <div class="flex items-start justify-between">
        <div>
          <h2 class="text-3xl font-bold text-gray-900">{_esc(name)}</h2>
          <p class="text-base font-mono text-green-600 mt-0.5">{_esc(ticker)}</p>
        </div>
        <span class="px-4 py-1.5 rounded-full border border-gray-300 text-sm font-semibold text-gray-700">{_esc(cap_size) if cap_size else 'N/A'}</span>
      </div>
      <div class="flex items-baseline gap-8 mt-4">
        <div>
          <p class="text-sm text-gray-500">Current Price</p>
          <p class="text-4xl font-bold text-gray-900">{_esc(price) if price else 'N/A'}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Market Cap</p>
          <p class="text-xl font-bold text-gray-700">{_esc(mcap) if mcap else 'N/A'}</p>
        </div>
      </div>
    </div>

    <div class="bg-slate-50 border border-gray-200 rounded-xl p-6 mt-4">
      <div class="flex items-center gap-2 mb-4">
        <span class="w-3 h-3 rounded-full {dot_color}"></span>
        <span class="text-sm font-bold text-gray-500 uppercase tracking-wider">Overall Verdict</span>
      </div>
      <div class="flex items-center gap-5 flex-wrap">
        <span class="inline-flex items-center gap-2.5 px-7 py-3 rounded-xl text-xl font-extrabold shadow-md {vbg} {vtxt}">
          {vicon} {_esc(verdict)}
        </span>
        <div>
          <p class="text-sm text-gray-500">Confidence Level</p>
          <span class="inline-block px-3 py-1 rounded border text-sm font-semibold {conf_cls}">{_esc(confidence)}</span>
        </div>
      </div>
      <div class="mt-5 border border-gray-200 rounded-lg p-4 bg-white">
        <p class="text-base text-gray-700 leading-relaxed">{_esc(summary) if summary else 'Summary not available.'}</p>
      </div>
      <div class="flex flex-wrap gap-2.5 mt-4">
        <span class="help-icon-wrapper px-4 py-1.5 rounded-full border border-gray-300 text-sm font-medium text-gray-600" data-tooltip="{tip_why}">Why this verdict?</span>
        <span class="help-icon-wrapper px-4 py-1.5 rounded-full border border-gray-300 text-sm font-medium text-gray-600" data-tooltip="{tip_who}">Who should invest?</span>
        <span class="help-icon-wrapper px-4 py-1.5 rounded-full border border-gray-300 text-sm font-medium text-gray-600" data-tooltip="{tip_risk}">Key risks</span>
      </div>
    </div>

    <div class="flex items-center gap-4 mt-5 text-base">
      <span class="text-gray-500">Sector:</span>
      <span class="px-2.5 py-0.5 bg-gray-100 rounded text-sm font-semibold text-gray-700">{_esc(sector) if sector else 'N/A'}</span>
      <span class="text-gray-500">Segment:</span>
      <span class="text-gray-700 text-sm">{_esc(segment) if segment else 'N/A'}</span>
    </div>
    '''

    # ── Quick Answers Card ──
    qa_lines = sections.get("QUICK_ANSWERS", [])
    qa_data: dict[str, tuple[str, str]] = {}
    for line in qa_lines:
        for key in ("Good Business", "Financially Healthy", "Stock Risky", "Expensive"):
            if line.startswith(f"{key}:"):
                val_part = line.split(":", 1)[1].strip()
                if " | " in val_part:
                    badge, desc = val_part.split(" | ", 1)
                    qa_data[key] = (badge.strip(), desc.strip())
                else:
                    qa_data[key] = (val_part, "")

    def _qa_card(question: str, key: str, fallback_badge: str, fallback_desc: str) -> str:
        badge, desc = qa_data.get(key, (fallback_badge, fallback_desc))
        icon = _badge_icon(badge)
        bcls = _badge_classes(badge)
        return f'''
        <div class="bg-white border border-gray-200 rounded-xl p-4 relative">
          <div class="absolute top-3 right-3">{_info_icon()}</div>
          <p class="text-sm font-semibold text-gray-800 mb-2">{question}</p>
          <div class="flex items-center gap-2 mb-1.5">
            {icon}
            <span class="px-2 py-0.5 rounded text-xs font-bold {bcls}">{_esc(badge)}</span>
          </div>
          <p class="text-xs text-gray-500 leading-relaxed">{_esc(desc) if desc else '<!-- TODO: Quick answer description not available -->'}</p>
        </div>'''

    quick_answers = f'''
    <div class="flex items-center gap-2 mb-4">
      <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      <div>
        <h3 class="text-lg font-bold text-gray-900">Quick Answers</h3>
        <p class="text-xs text-gray-500">Decision snapshot to help you decide</p>
      </div>
    </div>
    <div class="grid grid-cols-2 gap-4">
      {_qa_card("Is this a good business?", "Good Business", "Mixed", "<!-- TODO: Derive from revenue/profit growth -->")}
      {_qa_card("Is the company financially healthy?", "Financially Healthy", "Yes", "<!-- TODO: Derive from debt/cash metrics -->")}
      {_qa_card("Is the stock risky?", "Stock Risky", "Moderate", "<!-- TODO: Derive from volatility -->")}
      {_qa_card("Is it expensive right now?", "Expensive", "Fair", "<!-- TODO: Derive from P/E ratios -->")}
    </div>
    '''

    # ── Final Guidance Card ──
    parsed_suited = _clean(_parse_kv_all(raw, "Best Suited For", limit=4))
    parsed_not_ideal = _clean(_parse_kv_all(raw, "Not Ideal For", limit=4))
    suited = parsed_suited if parsed_suited else _SUITED_TEMPLATES.get(verdict, _SUITED_TEMPLATES["HOLD"])
    not_ideal = parsed_not_ideal if parsed_not_ideal else _NOT_IDEAL_TEMPLATES.get(verdict, _NOT_IDEAL_TEMPLATES["HOLD"])

    strengths = [l.split(":", 1)[1].strip() for l in sections.get("OTHER", []) if l.lower().startswith("strength:")]
    risks = [l.split(":", 1)[1].strip() for l in sections.get("OTHER", []) if l.lower().startswith("risk:")]

    advice_own = _parse_kv(raw, "Guidance For Existing Holders") or ""
    advice_buy = _parse_kv(raw, "Guidance For New Buyers") or ""
    if not advice_own:
        advice_lines = [l.split(":", 1)[1].strip() for l in sections.get("OTHER", []) if l.lower().startswith("advice:")]
        advice_own = advice_lines[0] if len(advice_lines) > 0 else ""
        advice_buy = advice_lines[1] if len(advice_lines) > 1 else ""

    suited_html = "".join(f'<div class="flex items-center gap-2 text-sm text-green-800"><span class="text-green-500 font-bold">&#10003;</span> {_esc(s)}</div>' for s in suited)
    not_ideal_html = "".join(f'<div class="flex items-center gap-2 text-sm text-red-700"><span class="text-red-500 font-bold">&#10007;</span> {_esc(n)}</div>' for n in not_ideal)

    final_guidance = f'''
    <div class="flex items-center gap-2 mb-5">
      <span class="text-xl">&#x1F3AF;</span>
      <h3 class="text-lg font-bold text-gray-900">Final Guidance</h3>
    </div>

    <div class="mb-4">
      <div class="flex items-center gap-2 mb-2">
        <svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
        <p class="text-sm font-bold text-gray-800">Best Suited For</p>
      </div>
      <div class="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2">
        {suited_html}
      </div>
    </div>

    <div class="mb-5">
      <div class="flex items-center gap-2 mb-2">
        <svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
        <p class="text-sm font-bold text-gray-800">Not Ideal For</p>
      </div>
      <div class="bg-red-50 border border-red-200 rounded-lg p-4 space-y-2">
        {not_ideal_html}
      </div>
    </div>

    <div class="border border-gray-200 rounded-xl overflow-hidden">
      <div class="flex items-center justify-between px-5 py-3 border-b border-gray-100">
        <div class="flex items-center gap-2">
          <span class="text-lg">&#x1F4C8;</span>
          <h4 class="text-base font-bold text-gray-900">Final Recommendation</h4>
        </div>
        <span class="px-3 py-1 rounded text-xs font-bold {vbg} {vtxt}">{_esc(verdict)}</span>
      </div>
      <div class="p-4 space-y-3">
        <div class="bg-blue-50 border border-blue-100 rounded-lg p-4">
          <p class="text-sm font-bold text-gray-800 mb-1">&#x1F4CA; If you already own this stock:</p>
          <p class="text-sm text-gray-600">{_esc(advice_own) if advice_own else 'Guidance not available.'}</p>
        </div>
        <div class="bg-white border border-gray-100 rounded-lg p-4">
          <p class="text-sm font-bold text-gray-800 mb-1">&#x1F3AF; If you&#39;re considering buying today:</p>
          <p class="text-sm text-gray-600">{_esc(advice_buy) if advice_buy else 'Guidance not available.'}</p>
        </div>
      </div>
    </div>

    <div class="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <p class="text-xs text-yellow-800">
        <span class="font-bold">&#x26A0; Important Disclaimer:</span>
        <em>This analysis is for educational and informational purposes only. It is not personalized financial advice. Always do your own research, consider your financial situation, risk tolerance, and investment goals. Past performance does not guarantee future results. Consult a qualified financial advisor before making investment decisions.</em>
      </p>
    </div>
    '''

    _ = quick_answers  # Kept for future optional use; hidden in wireframe-accurate layout.
    return _card(company_header, data_section="company-header") + _card(final_guidance, data_section="final-guidance")


# ── 2. Performance Overview ──────────────────────────────────

def _strip_suffix(val: str, *suffixes: str) -> str:
    """Strip trailing units like '%' or 'x' so the formatter can append its own."""
    v = val.strip()
    for s in suffixes:
        if v.endswith(s):
            v = v[: -len(s)].strip()
    return v


def _render_performance_card(raw: str, symbol: str) -> str:
    total_return = _strip_suffix(_parse_kv(raw, "Total Return (%)"), "%")
    annualized = _strip_suffix(_parse_kv(raw, "Annualized Return (%)"), "%")
    volatility = _strip_suffix(_parse_kv(raw, "Volatility (%)"), "%")
    vol_label = _parse_kv(raw, "Volatility Label") or "Moderate"
    max_dd = _strip_suffix(_parse_kv(raw, "Max Drawdown (%)"), "%")
    beta = _strip_suffix(_parse_kv(raw, "Beta (vs market)"), "x")
    sharpe = _parse_kv(raw, "Sharpe Ratio")
    market_return = _strip_suffix(_parse_kv(raw, "Market Total Return (%)"), "%")
    perf_badge = _parse_kv(raw, "Performance Badge") or "IN LINE"
    insight = _parse_kv(raw, "Insight") or ""

    badge_cls = _badge_classes(perf_badge.split()[0] if perf_badge else "IN LINE")

    def _is_pos(val: str | None) -> bool:
        return bool(val) and not val.strip().startswith("-")

    def _ret_style(val: str | None) -> tuple[str, str, str]:
        """Return (text_color, bg_classes, arrow_html)."""
        if not val:
            return "text-gray-900", "bg-white border border-gray-200", ""
        if _is_pos(val):
            return "text-green-600", "bg-white border border-green-300 border-l-4 border-l-green-500", '<span class="text-green-500 mr-1">&#x2191;</span>'
        return "text-red-600", "bg-white border border-red-300 border-l-4 border-l-red-500", '<span class="text-red-500 mr-1">&#x2193;</span>'

    def _vol_style(label: str) -> tuple[str, str]:
        low = label.lower()
        if low in ("low", "stable"):
            return "text-green-600", "bg-white border border-green-300 border-l-4 border-l-green-500"
        if low in ("high", "very high"):
            return "text-red-600", "bg-white border border-red-300 border-l-4 border-l-red-500"
        return "text-orange-500", "bg-white border border-orange-300 border-l-4 border-l-orange-500"

    def _beta_style(val: str | None) -> tuple[str, str]:
        if not val:
            return "text-blue-600", "bg-white border border-blue-300 border-l-4 border-l-blue-500"
        try:
            b = float(val.replace("x", "").strip())
        except ValueError:
            return "text-blue-600", "bg-white border border-blue-300 border-l-4 border-l-blue-500"
        if b > 1.3:
            return "text-red-600", "bg-white border border-red-300 border-l-4 border-l-red-500"
        if b < 0.7:
            return "text-green-600", "bg-white border border-green-300 border-l-4 border-l-green-500"
        return "text-blue-600", "bg-white border border-blue-300 border-l-4 border-l-blue-500"

    def _sharpe_style(val: str | None) -> tuple[str, str]:
        if not val:
            return "text-gray-900", "bg-white border border-gray-200"
        try:
            s = float(val.strip())
        except ValueError:
            return "text-gray-900", "bg-white border border-gray-200"
        if s >= 1.0:
            return "text-green-600", "bg-white border border-green-300 border-l-4 border-l-green-500"
        if s < 0.5:
            return "text-red-600", "bg-white border border-red-300 border-l-4 border-l-red-500"
        return "text-blue-600", "bg-white border border-blue-300 border-l-4 border-l-blue-500"

    tr_c, tr_bg, tr_arrow = _ret_style(total_return)
    ar_c, ar_bg, _ = _ret_style(annualized)
    vol_c, vol_bg = _vol_style(vol_label)
    beta_c, beta_bg = _beta_style(beta)
    sharpe_c, sharpe_bg = _sharpe_style(sharpe)

    comparison = ""
    if total_return and market_return:
        comparison = f'{_esc(total_return)}% over the past year vs. {_esc(market_return)}% for the S&amp;P 500 (market index)'

    tr_sign = "+" if _is_pos(total_return) else ""
    ar_sign = "+" if _is_pos(annualized) else ""

    body = f'''
    <div class="flex items-start justify-between mb-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center"><span class="text-orange-600 text-lg">&#x1F4C8;</span></div>
        <div>
          <h3 class="text-lg font-bold text-gray-900">Price Performance &amp; Risk</h3>
          <p class="text-xs text-gray-500">Returns &amp; volatility metrics</p>
        </div>
      </div>
      <span class="px-3 py-1 rounded text-xs font-bold {badge_cls}">{_esc(perf_badge)}</span>
    </div>

    <div class="grid grid-cols-2 gap-3">
      <div class="{tr_bg} rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Total Return</p>{_info_icon("Cumulative price return over the analysis period.")}</div>
        <p class="text-2xl font-bold {tr_c} mt-2">{tr_arrow}{tr_sign}{_esc(total_return) if total_return else 'N/A'}%</p>
        <p class="text-xs text-gray-400 mt-1 leading-snug">{comparison}</p>
      </div>
      <div class="{ar_bg} rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Annualized Return</p>{_info_icon("Return normalized to a yearly rate for comparison across time periods.")}</div>
        <p class="text-2xl font-bold {ar_c} mt-2">{ar_sign}{_esc(annualized) if annualized else 'N/A'}%</p>
      </div>

      <div class="{vol_bg} rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Volatility</p>{_info_icon("Annualized standard deviation of returns. Higher = more price swings.")}</div>
        <p class="text-2xl font-bold {vol_c} mt-2">{_esc(volatility) if volatility else 'N/A'}%</p>
      </div>
      <div class="{beta_bg} rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Beta</p>{_info_icon("Sensitivity to market moves. 1.0 = moves with market, >1 = more volatile.")}</div>
        <p class="text-2xl font-bold {beta_c} mt-2">{_esc(beta) if beta else 'N/A'}x</p>
      </div>

      <div class="{sharpe_bg} rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Sharpe Ratio</p>{_info_icon("Risk-adjusted return. Above 1.0 = good, above 2.0 = excellent.")}</div>
        <p class="text-2xl font-bold {sharpe_c} mt-2"><span class="text-gray-400 mr-1">&#x301C;</span>{_esc(sharpe) if sharpe else 'N/A'}</p>
      </div>
      <div class="bg-white border border-red-300 border-l-4 border-l-red-500 rounded-xl p-4">
        <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Max Drawdown</p>{_info_icon("Largest peak-to-trough decline. Shows worst-case loss scenario.")}</div>
        <p class="text-2xl font-bold text-red-600 mt-2"><span class="text-red-500 mr-1">&#x2193;</span>{_esc(max_dd) if max_dd else 'N/A'}%</p>
      </div>
    </div>

    <div class="mt-4 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
      <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0"><span class="text-amber-600">&#x26A1;</span></div>
      <div>
        <p class="text-sm font-bold text-gray-800">Performance Insight</p>
        <p class="text-sm text-amber-800 mt-0.5">{_esc(insight) if insight else "Performance analysis completed."}</p>
      </div>
    </div>
    '''
    return _card(body, data_section="performance")


# ── 3. Business Health ───────────────────────────────────────

def _render_health_card(raw: str, symbol: str) -> str:
    health_status = _parse_kv(raw, "Health Status") or "STABLE"
    insight = _parse_kv(raw, "Insight") or ""
    structured_summary = _parse_kv(raw, "Structured Summary") or ""

    rev_desc, rev_val = _parse_kv_split(raw, "Revenue Growth Desc")
    profit_desc, profit_val = _parse_kv_split(raw, "Profit Growth Desc")
    debt_desc, debt_val = _parse_kv_split(raw, "Debt Desc")
    cash_desc, cash_val = _parse_kv_split(raw, "Cash Desc")

    rev_growth_rate = _strip_suffix(_parse_kv(raw, "Revenue Growth Rate") or _parse_kv(raw, "Revenue Growth (%)"), "%")
    earn_growth_rate = _strip_suffix(_parse_kv(raw, "Earnings Growth Rate") or _parse_kv(raw, "Earnings Growth (%)"), "%")
    debt_ratio = _strip_suffix(debt_val, "%")

    badge_cls = _badge_classes(health_status)
    rg_color = "text-green-600" if rev_growth_rate and not rev_growth_rate.startswith("-") else "text-red-600"
    eg_color = "text-green-600" if earn_growth_rate and not earn_growth_rate.startswith("-") else "text-red-600"

    growth_signals = []
    caution_signals = []
    for line in raw.splitlines():
        cl = _clean_line(line)
        if cl.lower().startswith("growth signal:"):
            growth_signals.append(cl.split(":", 1)[1].strip())
        elif cl.lower().startswith("caution signal:"):
            caution_signals.append(cl.split(":", 1)[1].strip())

    body = f'''
    <div class="flex items-start justify-between mb-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center"><span class="text-green-600 text-lg">&#x1F3E5;</span></div>
        <div>
          <h3 class="text-lg font-bold text-gray-900">Financial Health</h3>
          <p class="text-xs text-gray-500">Growth, profitability &amp; stability</p>
        </div>
      </div>
      <span class="px-3 py-1 rounded text-xs font-bold {badge_cls}">{_esc(health_status)}</span>
    </div>

    <!-- Top 4 metrics -->
    <div class="grid grid-cols-4 gap-3 mb-5">
      <div class="bg-white border border-gray-200 rounded-xl p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Revenue Growth</p>{_info_icon("Year-over-year revenue growth rate.")}</div>
          <span class="w-7 h-7 rounded-lg bg-green-100 flex items-center justify-center text-green-600 text-xs">&#x1F4C8;</span>
        </div>
        <p class="text-2xl font-bold text-gray-900 mt-2">{_esc(rev_growth_rate) if rev_growth_rate else 'N/A'}<span class="text-sm font-semibold text-gray-400 ml-0.5">%</span></p>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Earnings Growth</p>{_info_icon("Year-over-year net income growth rate.")}</div>
          <span class="w-7 h-7 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600 text-xs">&#x26A1;</span>
        </div>
        <p class="text-2xl font-bold text-gray-900 mt-2">{_esc(earn_growth_rate) if earn_growth_rate else 'N/A'}<span class="text-sm font-semibold text-gray-400 ml-0.5">%</span></p>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Debt-to-Equity</p>{_info_icon("Total debt divided by shareholder equity. Lower = less leveraged.")}</div>
          <span class="w-7 h-7 rounded-lg bg-orange-100 flex items-center justify-center text-orange-600 text-xs">&#x1F534;</span>
        </div>
        <p class="text-2xl font-bold text-gray-900 mt-2">{_esc(debt_ratio) if debt_ratio else 'N/A'}<span class="text-sm font-semibold text-gray-400 ml-0.5">%</span></p>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Free Cash Flow</p>{_info_icon("Cash generated after capital expenditures. Key to dividends and buybacks.")}</div>
          <span class="w-7 h-7 rounded-lg bg-green-100 flex items-center justify-center text-green-600 text-xs">&#x1F4B2;</span>
        </div>
        <p class="text-2xl font-bold text-gray-900 mt-2">{_esc(cash_val) if cash_val else 'N/A'}</p>
      </div>
    </div>

    <!-- Growth & Profitability Metrics -->
    <div class="bg-green-50 border border-green-200 rounded-xl p-4 mb-5">
      <div class="flex items-center gap-2 mb-3">
        <span class="w-8 h-8 rounded-lg bg-green-500 flex items-center justify-center text-white text-sm">&#x1F4C8;</span>
        <p class="text-sm font-bold text-gray-800">&#x1F4CA; Growth &amp; Profitability Metrics</p>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div class="bg-white border border-gray-200 rounded-xl p-4">
          <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Revenue Growth Rate</p>{_info_icon("Annualized revenue growth over the analysis period.")}</div>
          <p class="text-2xl font-bold {rg_color} mt-2">{_esc(rev_growth_rate) if rev_growth_rate else 'N/A'}%</p>
        </div>
        <div class="bg-white border border-gray-200 rounded-xl p-4">
          <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">Earnings Growth Rate</p>{_info_icon("Annualized net income growth over the analysis period.")}</div>
          <p class="text-2xl font-bold {eg_color} mt-2">{_esc(earn_growth_rate) if earn_growth_rate else 'N/A'}%</p>
        </div>
      </div>
    </div>

    <!-- Key Financial Insights -->
    <div class="mb-1">
      <p class="text-sm font-bold text-gray-800 mb-3">&#x1F4A1; Key Financial Insights</p>
      <div class="grid grid-cols-2 gap-3">
        <div class="bg-white border border-gray-200 rounded-xl p-4">
          <div class="flex items-center gap-2 mb-1">
            <span class="w-5 h-5 rounded bg-blue-100 flex items-center justify-center text-blue-600 text-xs">i</span>
            <p class="text-sm font-bold text-gray-800">Insight</p>
          </div>
          <p class="text-sm text-gray-600">{_esc(insight) if insight else 'N/A'}</p>
        </div>
        <div class="bg-white border border-gray-200 rounded-xl p-4">
          <div class="flex items-center gap-2 mb-1">
            <span class="w-5 h-5 rounded bg-blue-100 flex items-center justify-center text-blue-600 text-xs">i</span>
            <p class="text-sm font-bold text-gray-800">Structured Summary</p>
          </div>
          <p class="text-sm text-gray-600">{_esc(structured_summary) if structured_summary else 'N/A'}</p>
        </div>

        <div class="bg-green-50 border border-green-300 border-l-4 border-l-green-500 rounded-xl p-4">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-green-600 font-bold">&#x2713;</span>
            <p class="text-sm font-bold text-green-700">Revenue Growth Rate</p>
          </div>
          <p class="text-sm text-green-800">{_esc(rev_desc) if rev_desc else 'N/A'}</p>
        </div>
        <div class="bg-green-50 border border-green-300 border-l-4 border-l-green-500 rounded-xl p-4">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-green-600 font-bold">&#x2713;</span>
            <p class="text-sm font-bold text-green-700">Net Income Growth Rate</p>
          </div>
          <p class="text-sm text-green-800">{_esc(profit_desc) if profit_desc else 'N/A'}</p>
        </div>

        <div class="bg-white border border-gray-200 rounded-xl p-4">
          <div class="flex items-center gap-2 mb-1">
            <span class="w-5 h-5 rounded bg-blue-100 flex items-center justify-center text-blue-600 text-xs">i</span>
            <p class="text-sm font-bold text-gray-800">Debt-to-Equity Ratio</p>
          </div>
          <p class="text-lg font-bold text-gray-900">{_esc(debt_ratio) if debt_ratio else 'N/A'}</p>
        </div>
        {"".join(f'''<div class="bg-white border border-gray-200 rounded-xl p-4">
          <div class="flex items-center gap-2 mb-1"><span class="text-green-600 font-bold">&#x2713;</span><p class="text-sm font-bold text-gray-800">Growth Signal</p></div>
          <p class="text-sm text-gray-600">{_esc(g)}</p>
        </div>''' for g in growth_signals)}
      </div>

      {"".join(f'''<div class="bg-amber-50 border border-amber-300 border-l-4 border-l-amber-500 rounded-xl p-4 mt-3">
        <div class="flex items-center gap-2 mb-1"><span class="text-amber-600">&#x26A0;</span><p class="text-sm font-bold text-amber-700">Caution Signal</p></div>
        <p class="text-sm text-amber-800">{_esc(c)}</p>
      </div>''' for c in caution_signals)}
    </div>
    '''
    return _card(body, data_section="health")


# ── 4. Valuation ─────────────────────────────────────────────

def _render_valuation_card(raw: str, symbol: str) -> str:
    insight = _parse_kv(raw, "Insight") or ""

    val_verdict_line = _parse_kv(raw, "Valuation Verdict")
    val_answer = "Fair"
    val_desc = ""
    if val_verdict_line and " | " in val_verdict_line:
        val_answer, val_desc = val_verdict_line.split(" | ", 1)
    elif val_verdict_line:
        val_answer = val_verdict_line

    is_expensive = val_answer.lower() in ("yes", "expensive", "overvalued")
    is_cheap = val_answer.lower() in ("no", "cheap", "undervalued")

    if is_expensive:
        badge_text, badge_cls = "OVERVALUED", "bg-red-100 text-red-700 border border-red-300"
    elif is_cheap:
        badge_text, badge_cls = "UNDERVALUED", "bg-green-100 text-green-700 border border-green-300"
    else:
        badge_text, badge_cls = "FAIR VALUE", "bg-yellow-100 text-yellow-700 border border-yellow-300"

    pe = _parse_kv(raw, "P/E Ratio") or _parse_kv(raw, "P/E (x)")
    fwd_pe = _parse_kv(raw, "Forward P/E") or _parse_kv(raw, "Forward P/E (x)")
    pb = _parse_kv(raw, "P/B Ratio") or _parse_kv(raw, "P/B (x)")
    ps = _parse_kv(raw, "P/S Ratio") or _parse_kv(raw, "P/S (x)")
    peg = _parse_kv(raw, "PEG Ratio")
    ev_ebitda = _parse_kv(raw, "EV/EBITDA")

    def _val_style(val_str: str | None, high: float, low: float) -> tuple[str, str]:
        """Return (text_color, box_classes) based on value thresholds."""
        if not val_str:
            return "text-gray-900", "bg-white border border-gray-200"
        try:
            v = float(val_str.replace("x", "").replace(",", "").strip())
        except ValueError:
            return "text-gray-900", "bg-white border border-gray-200"
        if v >= high:
            return "text-red-600", "bg-white border border-red-300 border-l-4 border-l-red-500"
        if v <= low:
            return "text-green-600", "bg-white border border-green-300 border-l-4 border-l-green-500"
        return "text-blue-600", "bg-white border border-blue-300 border-l-4 border-l-blue-500"

    pe_c, pe_bg = _val_style(pe, 25, 12)
    fpe_c, fpe_bg = _val_style(fwd_pe, 25, 12)
    pb_c, pb_bg = _val_style(pb, 3, 1)
    ps_c, ps_bg = _val_style(ps, 5, 1)
    peg_c, peg_bg = _val_style(peg, 1.5, 0.8)
    ev_c, ev_bg = _val_style(ev_ebitda, 15, 8)

    def _metric_box(label: str, value: str | None, suffix: str, color: str, bg: str, tip: str = "", icon: str = "") -> str:
        v = value.rstrip(suffix).strip() if value else ""
        v = _esc(v) if v else "N/A"
        ic = f'<span class="text-gray-400 text-sm">{icon}</span>' if icon else ""
        return f'''<div class="{bg} rounded-xl p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-1"><p class="text-sm font-semibold text-gray-800">{label}</p>{_info_icon(tip)}</div>{ic}
          </div>
          <p class="text-2xl font-bold {color} mt-2">{v}<span class="text-sm font-semibold text-gray-400 ml-0.5">{suffix}</span></p>
        </div>'''

    implications = []
    for line in raw.splitlines():
        cl = _clean_line(line)
        if cl.lower().startswith("implication:"):
            implications.append(cl.split(":", 1)[1].strip())
    impl_html = f'''<div class="flex items-start gap-2 mt-4 text-sm text-gray-600">
      <span class="font-bold text-gray-500">&#x1F4CA;</span>
      <p><span class="font-semibold">Implication:</span> {_esc(implications[0])}</p>
    </div>''' if implications else ""

    body = f'''
    <div class="flex items-start justify-between mb-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center"><span class="text-blue-600 text-lg">&#x1F4CA;</span></div>
        <div>
          <h3 class="text-lg font-bold text-gray-900">Valuation &amp; Profitability</h3>
          <p class="text-xs text-gray-500">Financial ratios &amp; metrics</p>
        </div>
      </div>
      <span class="px-3 py-1 rounded text-xs font-bold {badge_cls}">{badge_text}</span>
    </div>

    <div class="grid grid-cols-2 gap-3">
      {_metric_box("P/E Ratio", pe, "x", pe_c, pe_bg, "Price-to-Earnings: how much you pay per dollar of earnings. Lower = cheaper.")}
      {_metric_box("Forward P/E", fwd_pe, "x", fpe_c, fpe_bg, "Based on estimated future earnings. Lower = cheaper relative to growth.")}
      {_metric_box("P/B Ratio", pb, "x", pb_c, pb_bg, "Price-to-Book: stock price vs net asset value. Below 1 = trading below book value.")}
      {_metric_box("P/S Ratio", ps, "x", ps_c, ps_bg, "Price-to-Sales: what you pay per dollar of revenue. Useful for unprofitable companies.")}
      {_metric_box("PEG Ratio", peg, "x", peg_c, peg_bg, "P/E adjusted for growth. Below 1 = undervalued relative to growth rate.", "&#x1F4B2;")}
      {_metric_box("EV/EBITDA", ev_ebitda, "x", ev_c, ev_bg, "Enterprise value vs operating profit. Lower = cheaper on an operational basis.", "&#x1F4C8;")}
    </div>

    <div class="mt-4 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
      <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0"><span class="text-amber-600">&#x1F4A1;</span></div>
      <div>
        <p class="text-sm font-bold text-gray-800">Valuation Insight</p>
        <p class="text-sm text-amber-800 mt-0.5">{_esc(insight or val_desc or "Valuation analysis completed.")}</p>
      </div>
    </div>

    {impl_html}
    '''
    return _card(body, data_section="valuation")


# ── 5. Market Sentiment & News ───────────────────────────────

def _render_sentiment_card(raw: str, symbol: str) -> str:
    sentiment_signal = _parse_kv(raw, "Sentiment Signal") or "Neutral"
    analyst_consensus = _parse_kv(raw, "Analyst Consensus") or ""
    structured_summary = _parse_kv(raw, "Structured Summary") or ""
    insight = _parse_kv(raw, "Insight") or ""

    badge_cls = _badge_classes(sentiment_signal)
    signal_badge_cls = _badge_classes(sentiment_signal)

    buy_count = ""
    if analyst_consensus:
        buy_m = re.search(r"Buy\s+(\d+)", analyst_consensus)
        total_m = re.search(r"\((\d+)\s+analyst", analyst_consensus)
        if buy_m and total_m:
            buy_count = f"Buy {buy_m.group(1)}/{total_m.group(1)}"
        elif buy_m:
            buy_count = f"Buy {buy_m.group(1)}"

    news_items: list[tuple[str, str, str]] = []
    for line in raw.splitlines():
        cl = line.strip()
        if cl.lower().startswith("news:"):
            payload = cl.split(":", 1)[1].strip()
            parts = [p.strip() for p in payload.split("|")]
            title = parts[0] if parts else "News"
            publisher = parts[1] if len(parts) > 1 else "source"
            url = parts[2] if len(parts) > 2 else ""
            if title:
                news_items.append((title, publisher, url))

    def _news_row(title: str, publisher: str, url: str) -> str:
        tag = "a" if url.startswith("http") else "div"
        href = f' href="{_esc(url)}" target="_blank" rel="noopener noreferrer"' if tag == "a" else ""
        hover = " hover:bg-gray-50 transition-colors" if tag == "a" else ""
        return f'''<{tag}{href} class="flex items-center justify-between bg-white border border-gray-200 rounded-xl p-4{hover}">
          <div class="flex-1 min-w-0 mr-4">
            <p class="text-sm font-medium text-gray-800 leading-snug">{_esc(title)}</p>
            <p class="text-xs text-gray-400 mt-1 flex items-center gap-1">&#x1F517; {_esc(publisher)}</p>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <span class="text-gray-300">&mdash;</span>
            <span class="px-2.5 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-600 border border-gray-200">Neutral</span>
          </div>
        </{tag}>'''

    news_html = "\n".join(_news_row(t, p, u) for t, p, u in news_items[:4])

    body = f'''
    <div class="flex items-start justify-between mb-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center"><span class="text-blue-600 text-lg">&#x1F4E1;</span></div>
        <div>
          <h3 class="text-lg font-bold text-gray-900">Market Sentiment</h3>
          <p class="text-xs text-gray-500">Analyst consensus &amp; news analysis</p>
        </div>
      </div>
      <span class="px-3 py-1 rounded text-xs font-bold {badge_cls}">{_esc(sentiment_signal.upper())}</span>
    </div>

    <!-- Top 3 metrics -->
    <div class="grid grid-cols-3 gap-3 mb-5">
      <div class="bg-white border border-gray-200 rounded-xl p-4">
        <div class="flex items-center gap-1 mb-2">
          <span class="text-blue-500 text-sm">&#x1F4C8;</span>
          <p class="text-sm font-semibold text-gray-800">Analyst Consensus</p>
        </div>
        <p class="text-xl font-bold text-gray-900">{_esc(buy_count) if buy_count else _esc(analyst_consensus) if analyst_consensus else 'N/A'}</p>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-4">
        <p class="text-sm font-semibold text-gray-800 mb-2">Overall Status</p>
        <span class="inline-block px-2.5 py-0.5 rounded text-xs font-bold {signal_badge_cls}">{_esc(sentiment_signal.upper())}</span>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-4">
        <p class="text-sm font-semibold text-gray-800 mb-2">Sentiment Signal</p>
        <span class="inline-block px-2.5 py-0.5 rounded text-xs font-bold {signal_badge_cls}">{_esc(sentiment_signal)}</span>
      </div>
    </div>

    <!-- Latest News -->
    <div class="mb-5">
      <div class="flex items-center justify-between mb-3">
        <p class="text-sm font-bold text-gray-800">&#x1F4F0; Latest News</p>
        <p class="text-xs text-gray-400 italic">Tagged with AI sentiment analysis</p>
      </div>
      <div class="space-y-2">
        {news_html if news_html else '<p class="text-sm text-gray-400 italic py-2">No news items available.</p>'}
      </div>
    </div>

    <!-- Sentiment Insight -->
    <div class="bg-indigo-50 border border-indigo-200 rounded-xl p-4 flex items-start gap-3">
      <div class="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center flex-shrink-0"><span class="text-white text-sm">&#x1F3AF;</span></div>
      <div>
        <p class="text-sm font-bold text-gray-800">&#x1F3AF; Sentiment Insight</p>
        <p class="text-sm text-indigo-800 mt-0.5">{_esc(insight) if insight else _esc(structured_summary) if structured_summary else "Sentiment analysis completed."}</p>
      </div>
    </div>
    '''
    return _card(body, data_section="sentiment")


# ── 6. Quality Review ────────────────────────────────────────

def _render_review_card(raw: str, symbol: str) -> str:
    structured_summary = _parse_kv(raw, "Structured Summary") or ""

    accuracy_items = []
    watchout_items = []
    confirmed_items = []
    for line in raw.splitlines():
        cl = _clean_line(line)
        if cl.lower().startswith("data accuracy:"):
            accuracy_items.append(cl.split(":", 1)[1].strip())
        elif cl.lower().startswith("watchout:"):
            watchout_items.append(cl.split(":", 1)[1].strip())
        elif cl.lower().startswith("confirmed:"):
            confirmed_items.append(cl.split(":", 1)[1].strip())

    def _review_item(icon_type: str, label: str, text: str) -> str:
        if icon_type == "check":
            bg = "bg-green-50 border-green-200"
            icon = '<svg class="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
            text_cls = "text-green-700"
        else:
            bg = "bg-yellow-50 border-yellow-200"
            icon = '<svg class="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>'
            text_cls = "text-yellow-800"
        return f'''
        <div class="{bg} border rounded-lg p-3 flex items-start gap-2">
          {icon}
          <div>
            <p class="text-sm font-bold text-gray-800">{_esc(label)}</p>
            <p class="text-sm {text_cls}">{_esc(text)}</p>
          </div>
        </div>'''

    items_html = ""
    for item in accuracy_items:
        items_html += _review_item("check", "Data Accuracy", item)
    for item in watchout_items:
        items_html += _review_item("warning", "Watchout", item)
    for item in confirmed_items:
        items_html += _review_item("check", "Confirmed", item)

    if not items_html:
        items_html = '<p class="text-sm text-gray-400 italic">No review items available.</p>'

    body = f'''
    <div class="flex items-start justify-between mb-1">
      <div class="flex items-center gap-2">
        <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <h3 class="text-lg font-bold text-gray-900">Quality Review</h3>
      </div>
      <span class="px-3 py-1 rounded bg-blue-100 text-blue-700 text-xs font-bold">{_esc(symbol)}</span>
    </div>
    <p class="text-sm text-gray-500 mt-1 mb-4">{_esc(structured_summary) if structured_summary else 'Quality review completed.'}</p>
    <div class="space-y-3">
      {items_html}
    </div>
    '''
    return _card(body, data_section="review")


# ── Data Quality Card ────────────────────────────────────────

def _render_data_quality_card(raw: str, symbol: str) -> str:
    summary = _parse_kv(raw, "Structured Summary") or "Data quality check completed."
    gate = _parse_kv(raw, "Gate Status") or "UNKNOWN"
    context = _parse_kv(raw, "Market Context") or ""
    company_type = _parse_kv(raw, "Company Type") or ""

    validated = len(_parse_kv_all(raw, "Validated File", limit=50))
    missing = len(_parse_kv_all(raw, "Missing/Invalid File", limit=50))
    critical = len(_parse_kv_all(raw, "Critical Issue", limit=50))
    warnings = len(_parse_kv_all(raw, "Warning", limit=50))

    gate_up = gate.upper().replace(" ", "_")
    if gate_up == "PASS":
        gate_cls = "bg-green-100 text-green-700 border border-green-300"
    elif gate_up in ("FAIL", "HARD_BLOCKED"):
        gate_cls = "bg-red-100 text-red-700 border border-red-300"
    else:
        gate_cls = "bg-yellow-100 text-yellow-700 border border-yellow-300"

    stats_items = []
    if validated:
        stats_items.append(f'<span class="text-green-600 font-semibold">{validated} validated</span>')
    if missing:
        stats_items.append(f'<span class="text-red-600 font-semibold">{missing} missing</span>')
    if critical:
        stats_items.append(f'<span class="text-red-600 font-semibold">{critical} critical</span>')
    if warnings:
        stats_items.append(f'<span class="text-yellow-600 font-semibold">{warnings} warnings</span>')
    stats_html = ' <span class="text-gray-300">|</span> '.join(stats_items) if stats_items else ""

    meta_parts = []
    if company_type:
        meta_parts.append(_esc(company_type))
    if context:
        meta_parts.append(_esc(context))
    meta_html = f'<p class="text-sm text-gray-500 mt-2">{" &middot; ".join(meta_parts)}</p>' if meta_parts else ""

    return _card(f'''
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <span>&#x1F50D;</span>
        <h3 class="text-lg font-bold text-gray-900">Data Quality</h3>
      </div>
      <span class="px-3 py-1 rounded text-xs font-bold {gate_cls}">{_esc(gate)}</span>
    </div>
    <p class="text-sm text-gray-700 leading-relaxed">{_esc(summary)}</p>
    <div class="flex items-center gap-2 mt-3 text-sm">{stats_html}</div>
    {meta_html}
    ''', data_section="data-quality")


# ══════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════

def _format_analysis_block(log_entry: LogEntry) -> str:
    substage_val = log_entry.substage.value
    raw = log_entry.message or ""
    symbol = (log_entry.symbol or "").upper()

    renderers = {
        "analyzing_valuation_ratios": _render_valuation_card,
        "analyzing_price_performance": _render_performance_card,
        "analyzing_financial_health": _render_health_card,
        "analyzing_market_sentiment": _render_sentiment_card,
        "reviewing_analysis": _render_review_card,
        "generating_investment_report": _render_report_cards,
    }

    ws_summary = _extract_ws_summary(raw)
    extra_attrs = f' data-substage="{substage_val}"'
    if ws_summary:
        extra_attrs += f' data-ws-summary="{ws_summary}"'

    renderer = renderers.get(substage_val)
    if renderer:
        result = renderer(raw, symbol)
        tag_end = result.index(">")
        return result[:tag_end] + extra_attrs + result[tag_end:]

    return ""


# ── Public API ───────────────────────────────────────────────

def _ws_entry(text: str, status: str = "success", arrow: bool = False,
              stage: str = "", substage: str = "") -> str:
    """Build a single workspace-entry div."""
    prefix = "&rarr; " if arrow else ""
    sub_attr = f' data-substage="{substage}"' if substage else ""
    return (f'<div class="workspace-entry" data-status="{status}" data-stage="{stage}"{sub_attr}>'
            f'<span class="ws-icon"></span>'
            f'<span class="ws-text">{prefix}{text}</span></div>')


def format_log_entry(log_entry: LogEntry) -> str:
    """Format a log entry for HTML display — analysis entries get rich cards,
    everything else gets compact workspace-entry lines."""

    # Stage-level entries (no substage) — no arrow prefix
    if log_entry.substage is None:
        text = _esc(log_entry.message or log_entry.stage.display_name)
        return _ws_entry(text, log_entry.status_type.value, arrow=False, stage=log_entry.stage.value)

    # Analysis entries — rich card for SUCCESS, workspace line for progress/failed
    if _is_analysis_entry(log_entry):
        if log_entry.status_type == StatusType.SUCCESS:
            return _format_analysis_block(log_entry)
        label = _esc(log_entry.substage.display_name)
        return (f'<div class="workspace-entry" data-status="{log_entry.status_type.value}" '
                f'data-stage="{log_entry.stage.value}" data-substage="{log_entry.substage.value}">'
                f'<span class="ws-icon"></span>'
                f'<span class="ws-text">&rarr; {label}</span></div>')

    # Non-analysis substage entries (download, validation, etc.) — with arrow
    text = _esc(log_entry.message or log_entry.substage.display_name)
    return _ws_entry(text, log_entry.status_type.value, arrow=True,
                     stage=log_entry.stage.value, substage=log_entry.substage.value)
