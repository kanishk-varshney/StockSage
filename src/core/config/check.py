# SPDX-License-Identifier: MIT
"""Validate LLM / environment configuration before running the app.

Usage (from repository root):

    python -m src.core.config.check

Exit code 0 if checks pass, 1 otherwise.
"""

from __future__ import annotations

import os
import sys

# Load .env before reading config
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env")

# Import after load_dotenv so os.environ is populated
from src.core.config.config import (  # noqa: E402
    LLM_FALLBACK_MODEL,
    LLM_MODEL,
    OLLAMA_BASE_URL,
)
from src.core.config.llm import _is_ollama_model, _ollama_reachable  # noqa: E402

# LiteLLM convention: provider prefix -> env var(s) that must be non-empty for API calls.
_PROVIDER_ENV_KEYS: dict[str, tuple[str, ...]] = {
    "openai": ("OPENAI_API_KEY",),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "gemini": ("GEMINI_API_KEY",),
    "groq": ("GROQ_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "azure": ("AZURE_API_KEY", "AZURE_OPENAI_API_KEY"),
    "mistral": ("MISTRAL_API_KEY",),
    "cohere": ("COHERE_API_KEY",),
}


def _provider_from_model(model: str) -> str:
    model = (model or "").strip()
    if "/" not in model:
        return ""
    return model.split("/", 1)[0].strip().lower()


def _check_api_keys_for_model(label: str, model: str) -> list[str]:
    errors: list[str] = []
    model = (model or "").strip()
    if not model:
        errors.append(
            f"{label} is empty; set LLM_MODEL (e.g. ollama/llama3.1:8b or openai/gpt-4o-mini)."
        )
        return errors
    if "/" not in model or not model.split("/", 1)[1].strip():
        errors.append(f"{label} must look like 'provider/model-name' (got {model!r}).")
        return errors

    provider = _provider_from_model(model)
    if _is_ollama_model(model):
        if not _ollama_reachable(OLLAMA_BASE_URL, model):
            errors.append(
                f"{label} uses Ollama but the server at {OLLAMA_BASE_URL!r} does not list "
                f"model {model.split('/', 1)[1]!r}. Start Ollama and pull the model, or change LLM_MODEL."
            )
        return errors

    keys = _PROVIDER_ENV_KEYS.get(provider)
    if keys is None:
        print(f"Note: unknown provider {provider!r} for {label}; skipping API key check.")
        return errors

    if not any(os.getenv(k) for k in keys):
        errors.append(f"{label} ({model}) expects one of these env vars set: {', '.join(keys)}.")
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(_check_api_keys_for_model("LLM_MODEL", LLM_MODEL))
    if LLM_FALLBACK_MODEL and LLM_FALLBACK_MODEL.strip():
        errors.extend(_check_api_keys_for_model("LLM_FALLBACK_MODEL", LLM_FALLBACK_MODEL))

    if errors:
        print("Configuration issues:\n", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            "\nFix your `.env` (see `.env.example` and docs/model-providers.md).", file=sys.stderr
        )
        return 1

    print("Configuration OK.")
    print(f"  LLM_MODEL={LLM_MODEL}")
    if LLM_FALLBACK_MODEL and LLM_FALLBACK_MODEL.strip():
        print(f"  LLM_FALLBACK_MODEL={LLM_FALLBACK_MODEL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
