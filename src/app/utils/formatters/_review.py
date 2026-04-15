"""Quality review card renderer."""

from src.app.utils.formatters._shared import (
    _card,
    _clean_line,
    _esc,
    _parse_kv,
)


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

    body = f"""
    <div class="flex items-start justify-between mb-1">
      <div class="flex items-center gap-2">
        <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        <h3 class="text-lg font-bold text-gray-900">Quality Review</h3>
      </div>
      <span class="px-3 py-1 rounded bg-blue-100 text-blue-700 text-xs font-bold">{_esc(symbol)}</span>
    </div>
    <p class="text-sm text-gray-500 mt-1 mb-4">{_esc(structured_summary) if structured_summary else "Quality review completed."}</p>
    <div class="space-y-3">
      {items_html}
    </div>
    """
    return _card(body, data_section="review")
