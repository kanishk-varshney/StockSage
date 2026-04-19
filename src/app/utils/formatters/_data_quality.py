# SPDX-License-Identifier: MIT
"""Data quality / data sanity card renderer."""

from src.app.utils.formatters._shared import (
    _card,
    _esc,
    _parse_kv,
    _parse_kv_all,
)


def _render_data_quality_card(raw: str, symbol: str) -> str:  # noqa: ARG001
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
        stats_items.append(
            f'<span class="text-green-600 font-semibold">{validated} validated</span>'
        )
    if missing:
        stats_items.append(f'<span class="text-red-600 font-semibold">{missing} missing</span>')
    if critical:
        stats_items.append(f'<span class="text-red-600 font-semibold">{critical} critical</span>')
    if warnings:
        stats_items.append(
            f'<span class="text-yellow-600 font-semibold">{warnings} warnings</span>'
        )
    stats_html = ' <span class="text-gray-300">|</span> '.join(stats_items) if stats_items else ""

    meta_parts = []
    if company_type:
        meta_parts.append(_esc(company_type))
    if context:
        meta_parts.append(_esc(context))
    meta_html = (
        f'<p class="text-sm text-gray-500 mt-2">{" &middot; ".join(meta_parts)}</p>'
        if meta_parts
        else ""
    )

    return _card(
        f"""
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
    """,
        data_section="data-quality",
    )
