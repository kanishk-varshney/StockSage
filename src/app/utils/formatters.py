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


def _info_icon() -> str:
    return '<svg class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'


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
        <span class="px-4 py-1.5 rounded-full border border-gray-300 text-sm font-semibold text-gray-700">{_esc(cap_size) if cap_size else '<!-- TODO: Cap Size not available -->'}</span>
      </div>
      <div class="flex items-baseline gap-8 mt-4">
        <div>
          <p class="text-sm text-gray-500">Current Price</p>
          <p class="text-4xl font-bold text-gray-900">{_esc(price) if price else '<!-- TODO: Price not available -->'}</p>
        </div>
        <div>
          <p class="text-sm text-gray-500">Market Cap</p>
          <p class="text-xl font-bold text-gray-700">{_esc(mcap) if mcap else '<!-- TODO: Market Cap not available -->'}</p>
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
          &#x1F4C8; {_esc(verdict)}
        </span>
        <div>
          <p class="text-sm text-gray-500">Confidence Level</p>
          <span class="inline-block px-3 py-1 rounded border text-sm font-semibold {conf_cls}">{_esc(confidence)}</span>
        </div>
      </div>
      <div class="mt-5 border border-gray-200 rounded-lg p-4 bg-white">
        <p class="text-base text-gray-700 leading-relaxed">{_esc(summary) if summary else '<!-- TODO: Plain-English Summary not generated by LLM yet -->'}</p>
      </div>
      <div class="flex flex-wrap gap-2.5 mt-4">
        <span class="help-icon-wrapper px-4 py-1.5 rounded-full border border-gray-300 text-sm font-medium text-gray-600" data-tooltip="{tip_why}">Why this verdict?</span>
        <span class="help-icon-wrapper px-4 py-1.5 rounded-full border border-gray-300 text-sm font-medium text-gray-600" data-tooltip="{tip_who}">Who should invest?</span>
        <span class="help-icon-wrapper px-4 py-1.5 rounded-full border border-gray-300 text-sm font-medium text-gray-600" data-tooltip="{tip_risk}">Key risks</span>
      </div>
    </div>

    <div class="flex items-center gap-4 mt-5 text-base">
      <span class="text-gray-500">Sector:</span>
      <span class="px-2.5 py-0.5 bg-gray-100 rounded text-sm font-semibold text-gray-700">{_esc(sector) if sector else '<!-- TODO: Sector not available -->'}</span>
      <span class="text-gray-500">Segment:</span>
      <span class="text-gray-700 text-sm">{_esc(segment) if segment else '<!-- TODO: Segment not available -->'}</span>
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
    suited = _SUITED_TEMPLATES.get(verdict, _SUITED_TEMPLATES["HOLD"])
    not_ideal = _NOT_IDEAL_TEMPLATES.get(verdict, _NOT_IDEAL_TEMPLATES["HOLD"])

    strengths = [l.split(":", 1)[1].strip() for l in sections.get("OTHER", []) if l.lower().startswith("strength:")]
    risks = [l.split(":", 1)[1].strip() for l in sections.get("OTHER", []) if l.lower().startswith("risk:")]
    advice_lines = [l.split(":", 1)[1].strip() for l in sections.get("OTHER", []) if l.lower().startswith("advice:")]

    advice_own = advice_lines[0] if len(advice_lines) > 0 else "<!-- TODO: Advice for existing holders not generated -->"
    advice_buy = advice_lines[1] if len(advice_lines) > 1 else "<!-- TODO: Advice for potential buyers not generated -->"

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
          <p class="text-sm text-gray-600">{_esc(advice_own)}</p>
        </div>
        <div class="bg-white border border-gray-100 rounded-lg p-4">
          <p class="text-sm font-bold text-gray-800 mb-1">&#x1F3AF; If you&#39;re considering buying today:</p>
          <p class="text-sm text-gray-600">{_esc(advice_buy)}</p>
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

def _render_performance_card(raw: str, symbol: str) -> str:
    total_return = _parse_kv(raw, "Total Return (%)")
    annualized = _parse_kv(raw, "Annualized Return (%)")
    volatility = _parse_kv(raw, "Volatility (%)")
    vol_label = _parse_kv(raw, "Volatility Label") or "Moderate"
    max_dd = _parse_kv(raw, "Max Drawdown (%)")
    beta = _parse_kv(raw, "Beta (vs market)")
    sharpe = _parse_kv(raw, "Sharpe Ratio")
    market_return = _parse_kv(raw, "Market Total Return (%)")
    perf_badge = _parse_kv(raw, "Performance Badge") or "IN LINE"
    insight = _parse_kv(raw, "Insight") or ""

    chart_m = re.search(r"CHART_DATA:\s*(\{.+\})", raw)
    chart_json = chart_m.group(1) if chart_m else ""

    badge_cls = _badge_classes(perf_badge.split()[0] if perf_badge else "IN LINE")

    total_color = "text-green-600" if total_return and not total_return.startswith("-") else "text-red-600"
    ann_color = "text-green-600" if annualized and not annualized.startswith("-") else "text-red-600"
    dd_color = "text-red-600"

    vol_badge_cls = _badge_classes(vol_label)

    body = f'''
    <div class="flex items-start justify-between mb-1">
      <div class="flex items-center gap-2">
        <span class="text-xl text-green-500">&#x1F4C8;</span>
        <div>
          <h3 class="text-lg font-bold text-gray-900">Price Performance &amp; Risk</h3>
          <p class="text-xs text-gray-500">How the stock has performed vs market risk</p>
        </div>
      </div>
      <span class="px-3 py-1 rounded text-xs font-bold {badge_cls}">{_esc(perf_badge)}</span>
    </div>

    <div class="bg-white border border-gray-200 rounded-xl p-4 mt-4 mb-4">
      <div class="flex items-center justify-between mb-3">
        <p class="text-sm font-bold text-gray-800">Stock vs Market Performance</p>
        <div class="flex gap-1">
          <span class="px-2 py-0.5 rounded border border-gray-300 text-xs font-medium text-gray-700 bg-white">1Y</span>
          <span class="px-2 py-0.5 rounded text-xs font-medium text-gray-400">3Y</span>
          <span class="px-2 py-0.5 rounded text-xs font-medium text-gray-400">5Y</span>
        </div>
      </div>
      <div class="h-48" id="perf-chart-container" data-chart='{_esc(chart_json) if chart_json else ""}'>
        <canvas id="perf-chart"></canvas>
      </div>
      <div class="flex items-center gap-4 mt-2 text-xs text-gray-500">
        <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-green-500 inline-block"></span> Stock Performance</span>
        <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-blue-400 inline-block"></span> Market Benchmark</span>
      </div>
    </div>

    <div class="mb-4">
      <p class="text-sm font-bold text-gray-800 mb-2">Key Takeaways</p>
      <div class="flex items-start justify-between flex-wrap gap-4">
        <div>
          <p class="text-xs text-gray-500">Total Return</p>
          <p class="text-2xl font-bold {total_color}">{_esc(total_return) if total_return else '<!-- TODO: Total return not computed -->'}</p>
          <p class="text-xs text-gray-400 mt-0.5">{_esc(total_return) if total_return else ''} over the past year vs. {_esc(market_return) if market_return else 'N/A'} for the S&amp;P 500 (market index)</p>
        </div>
        <div>
          <div class="flex items-center gap-1">
            <p class="text-xs text-gray-500">Volatility</p>
            {_info_icon()}
          </div>
          <span class="inline-block px-2 py-0.5 rounded text-xs font-bold mt-1 {vol_badge_cls}">{_esc(vol_label)}</span>
          <p class="text-xs text-gray-400 mt-0.5">{_esc(volatility)} annualized</p>
        </div>
      </div>
    </div>

    <details class="border border-gray-200 rounded-lg mb-4">
      <summary class="px-4 py-2.5 cursor-pointer text-sm font-medium text-gray-600 text-center select-none hover:bg-gray-50">
        <span class="details-show">+ Show technical performance metrics</span>
        <span class="details-hide">&ndash; Hide technical performance metrics</span>
      </summary>
      <div class="px-4 pb-4 pt-2">
        <div class="grid grid-cols-4 gap-3">
          <div class="text-center">
            <div class="flex items-center justify-center gap-1"><p class="text-xs text-gray-500">Beta (vs market)</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(beta) if beta else 'N/A'}</p>
          </div>
          <div class="text-center">
            <div class="flex items-center justify-center gap-1"><p class="text-xs text-gray-500">Annualized Return</p>{_info_icon()}</div>
            <p class="text-xl font-bold {ann_color} mt-1">{_esc(annualized) if annualized else 'N/A'}</p>
          </div>
          <div class="text-center">
            <div class="flex items-center justify-center gap-1"><p class="text-xs text-gray-500">Sharpe Ratio</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(sharpe) if sharpe else 'N/A'}</p>
          </div>
          <div class="text-center">
            <div class="flex items-center justify-center gap-1"><p class="text-xs text-gray-500">Max Drawdown</p>{_info_icon()}</div>
            <p class="text-xl font-bold {dd_color} mt-1">{_esc(max_dd) if max_dd else 'N/A'}</p>
          </div>
        </div>
      </div>
    </details>

    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-2">
      <svg class="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
      <div>
        <p class="text-sm font-bold text-gray-800">Risk Assessment</p>
        <p class="text-sm text-yellow-800">{_esc(insight) if insight else '<!-- TODO: Risk assessment insight not available -->'}</p>
      </div>
    </div>
    '''
    return _card(body, data_section="performance")


# ── 3. Business Health ───────────────────────────────────────

def _render_health_card(raw: str, symbol: str) -> str:
    health_status = _parse_kv(raw, "Health Status") or "STABLE"
    insight = _parse_kv(raw, "Insight") or ""
    structured_summary = _parse_kv(raw, "Structured Summary") or ""

    # Health description rows
    rev_desc, rev_val = _parse_kv_split(raw, "Revenue Growth Desc")
    profit_desc, profit_val = _parse_kv_split(raw, "Profit Growth Desc")
    debt_desc, debt_val = _parse_kv_split(raw, "Debt Desc")
    cash_desc, cash_val = _parse_kv_split(raw, "Cash Desc")

    # Financial metrics for expanded section
    pe = _parse_kv(raw, "P/E Ratio") or _parse_kv(raw, "P/E (x)")
    pb = _parse_kv(raw, "P/B Ratio") or _parse_kv(raw, "P/B (x)")
    fwd_pe = _parse_kv(raw, "Forward P/E") or _parse_kv(raw, "Forward P/E (x)")
    rev_growth_rate = _parse_kv(raw, "Revenue Growth Rate") or _parse_kv(raw, "Revenue Growth (%)")
    earn_growth_rate = _parse_kv(raw, "Earnings Growth Rate") or _parse_kv(raw, "Earnings Growth (%)")

    badge_cls = _badge_classes(health_status)

    def _health_row(label: str, desc: str, value: str) -> str:
        return f'''
        <div class="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
          <div class="flex-1">
            <div class="flex items-center gap-1">
              <p class="text-sm font-semibold text-gray-800">{_esc(label)}</p>
              {_info_icon()}
            </div>
            <p class="text-xs text-gray-500 mt-0.5">{_esc(desc) if desc else '<!-- TODO: Health description not available -->'}</p>
          </div>
          <p class="text-sm font-semibold text-gray-700 ml-4 text-right whitespace-nowrap">{_esc(value) if value else 'N/A'}</p>
        </div>'''

    rg_color = "text-green-600" if rev_growth_rate and not rev_growth_rate.startswith("-") else "text-red-600"
    eg_color = "text-green-600" if earn_growth_rate and not earn_growth_rate.startswith("-") else "text-red-600"

    # Growth signals from structured output
    growth_signals = []
    caution_signals = []
    for line in raw.splitlines():
        cl = _clean_line(line)
        if cl.lower().startswith("growth signal:"):
            growth_signals.append(cl.split(":", 1)[1].strip())
        elif cl.lower().startswith("caution signal:"):
            caution_signals.append(cl.split(":", 1)[1].strip())

    body = f'''
    <div class="flex items-start justify-between mb-1">
      <div class="flex items-center gap-2">
        <span class="text-xl">&#x1F4B2;</span>
        <div>
          <h3 class="text-lg font-bold text-gray-900">Financial Health</h3>
          <p class="text-xs text-gray-500">Translated - understanding the fundamentals</p>
        </div>
      </div>
      <span class="px-3 py-1 rounded text-xs font-bold {badge_cls}">{_esc(health_status)}</span>
    </div>

    <div class="mt-4">
      <div class="bg-green-50 rounded-t-lg px-4 py-2">
        <p class="text-sm font-bold text-gray-800">Business Health Status</p>
      </div>
      <div class="border border-gray-200 border-t-0 rounded-b-lg px-4">
        {_health_row("Revenue Growth", rev_desc, rev_val)}
        {_health_row("Profit Growth", profit_desc, profit_val)}
        {_health_row("Debt Situation", debt_desc, debt_val)}
        {_health_row("Cash Generation", cash_desc, cash_val)}
      </div>
    </div>

    <details class="border border-gray-200 rounded-lg mt-4">
      <summary class="px-4 py-2.5 cursor-pointer text-sm font-medium text-gray-600 text-center select-none hover:bg-gray-50">
        <span class="details-show">+ Show financial ratios &amp; detailed metrics</span>
        <span class="details-hide">&ndash; Hide financial ratios &amp; detailed metrics</span>
      </summary>
      <div class="px-4 pb-4 pt-2">
        <div class="grid grid-cols-3 gap-3 mb-4">
          <div class="border border-gray-200 rounded-lg p-3">
            <div class="flex items-center gap-1"><p class="text-xs text-gray-500">P/E Ratio</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(pe) if pe else 'N/A'}</p>
          </div>
          <div class="border border-gray-200 rounded-lg p-3">
            <div class="flex items-center gap-1"><p class="text-xs text-gray-500">P/B Ratio</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(pb) if pb else 'N/A'}</p>
          </div>
          <div class="border border-gray-200 rounded-lg p-3">
            <div class="flex items-center gap-1"><p class="text-xs text-gray-500">Forward P/E</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(fwd_pe) if fwd_pe else 'N/A'}</p>
          </div>
        </div>

        <div class="flex items-center gap-2 mb-3">
          <span class="text-sm">&#x1F4C8;</span>
          <p class="text-sm font-bold text-gray-800">Detailed Growth Metrics</p>
        </div>
        <div class="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p class="text-xs text-gray-500">Revenue Growth Rate</p>
            <p class="text-xl font-bold {rg_color}">{_esc(rev_growth_rate) if rev_growth_rate else 'N/A'}</p>
          </div>
          <div>
            <p class="text-xs text-gray-500">Earnings Growth Rate</p>
            <p class="text-xl font-bold {eg_color}">{_esc(earn_growth_rate) if earn_growth_rate else 'N/A'}</p>
          </div>
        </div>

        {"".join(f'<div class="bg-green-50 border-l-4 border-green-400 p-3 mb-2 rounded-r"><p class="text-sm text-green-800">{_esc(g)}</p></div>' for g in growth_signals)}
        {"".join(f'<div class="bg-yellow-50 border-l-4 border-yellow-400 p-3 mb-2 rounded-r"><p class="text-sm text-yellow-800">{_esc(c)}</p></div>' for c in caution_signals)}

        <div class="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-2">
          <p class="text-sm font-bold text-gray-700">Insight</p>
          <p class="text-sm text-gray-600">{_esc(insight) if insight else '<!-- TODO: Health insight not available -->'}</p>
        </div>
        <div class="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <p class="text-sm font-bold text-gray-700">Structured Summary</p>
          <p class="text-sm text-gray-600">{_esc(structured_summary) if structured_summary else '<!-- TODO: Structured summary not generated -->'}</p>
        </div>
      </div>
    </details>
    '''
    return _card(body, data_section="health")


# ── 4. Valuation ─────────────────────────────────────────────

def _render_valuation_card(raw: str, symbol: str) -> str:
    insight = _parse_kv(raw, "Insight") or ""
    structured_summary = _parse_kv(raw, "Structured Summary") or ""

    val_verdict_line = _parse_kv(raw, "Valuation Verdict")
    val_answer = "Unknown"
    val_desc = ""
    if val_verdict_line and " | " in val_verdict_line:
        val_answer, val_desc = val_verdict_line.split(" | ", 1)

    is_expensive = val_answer.lower() in ("yes", "expensive")
    is_cheap = val_answer.lower() in ("no", "cheap")

    if is_expensive:
        verdict_btn_cls = "bg-red-500 text-white"
        verdict_btn_text = f"Yes - {val_desc}" if val_desc else "Yes - Trading above fair value"
        means_text = "The stock price is high compared to the company's fundamentals. You're paying more for each dollar of earnings, assets, or sales than historical averages suggest is reasonable."
    elif is_cheap:
        verdict_btn_cls = "bg-green-500 text-white"
        verdict_btn_text = f"No - {val_desc}" if val_desc else "No - Trading below fair value"
        means_text = "The stock price is low compared to its fundamentals. This could present a buying opportunity if the company's business remains sound."
    else:
        verdict_btn_cls = "bg-yellow-500 text-white"
        verdict_btn_text = f"Fair - {val_desc}" if val_desc else "Fair - Trading near fair value"
        means_text = "The stock appears to be trading near its fundamental value based on current metrics."

    # Implications from structured output
    implications = []
    for line in raw.splitlines():
        cl = _clean_line(line)
        if cl.lower().startswith("implication:"):
            implications.append(cl.split(":", 1)[1].strip())

    # Financial metrics
    pe = _parse_kv(raw, "P/E Ratio") or _parse_kv(raw, "P/E (x)")
    fwd_pe = _parse_kv(raw, "Forward P/E") or _parse_kv(raw, "Forward P/E (x)")
    pb = _parse_kv(raw, "P/B Ratio") or _parse_kv(raw, "P/B (x)")
    ps = _parse_kv(raw, "P/S Ratio") or _parse_kv(raw, "P/S (x)")
    peg = _parse_kv(raw, "PEG Ratio")
    ev_ebitda = _parse_kv(raw, "EV/EBITDA")

    warning_items = ""
    if is_expensive:
        default_warnings = [
            "Earnings growth must accelerate significantly to justify current price",
            "Company must maintain or expand profit margins",
            "Market sentiment and investor confidence must remain strong",
        ]
        warning_items = "".join(f'<p class="text-sm text-red-700 ml-4">&#8250; {_esc(w)}</p>' for w in default_warnings)

    impl_text = ""
    if implications:
        impl_text = f'<p class="text-sm text-gray-600 mt-3">Implication: {_esc(implications[0])}</p>'

    body = f'''
    <div class="flex items-center gap-2 mb-1">
      <span class="text-xl text-blue-500">&#x1F4C8;</span>
      <div>
        <h3 class="text-lg font-bold text-gray-900">Valuation</h3>
        <p class="text-xs text-gray-500">Explain before numbers - is it expensive?</p>
      </div>
    </div>

    <div class="bg-slate-50 border border-gray-200 rounded-xl p-5 mt-4">
      <p class="text-sm font-bold text-gray-800 mb-2">Is the stock expensive?</p>
      <span class="inline-block px-4 py-1.5 rounded-lg text-sm font-bold {verdict_btn_cls}">{_esc(verdict_btn_text)}</span>
    </div>

    <div class="flex items-start gap-2 mt-4 p-4 bg-blue-50 border border-blue-100 rounded-lg">
      <svg class="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      <div>
        <p class="text-sm font-bold text-gray-800">What this means:</p>
        <p class="text-sm text-gray-600 mt-1">{_esc(means_text)}</p>
      </div>
    </div>

    {f"""<div class="mt-3 p-4 bg-red-50 border border-red-200 rounded-lg">
      <div class="flex items-center gap-2 mb-2">
        <svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>
        <p class="text-sm font-bold text-red-800">What needs to go right:</p>
      </div>
      {warning_items}
    </div>""" if is_expensive else ""}

    <div class="mt-3 bg-indigo-50 border-l-4 border-indigo-400 p-3 rounded-r">
      <p class="text-sm font-bold text-indigo-800">Analyst Insight</p>
      <p class="text-sm text-indigo-700">{_esc(insight) if insight else '<!-- TODO: Valuation insight not available -->'}</p>
    </div>

    <details class="border border-gray-200 rounded-lg mt-4">
      <summary class="px-4 py-2.5 cursor-pointer text-sm font-medium text-gray-600 text-center select-none hover:bg-gray-50">
        <span class="details-show">+ Show valuation metrics &amp; ratios</span>
        <span class="details-hide">&ndash; Hide valuation metrics &amp; ratios</span>
      </summary>
      <div class="px-4 pb-4 pt-2">
        <p class="text-sm font-bold text-gray-800 mb-3">Financial Summary</p>
        <div class="grid grid-cols-3 gap-3 mb-3">
          <div class="border border-gray-200 rounded-lg p-3">
            <div class="flex items-center gap-1"><p class="text-xs text-gray-500">P/E Ratio</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(pe) if pe else 'N/A'}</p>
          </div>
          <div class="border border-gray-200 rounded-lg p-3">
            <div class="flex items-center gap-1"><p class="text-xs text-gray-500">Forward P/E</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(fwd_pe) if fwd_pe else 'N/A'}</p>
          </div>
          <div class="border border-gray-200 rounded-lg p-3">
            <div class="flex items-center gap-1"><p class="text-xs text-gray-500">P/B Ratio</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(pb) if pb else 'N/A'}</p>
          </div>
          <div class="border border-gray-200 rounded-lg p-3">
            <div class="flex items-center gap-1"><p class="text-xs text-gray-500">P/S Ratio</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(ps) if ps else 'N/A'}</p>
          </div>
          <div class="border border-gray-200 rounded-lg p-3">
            <div class="flex items-center gap-1"><p class="text-xs text-gray-500">PEG Ratio</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(peg) if peg else 'N/A'}</p>
          </div>
          <div class="border border-gray-200 rounded-lg p-3">
            <div class="flex items-center gap-1"><p class="text-xs text-gray-500">EV/EBITDA</p>{_info_icon()}</div>
            <p class="text-xl font-bold text-gray-900 mt-1">{_esc(ev_ebitda) if ev_ebitda else 'N/A'}</p>
          </div>
        </div>
        {impl_text}
      </div>
    </details>
    '''
    return _card(body, data_section="valuation")


# ── 5. Market Sentiment & News ───────────────────────────────

def _render_sentiment_card(raw: str, symbol: str) -> str:
    sentiment_signal = _parse_kv(raw, "Sentiment Signal") or "Neutral"
    analyst_consensus = _parse_kv(raw, "Analyst Consensus") or ""
    structured_summary = _parse_kv(raw, "Structured Summary") or ""
    insight = _parse_kv(raw, "Insight") or ""

    badge_cls = _badge_classes(sentiment_signal)

    # Parse analyst numbers from "Buy 3 | Hold 1 | Sell 0 (4 analysts)"
    buy_count = ""
    total_analysts = ""
    if analyst_consensus:
        buy_m = re.search(r"Buy\s+(\d+)", analyst_consensus)
        total_m = re.search(r"\((\d+)\s+analyst", analyst_consensus)
        if buy_m and total_m:
            buy_count = f"{buy_m.group(1)}/{total_m.group(1)}"
        elif buy_m:
            buy_count = buy_m.group(1)

    # Parse news
    news_items: list[tuple[str, str, str]] = []
    for line in raw.splitlines():
        cl = line.strip()
        lower = cl.lower()
        if lower.startswith("news:"):
            payload = cl.split(":", 1)[1].strip()
            parts = [p.strip() for p in payload.split("|")]
            title = parts[0] if parts else "News"
            publisher = parts[1] if len(parts) > 1 else "source"
            url = parts[2] if len(parts) > 2 else ""
            if title:
                news_items.append((title, publisher, url))

    mood_cls = "bg-green-50 border-green-200" if sentiment_signal.lower() == "positive" else (
        "bg-red-50 border-red-200" if sentiment_signal.lower() == "negative" else "bg-yellow-50 border-yellow-200"
    )

    sentiment_badge_cls = _badge_classes(sentiment_signal)

    news_html = ""
    for title, publisher, url in news_items[:3]:
        if url.startswith("http"):
            news_html += f'''
            <a href="{_esc(url)}" target="_blank" rel="noopener noreferrer" class="block border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors">
              <p class="text-sm font-semibold text-gray-800">{_esc(title)}</p>
              <p class="text-xs text-gray-500 mt-0.5">{_esc(publisher)}</p>
            </a>'''
        else:
            news_html += f'''
            <div class="border border-gray-200 rounded-lg p-3">
              <p class="text-sm font-semibold text-gray-800">{_esc(title)}</p>
              <p class="text-xs text-gray-500 mt-0.5">{_esc(publisher)}</p>
            </div>'''

    body = f'''
    <div class="flex items-start justify-between mb-1">
      <div class="flex items-center gap-2">
        <span class="text-xl">&#x1F4F0;</span>
        <h3 class="text-lg font-bold text-gray-900">Market Sentiment</h3>
      </div>
      <span class="px-3 py-1 rounded text-xs font-bold {badge_cls}">{_esc(sentiment_signal.upper())}</span>
    </div>

    <div class="{mood_cls} border rounded-xl p-4 mt-4">
      <p class="text-sm font-bold text-gray-800 mb-2">Market Mood</p>
      <span class="inline-block px-2.5 py-0.5 rounded text-xs font-bold {sentiment_badge_cls} mb-2">{_esc(sentiment_signal.upper())}</span>
      <p class="text-sm text-gray-600">{_esc(structured_summary) if structured_summary else _esc(insight) if insight else '<!-- TODO: Market mood description not available -->'}</p>
    </div>

    <div class="grid grid-cols-2 gap-4 mt-4">
      <div class="border border-gray-200 rounded-lg p-4">
        <div class="flex items-center gap-1 mb-1">
          <span class="text-sm">&#x1F4C8;</span>
          <p class="text-sm font-bold text-gray-800">Analyst View</p>
        </div>
        <p class="text-2xl font-bold text-gray-900">Buy {_esc(buy_count) if buy_count else '<!-- TODO: Buy count not available -->'}</p>
        <p class="text-xs text-gray-500">Professional analyst recommendations</p>
      </div>
      <div class="border border-gray-200 rounded-lg p-4">
        <p class="text-sm font-bold text-gray-800 mb-1">Sentiment Signal</p>
        <span class="inline-block px-2.5 py-0.5 rounded text-xs font-bold {sentiment_badge_cls} mb-1">{_esc(sentiment_signal)}</span>
        <p class="text-xs text-gray-500">Overall market sentiment indicator</p>
      </div>
    </div>

    <div class="mt-4">
      <div class="flex items-center justify-between mb-1">
        <div>
          <p class="text-sm font-bold text-gray-800">Latest News</p>
          <p class="text-xs text-gray-400">Recent coverage from financial sources</p>
        </div>
        <a href="#" class="text-xs text-blue-600 hover:underline">Read latest news &rarr;</a>
      </div>
      <div class="space-y-2 mt-2">
        {news_html if news_html else '<p class="text-sm text-gray-400 italic"><!-- TODO: No news items available --></p>'}
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
        items_html = '<p class="text-sm text-gray-400 italic"><!-- TODO: No review items available --></p>'

    body = f'''
    <div class="flex items-start justify-between mb-1">
      <div class="flex items-center gap-2">
        <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <h3 class="text-lg font-bold text-gray-900">Quality Review</h3>
      </div>
      <span class="px-3 py-1 rounded bg-blue-100 text-blue-700 text-xs font-bold">{_esc(symbol)}</span>
    </div>
    <p class="text-sm text-gray-500 mt-1 mb-4">{_esc(structured_summary) if structured_summary else '<!-- TODO: Review summary not available -->'}</p>
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
        "validating_data_sanity": _render_data_quality_card,
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

    title = _ANALYSIS_TITLES.get(substage_val, html.escape(log_entry.substage.display_name))
    icon = _ANALYSIS_ICONS.get(substage_val, "&#x2728;")
    return _card(f'<div class="flex items-center gap-2"><span>{icon}</span><h3 class="text-lg font-bold text-gray-900">{title}</h3></div><p class="text-sm text-gray-600 mt-2">{_esc(raw[:500])}</p>')


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
