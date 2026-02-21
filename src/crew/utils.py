"""Text sanitization utilities for cleaning raw CrewAI agent output."""

import json
import re

_TOOL_CALL_RE = re.compile(
    r'(?:Action|Action Input|Observation|Thought):.*?(?=\n[A-Z]|\n\n|\Z)',
    re.DOTALL,
)
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_DICT_LINE_RE = re.compile(r"^\s*\{.*\}\s*$", re.MULTILINE)
_BOILERPLATE_LINE_RE = re.compile(
    r"(past performance|do your own research|not investment advice|consult (an )?advisor|"
    r"indicative of future results|consider your risk tolerance)",
    re.IGNORECASE,
)
_EMPTY_LINES_RE = re.compile(r'\n{3,}')


def sanitize_output(text: str) -> str:
    """Strip JSON blobs, tool-call artifacts, and noise from agent output."""
    if not text:
        return text
    cleaned = _strip_json_blobs(text)
    cleaned = _CODE_FENCE_RE.sub("", cleaned)
    cleaned = _DICT_LINE_RE.sub("", cleaned)
    cleaned = _TOOL_CALL_RE.sub('', cleaned)
    cleaned = _remove_low_value_lines(cleaned)
    cleaned = _EMPTY_LINES_RE.sub('\n\n', cleaned)
    return cleaned.strip()


def should_apply_fallback_cleanup(text: str) -> bool:
    """Heuristic gate: cleanup if output looks noisy and low-evidence."""
    if not text:
        return True
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return True
    metricish = sum(bool(re.search(r"\d|%|x|[:\-]\s*[$]?\d", ln)) for ln in lines)
    noisy = sum(bool(_BOILERPLATE_LINE_RE.search(ln)) for ln in lines)
    return metricish == 0 or noisy >= 2


def fallback_cleanup(text: str) -> str:
    """Conservative fallback cleanup: keep only evidence-bearing lines."""
    if not text:
        return ""
    kept: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _BOILERPLATE_LINE_RE.search(line):
            continue
        has_evidence = bool(re.search(r"\d|%|x|https?://|\[source:", line, re.IGNORECASE))
        is_section = bool(re.match(r"^[A-Z][A-Z0-9 &'?/\-]{4,}:?$", line))
        if has_evidence or is_section:
            kept.append(raw)
    return "\n".join(kept).strip()


def _remove_low_value_lines(text: str) -> str:
    lines = text.splitlines()
    kept = [ln for ln in lines if not _BOILERPLATE_LINE_RE.search(ln)]
    return "\n".join(kept)


def _strip_json_blobs(text: str) -> str:
    """Remove any JSON object/array literals from the text using actual parsing."""
    result: list[str] = []
    i = 0
    while i < len(text):
        if text[i] in ('{', '['):
            end = _find_json_end(text, i)
            if end is not None:
                i = end
                continue
        result.append(text[i])
        i += 1
    return ''.join(result)


def _find_json_end(text: str, start: int) -> int | None:
    """Try to parse a JSON value starting at `start`. Return index past the end, or None."""
    depth = 0
    open_char = text[start]
    close_char = '}' if open_char == '{' else ']'
    for i in range(start, len(text)):
        if text[i] == open_char:
            depth += 1
        elif text[i] == close_char:
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    json.loads(candidate)
                    return i + 1
                except (json.JSONDecodeError, ValueError):
                    return None
    return None
