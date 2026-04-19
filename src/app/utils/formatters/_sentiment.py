# SPDX-License-Identifier: MIT
"""Market sentiment & news card renderer."""

import re

from src.app.utils.formatters._shared import (
    _badge_classes,
    _card,
    _esc,
    _parse_kv,
)


def _render_sentiment_card(raw: str, symbol: str) -> str:  # noqa: ARG001
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
        href = (
            f' href="{_esc(url)}" target="_blank" rel="noopener noreferrer"' if tag == "a" else ""
        )
        hover = " hover:bg-gray-50 transition-colors" if tag == "a" else ""
        return f"""<{tag}{href} class="flex items-center justify-between bg-white border border-gray-200 rounded-xl p-4{hover}">
          <div class="flex-1 min-w-0 mr-4">
            <p class="text-sm font-medium text-gray-800 leading-snug">{_esc(title)}</p>
            <p class="text-xs text-gray-400 mt-1 flex items-center gap-1">&#x1F517; {_esc(publisher)}</p>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <span class="text-gray-300">&mdash;</span>
            <span class="px-2.5 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-600 border border-gray-200">Neutral</span>
          </div>
        </{tag}>"""

    news_html = "\n".join(_news_row(t, p, u) for t, p, u in news_items[:4])

    body = f"""
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
        <p class="text-xl font-bold text-gray-900">{_esc(buy_count) if buy_count else _esc(analyst_consensus) if analyst_consensus else "N/A"}</p>
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
    """
    return _card(body, data_section="sentiment")
