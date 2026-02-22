"""Log formatting utilities — evidence-first, compact analysis rendering."""

import html
import re
from urllib.parse import urlparse

from src.core.config.enums import StatusType
from src.core.config.models import LogEntry

_ANALYSIS_SUBSTAGES = {
    "analyzing_valuation_ratios",
    "analyzing_price_performance",
    "analyzing_financial_health",
    "analyzing_market_sentiment",
    "reviewing_analysis",
    "generating_investment_report",
}

_ANALYSIS_TITLES = {
    "analyzing_valuation_ratios": "Valuation &amp; Profitability",
    "analyzing_price_performance": "Price Performance &amp; Risk",
    "analyzing_financial_health": "Financial Health",
    "analyzing_market_sentiment": "Market Sentiment",
    "reviewing_analysis": "Quality Review",
    "generating_investment_report": "Final Analysis",
}

_ANALYSIS_ICONS = {
    "analyzing_valuation_ratios": "&#x1F4CA;",
    "analyzing_price_performance": "&#x1F4C8;",
    "analyzing_financial_health": "&#x1F3E6;",
    "analyzing_market_sentiment": "&#x1F4F0;",
    "reviewing_analysis": "&#x2705;",
    "generating_investment_report": "&#x1F3AF;",
}

_CARD_SENTIMENT_PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    "analyzing_valuation_ratios": [
        (r"\b(overvalued|expensive|overpriced)\b", "Overvalued", "badge-negative"),
        (r"\b(undervalued|cheap)\b", "Undervalued", "badge-positive"),
        (r"\b(fairly valued|fair value)\b", "Fairly Valued", "badge-neutral"),
    ],
    "analyzing_price_performance": [
        (r"\b(outperform|beat)\w*\b", "Outperforming", "badge-positive"),
        (r"\b(underperform|lag)\w*\b", "Underperforming", "badge-negative"),
        (r"\b(in line|similar)\b", "In Line", "badge-neutral"),
    ],
    "analyzing_financial_health": [
        (r"\b(strong|healthy|solid|excellent)\b", "Strong", "badge-positive"),
        (r"\b(weak|concern|worrying)\w*\b", "Weak", "badge-negative"),
        (r"\b(stable|steady|moderate)\b", "Stable", "badge-neutral"),
    ],
    "analyzing_market_sentiment": [
        (r"\b(positive|bullish|optimistic)\b", "Positive", "badge-positive"),
        (r"\b(negative|bearish|pessimistic)\b", "Negative", "badge-negative"),
        (r"\b(neutral|mixed)\b", "Neutral", "badge-neutral"),
    ],
}

_POSITIVE_WORDS = re.compile(r"\b(strong buy|buy|positive|bullish|outperform|undervalued|healthy|excellent|robust)\b", re.IGNORECASE)
_NEGATIVE_WORDS = re.compile(r"\b(strong sell|sell|negative|bearish|risk|overvalued|weak|concern|declining)\b", re.IGNORECASE)
_NEUTRAL_WORDS = re.compile(r"\b(neutral|mixed|hold|stable|in line|fairly valued)\b", re.IGNORECASE)
_SIGNAL_TAG_RE = re.compile(r"\[(POSITIVE|NEGATIVE|NEUTRAL|BULLISH|BEARISH)\]", re.IGNORECASE)
_SECTION_HEADER_RE = re.compile(r"^(?:\*{0,2})?([A-Z][A-Z0-9 &'?/\-]{4,})(?::)?(?:\*{0,2})?$")
_METRIC_LINE_RE = re.compile(
    r"^\s*[*\-\d.)]*\s*([A-Za-z][A-Za-z0-9/ ()&-]{2,60})\s*[:\-]\s*([^\n]+?)\s*$"
)
_VERDICT_INLINE_RE = re.compile(
    r"VERDICT:\s*(STRONG\s*BUY|BUY|HOLD|SELL|STRONG\s*SELL)\s*\|?\s*Confidence:\s*(High|Medium|Low)",
    re.IGNORECASE,
)
_VERDICT_STANDALONE_RE = re.compile(r"^(Strong\s*BUY|Strong\s*SELL|BUY|HOLD|SELL)\s*$", re.MULTILINE | re.IGNORECASE)
_CONFIDENCE_RE = re.compile(r"Confidence:\s*(High|Medium|Low)", re.IGNORECASE)
_REDUNDANT_LINE_RE = re.compile(
    r"(past performance|do your own research|not investment advice|consult (an )?advisor|"
    r"indicative of future results|consider your risk tolerance|i can now give|let me give you|here is my advice)",
    re.IGNORECASE,
)
_EVIDENCE_TOKENS_RE = re.compile(
    r"(\d|%|x\b|https?://|\[source:|market cap|pe\b|roe\b|roa\b|beta\b|drawdown|volatility)",
    re.IGNORECASE,
)

_GROUP_BY_LABEL = {
    "financial_snapshot": ("p/e", "forward p/e", "p/b", "p/s", "roe", "roa", "gross margin", "free cash flow", "operating cash flow"),
    "performance_risk": ("total return", "annualized return", "volatility", "drawdown", "beta"),
    "sentiment": ("analyst consensus", "sentiment signal", "top holders"),
    "company_basics": ("company name", "ticker", "sector", "segment", "price", "market cap", "peers"),
    "market_pulse": ("mini screener", "ticker tape"),
}

_SECTION_ORDER = [
    "COMPANY BASICS",
    "FINANCIAL SNAPSHOT",
    "VALUATION SUMMARY",
    "PERFORMANCE & RISK",
    "SENTIMENT & ANALYST SUMMARY",
    "RELATED NEWS",
    "MARKET PULSE",
    "RECOMMENDATION",
]

_SECTION_LABELS = {
    "COMPANY BASICS": "Company Profile",
    "FINANCIAL SNAPSHOT": "Financial Summary",
    "VALUATION SUMMARY": "Valuation",
    "PERFORMANCE & RISK": "Performance & Risk",
    "SENTIMENT & ANALYST SUMMARY": "Sentiment & News",
    "RELATED NEWS": "Sentiment & News - Related News",
    "MARKET PULSE": "Sentiment & News - Market Pulse",
    "RECOMMENDATION": "Final Recommendation",
}


def _is_analysis_entry(log_entry: LogEntry) -> bool:
    return log_entry.substage is not None and log_entry.substage.value in _ANALYSIS_SUBSTAGES


# ── Sentiment badge for card header ──────────────────────────

def _extract_card_badge(substage_val: str, text: str) -> str:
    patterns = _CARD_SENTIMENT_PATTERNS.get(substage_val, [])
    for pattern, label, css_class in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return f'<span class="card-badge {css_class}">{label}</span>'
    return ""


# ── Signal highlighting ──────────────────────────────────────

def _format_signal_tag(match: re.Match) -> str:
    tag = match.group(1).upper()
    if tag in ("POSITIVE", "BULLISH"):
        return '<span class="pill pill-positive">POSITIVE</span>'
    if tag in ("NEGATIVE", "BEARISH"):
        return '<span class="pill pill-negative">NEGATIVE</span>'
    return '<span class="pill pill-neutral">NEUTRAL</span>'


def _highlight_signals(text: str) -> str:
    text = _SIGNAL_TAG_RE.sub(_format_signal_tag, text)
    text = _POSITIVE_WORDS.sub(r'<span class="signal-positive">\g<0></span>', text)
    text = _NEGATIVE_WORDS.sub(r'<span class="signal-negative">\g<0></span>', text)
    text = _NEUTRAL_WORDS.sub(r'<span class="signal-neutral">\g<0></span>', text)
    return text


def _clean_line(line: str) -> str:
    line = line.strip().strip('"').strip("'")
    line = re.sub(r"^[\-\*\d.)\s]+", "", line)
    line = line.replace("**", "")
    return re.sub(r"\s+", " ", line).strip()


def _clean_note_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"^[\[\]\s]+", "", cleaned)
    cleaned = re.sub(r"[\[\]\s]+$", "", cleaned)
    cleaned = re.sub(r"\s+\.\s*$", ".", cleaned)
    return cleaned


def _is_low_value_line(line: str, symbol: str) -> bool:
    """Rule-based quality gate for dropping filler lines."""
    lower = line.lower()
    if _REDUNDANT_LINE_RE.search(lower):
        return True
    if len(line) < 3:
        return True
    if re.fullmatch(r"[\[\](){}.,;:\-]+", line):
        return True
    has_evidence = bool(_EVIDENCE_TOKENS_RE.search(line))
    mentions_symbol = bool(symbol) and symbol.lower() in lower
    looks_generic = lower.startswith(("remember ", "ultimately ", "in general ", "overall, it is important"))
    return looks_generic and not (has_evidence or mentions_symbol)


def _metric_row(label: str, value: str, note: str = "") -> str:
    lower = f"{label} {value} {note}".lower()
    sentiment = "metric-neutral"
    if "sentiment signal" in label.lower():
        if "positive" in lower:
            sentiment = "metric-positive"
        elif "negative" in lower:
            sentiment = "metric-negative"
        else:
            sentiment = "metric-neutral"
    elif any(w in lower for w in ("risk", "overvalued", "weak", "declining", "high debt", "drawdown")):
        sentiment = "metric-negative"
    elif any(w in lower for w in ("healthy", "strong", "good", "improved", "undervalued", "growth")):
        sentiment = "metric-positive"

    safe_note = _clean_note_text(note)
    tooltip = ""
    if safe_note:
        tooltip = (
            f'<span class="metric-info-wrapper" tabindex="0" role="button" '
            f'aria-label="More detail for {html.escape(label, quote=True)}" '
            f'data-tooltip="{html.escape(safe_note, quote=True)}">'
            '<span class="metric-info">i</span>'
            "</span>"
        )

    row = (
        '<div class="metric-tile">'
        f'<span class="metric-label-wrap"><span class="metric-label">{html.escape(label)}</span>{tooltip}</span>'
        f'<span class="metric-value {sentiment}">{html.escape(value)}</span>'
        "</div>"
    )
    return row


def _parse_metric_line(line: str) -> tuple[str, str, str] | None:
    metric = _METRIC_LINE_RE.match(line)
    if not metric:
        return None

    label = metric.group(1).strip()
    raw_value = metric.group(2).strip()

    source = None
    source_match = re.search(r"\[source:\s*([^\]]+)\]", raw_value, re.IGNORECASE)
    if source_match:
        source = source_match.group(1).strip()
        raw_value = re.sub(r"\[source:\s*[^\]]+\]", "", raw_value, flags=re.IGNORECASE).strip()

    value, note = raw_value, ""
    for sep in (" | ", " — ", " - "):
        if sep in raw_value:
            left, right = raw_value.split(sep, 1)
            value = left.strip()
            note = right.strip()
            break

    value = _clean_note_text(value)
    note = _clean_note_text(note)
    return label, value, note


def _render_news_from_lines(lines: list[str]) -> str:
    cards: list[str] = []
    status_line = ""
    for line in lines:
        lower = line.lower()
        if lower.startswith("news status:"):
            status_line = line.split(":", 1)[1].strip()
            continue
        if lower.startswith("news:"):
            payload = line.split(":", 1)[1].strip()
            parts = [p.strip() for p in payload.split("|")]
            title = parts[0] if parts else "News"
            publisher = parts[1] if len(parts) > 1 else "source"
            url = parts[2] if len(parts) > 2 else ""
            if url.startswith("http"):
                cards.append(
                    f'<a class="news-item" href="{html.escape(url)}" target="_blank" rel="noopener noreferrer">'
                    f'<span class="news-title" title="{html.escape(title)}">{html.escape(title)}</span>'
                    f'<span class="news-meta">{html.escape(publisher)}</span>'
                    "</a>"
                )
            continue
        if line.startswith("http"):
            parsed = urlparse(line)
            cards.append(
                f'<a class="news-item" href="{html.escape(line)}" target="_blank" rel="noopener noreferrer">'
                f'<span class="news-title">{html.escape(parsed.netloc.replace("www.", ""))}</span>'
                "</a>"
            )

    if not cards and not status_line:
        return '<div class="section-divider">Sentiment &amp; News - Related News</div><div class="summary-item">No recent news available.</div>'

    status_html = f'<div class="news-status">{html.escape(status_line)}</div>' if status_line else ""
    return '<div class="section-divider">Sentiment &amp; News - Related News</div>' + status_html + '<div class="news-list">' + "".join(cards) + "</div>"


def _render_market_pulse(lines: list[str]) -> str:
    screener = ""
    ticker_tape = ""
    for line in lines:
        if line.lower().startswith("mini screener:"):
            screener = line.split(":", 1)[1].strip()
        elif line.lower().startswith("ticker tape:"):
            ticker_tape = line.split(":", 1)[1].strip()

    chips_html = ""
    if screener:
        parts = [p.strip() for p in screener.split("|") if p.strip()]
        normalized_parts = []
        for p in parts[:4]:
            if "=" in p:
                left, right = p.split("=", 1)
                normalized_parts.append(f"{left.strip()}: {right.strip()}")
            else:
                normalized_parts.append(p)
        chips_html = '<div class="pulse-chips">' + "".join(f'<span class="pulse-chip">{html.escape(p)}</span>' for p in normalized_parts) + "</div>"

    ticker_html = ""
    if ticker_tape:
        items = [x.strip() for x in ticker_tape.split("|") if x.strip()]
        ticker_html = '<div class="ticker-tape">' + "".join(f'<span class="ticker-item">{html.escape(i)}</span>' for i in items[:4]) + "</div>"

    if not chips_html and not ticker_html:
        return ""
    context = (
        '<div class="section-insight">'
        'Market Pulse is a quick context snapshot from screener and ticker tape data. '
        'Use these tags as directional signals, not standalone recommendations.'
        "</div>"
    )
    return '<div class="section-divider">Sentiment &amp; News - Market Pulse</div>' + context + chips_html + ticker_html


def _group_for_label(label: str) -> str:
    lower = label.lower()
    for group, keys in _GROUP_BY_LABEL.items():
        if any(k in lower for k in keys):
            return group
    return "other"


def _read_more_line(line: str) -> str:
    cleaned = _clean_note_text(line)
    if not cleaned:
        return ""
    return f'<div class="summary-item">{_highlight_signals(html.escape(cleaned))}</div>'


def _render_misc_lines(lines: list[str]) -> str:
    if not lines:
        return ""

    preview = lines[:2]
    remaining = lines[2:]
    content = "".join(_read_more_line(line) for line in preview)
    if not remaining:
        return content

    detail_count = len(remaining)
    details_html = "".join(_read_more_line(line) for line in remaining)
    if not details_html:
        return content
    content += (
        '<details class="summary-more">'
        f'<summary>Detailed evidence<span class="read-more-chip">+{detail_count} more</span></summary>'
        f'<div class="summary-more-content">{details_html}</div>'
        "</details>"
    )
    return content


def _render_company_basics(raw_text: str, symbol: str) -> str:
    ordered_keys = ("company name", "ticker", "symbol", "sector", "segment", "price", "market cap")
    value_map: dict[str, str] = {}
    for key in ordered_keys:
        match = re.search(rf"{re.escape(key)}\s*[:\-]\s*([^\n]+)", raw_text, re.IGNORECASE)
        if match:
            value_map[key] = match.group(1).strip()

    if "ticker" not in value_map:
        value_map["ticker"] = symbol

    rows = []
    label_map = {
        "company name": "Company Name",
        "ticker": "Ticker",
        "symbol": "Ticker",
        "sector": "Sector",
        "segment": "Segment",
        "price": "Price (USD)",
        "market cap": "Market Cap",
    }
    added = set()
    for key in ordered_keys:
        if key in value_map:
            final_key = "ticker" if key == "symbol" else key
            if final_key in added:
                continue
            added.add(final_key)
            rows.append(
                f'<div class="basic-row"><span class="basic-key">{label_map[final_key]}</span>'
                f'<span class="basic-value">{html.escape(value_map[key])}</span></div>'
            )

    peers_match = re.search(r"peers?\s*[:\-]\s*([^\n]+)", raw_text, re.IGNORECASE)
    peer_html = ""
    if peers_match:
        peers = [p.strip() for p in peers_match.group(1).split(",") if p.strip()][:5]
        peer_html = '<div class="basic-peers">' + "".join(f'<span class="peer-chip">{html.escape(p)}</span>' for p in peers) + "</div>"

    return '<div class="section-divider">Company Profile</div><div class="company-basics">' + "".join(rows) + peer_html + "</div>"


# ── Verdict extraction (flexible) ────────────────────────────

def _extract_verdict(text: str) -> tuple[str | None, str]:
    m = _VERDICT_INLINE_RE.search(text)
    if m:
        verdict = m.group(1).strip().upper()
        confidence = m.group(2).strip().capitalize()
        cleaned = text[:m.start()] + text[m.end():]
        return _build_gauge(verdict, confidence), cleaned.strip()

    verdicts_found = _VERDICT_STANDALONE_RE.findall(text)
    confidence_match = _CONFIDENCE_RE.search(text)

    if verdicts_found:
        verdict = verdicts_found[-1].strip().upper()
        confidence = confidence_match.group(1).capitalize() if confidence_match else "Medium"

        cleaned = text
        for v in verdicts_found:
            cleaned = cleaned.replace(v.strip(), '', 1)
        if confidence_match:
            cleaned = cleaned[:confidence_match.start()] + cleaned[confidence_match.end():]

        standalone_labels = re.compile(r"^\s*(Strong BUY|Strong SELL|BUY|HOLD|SELL)\s*$", re.MULTILINE | re.IGNORECASE)
        cleaned = standalone_labels.sub('', cleaned)
        return _build_gauge(verdict, confidence), cleaned.strip()

    return None, text


# ── Semicircle gauge ─────────────────────────────────────────

_GAUGE_LEVELS = ["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]


def _build_gauge(verdict: str, confidence: str) -> str:
    verdict_upper = re.sub(r'\s+', ' ', verdict.strip().upper())
    active_idx = 2
    for i, level in enumerate(_GAUGE_LEVELS):
        if level == verdict_upper:
            active_idx = i
            break

    labels = []
    for i, level in enumerate(_GAUGE_LEVELS):
        active_cls = " meter-step-active" if i == active_idx else ""
        display = level.replace("STRONG ", "Strong ")
        labels.append(f'<span class="meter-step{active_cls}">{display}</span>')

    verdict_display = verdict_upper.replace("STRONG ", "Strong ")
    sentiment_cls = "gauge-verdict-buy" if active_idx <= 1 else ("gauge-verdict-sell" if active_idx >= 3 else "gauge-verdict-hold")

    return (
        f'<div class="gauge-container" id="riskometer-gauge">'
        f'<div class="gauge-title">Recommendation</div>'
        f'<div class="meter-track">{"".join(labels)}</div>'
        f'<div class="gauge-verdict {sentiment_cls}">{verdict_display}</div>'
        f'<div class="gauge-confidence">Confidence: {confidence}</div>'
        f'</div>'
    )


def _format_analysis_body(raw_text: str, symbol: str) -> str:
    lines = [l for l in (_clean_line(x) for x in raw_text.splitlines()) if l]
    section_map: dict[str, list[str]] = {}
    current_section = "OTHER"

    for line in lines:
        if _is_low_value_line(line, symbol):
            continue
        if line.lower().startswith("insight:"):
            section_map.setdefault(current_section, []).append(line)
            continue
        if _SECTION_HEADER_RE.match(line) and len(line) <= 36:
            current_section = line.strip(": ").upper()
            section_map.setdefault(current_section, [])
            continue
        if line.startswith("{") or line.endswith("}") or line.lower().startswith("action"):
            continue
        section_map.setdefault(current_section, []).append(line)

    metric_seen: set[str] = set()
    rendered_blocks: list[str] = []

    # Render known sections in fixed order first.
    for section_name in _SECTION_ORDER:
        payload = section_map.get(section_name, [])
        if not payload:
            continue

        if section_name == "RELATED NEWS":
            rendered_blocks.append(_render_news_from_lines(payload))
            continue
        if section_name == "MARKET PULSE":
            pulse = _render_market_pulse(payload)
            if pulse:
                rendered_blocks.append(pulse)
            continue

        metrics: list[str] = []
        insight_line = ""
        misc: list[str] = []
        for line in payload:
            if line.lower().startswith("insight:") and not insight_line:
                insight_line = line.split(":", 1)[1].strip()
                continue
            parsed = _parse_metric_line(line)
            if parsed:
                label, value, note = parsed
                normalized = label.lower().strip()
                if normalized in metric_seen:
                    continue
                metric_seen.add(normalized)
                metrics.append(_metric_row(label, value, note))
            else:
                misc.append(line)

        if not metrics and not misc and not insight_line:
            continue

        display_name = _SECTION_LABELS.get(section_name, section_name.title())
        block = f'<div class="section-divider">{display_name}</div>'
        if metrics:
            block += '<div class="metric-grid">' + "".join(metrics) + "</div>"
        if misc:
            block += _render_misc_lines(misc)
        if insight_line:
            block += f'<div class="section-insight">{_highlight_signals(html.escape(insight_line))}</div>'
        rendered_blocks.append(block)

    # Render any extra sections not in the fixed order.
    for section_name, payload in section_map.items():
        if section_name in _SECTION_ORDER:
            continue
        metrics: list[str] = []
        misc: list[str] = []
        for line in payload:
            parsed = _parse_metric_line(line)
            if parsed:
                label, value, note = parsed
                normalized = label.lower().strip()
                if normalized in metric_seen:
                    continue
                metric_seen.add(normalized)
                metrics.append(_metric_row(label, value, note))
            else:
                misc.append(line)
        if metrics or misc:
            display_name = _SECTION_LABELS.get(section_name, section_name.title())
            block = f'<div class="section-divider">{html.escape(display_name)}</div>'
            if metrics:
                block += '<div class="metric-grid">' + "".join(metrics) + "</div>"
            if misc:
                block += _render_misc_lines(misc)
            rendered_blocks.append(block)

    if not rendered_blocks:
        return '<div class="summary-item">No detailed data available for this section.</div>'
    return "".join(rendered_blocks)


# ── Analysis card renderer ───────────────────────────────────

def _format_analysis_block(log_entry: LogEntry) -> str:
    substage_val = log_entry.substage.value
    title = _ANALYSIS_TITLES.get(substage_val, html.escape(log_entry.substage.display_name))
    icon = _ANALYSIS_ICONS.get(substage_val, "&#x2728;")
    raw = log_entry.message or ""
    symbol = html.escape((log_entry.symbol or "").upper())
    symbol_chip = f'<span class="symbol-chip">{symbol}</span>' if symbol else ""

    badge = _extract_card_badge(substage_val, raw)
    gauge_html, raw = _extract_verdict(raw)
    body_html = _format_analysis_body(raw, symbol)
    if substage_val == "generating_investment_report" and "COMPANY BASICS" not in (raw or "").upper():
        body_html = _render_company_basics(raw, symbol or "N/A") + body_html

    parts = [
        f'<div class="log-entry log-analysis">',
        f'<div class="log-analysis-header"><span class="analysis-title">{icon} {title}</span>{badge}{symbol_chip}</div>',
        f'<div class="log-analysis-body">{body_html}</div>',
    ]

    if gauge_html:
        parts.append(gauge_html)

    parts.append('</div>')
    return ''.join(parts)


# ── Public API ───────────────────────────────────────────────

def format_log_entry(log_entry: LogEntry) -> str:
    """Format a log entry for HTML display — analysis entries get rich rendering."""
    if log_entry.substage is None:
        display_text = log_entry.message or log_entry.stage.display_name
        if log_entry.status_type == StatusType.FAILED:
            return f'<div class="log-entry log-stage log-failed">{html.escape(display_text)}</div>'
        if log_entry.status_type == StatusType.IN_PROGRESS:
            return f'<div class="log-entry log-stage log-stage-progress">{html.escape(display_text)}</div>'
        return f'<div class="log-entry log-stage">{html.escape(display_text)}</div>'

    if _is_analysis_entry(log_entry):
        if log_entry.status_type == StatusType.IN_PROGRESS:
            title = _ANALYSIS_TITLES.get(log_entry.substage.value, html.escape(log_entry.substage.display_name))
            icon = _ANALYSIS_ICONS.get(log_entry.substage.value, "&#x2728;")
            return f'<div class="log-entry log-substage log-analyzing log-progress-item">  &rarr; {icon} {title}...</div>'
        if log_entry.status_type == StatusType.SUCCESS:
            return _format_analysis_block(log_entry)
        if log_entry.status_type == StatusType.FAILED:
            title = _ANALYSIS_TITLES.get(log_entry.substage.value, html.escape(log_entry.substage.display_name))
            msg = html.escape(log_entry.message or "failed")
            return f'<div class="log-entry log-substage log-failed">  &rarr; {title} &mdash; {msg}</div>'

    if log_entry.status_type == StatusType.IN_PROGRESS:
        return f'<div class="log-entry log-substage log-progress-item">  &rarr; {html.escape(log_entry.substage.display_name)}...</div>'

    substage_name = html.escape(log_entry.substage.display_name)
    status_message = html.escape(log_entry.message or log_entry.status_type.display_message)

    if log_entry.status_type == StatusType.SUCCESS:
        status_class = "log-success"
    elif log_entry.status_type == StatusType.FAILED:
        status_class = "log-failed"
    else:
        status_class = "log-complete"

    return f'<div class="log-entry log-substage {status_class}">  &rarr; {substage_name} ({status_message})</div>'
