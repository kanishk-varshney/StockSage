"""LLM factory — builds a CrewAI LLM instance using LiteLLM under the hood.

CrewAI's LLM class delegates to LiteLLM for provider routing, auth,
retries, and API normalization. This module reads the model config and
returns a ready-to-use LLM instance.

Switching providers requires only changing LLM_MODEL in config.py.
"""

import logging
import json
from urllib.error import URLError
from urllib.request import Request, urlopen

import litellm
from crewai import LLM

from src.core.config.config import (
    LLM_FALLBACK_MODEL,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    OLLAMA_BASE_URL,
    OLLAMA_NUM_CTX,
)

litellm.suppress_debug_info = True
# LiteLLM's internal logging tries to import its proxy server module
# (apscheduler, email-validator, fastapi-sso, etc.) on every call.
# These are non-functional errors from a code path we don't use.
# Real LLM errors raise exceptions caught by the pipeline.
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("litellm").setLevel(logging.CRITICAL)


def _is_ollama_model(model: str) -> bool:
    return model.startswith("ollama/") or model.startswith("ollama_chat/")


def _normalized_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _extract_ollama_model_name(model: str) -> str:
    return model.split("/", 1)[1].strip() if "/" in model else ""


def _ollama_ready_for_model(base_url: str, model: str) -> bool:
    """Check Ollama endpoint health and whether requested model is available."""
    tags_url = f"{_normalized_base_url(base_url)}/api/tags"
    request = Request(tags_url, method="GET")
    requested_model_name = _extract_ollama_model_name(model)
    try:
        with urlopen(request, timeout=3) as response:
            if not (200 <= response.status < 300):
                return False
            payload = json.loads(response.read().decode("utf-8"))
            available_models = {
                item.get("name", "").strip()
                for item in payload.get("models", [])
                if isinstance(item, dict)
            }
            if not requested_model_name:
                return False
            return requested_model_name in available_models
    except (URLError, TimeoutError, ValueError):
        return False


def _has_model_name(model: str) -> bool:
    provider_and_name = model.split("/", 1)
    return len(provider_and_name) == 2 and bool(provider_and_name[1].strip())


def _resolve_model() -> str:
    """Choose primary model, with fallback if Ollama endpoint is unavailable."""
    if _is_ollama_model(LLM_MODEL) and not _ollama_ready_for_model(OLLAMA_BASE_URL, LLM_MODEL):
        if LLM_FALLBACK_MODEL:
            logging.getLogger(__name__).warning(
                "Ollama endpoint/model not ready (%s, model=%s). Falling back to %s.",
                OLLAMA_BASE_URL,
                LLM_MODEL,
                LLM_FALLBACK_MODEL,
            )
            return LLM_FALLBACK_MODEL
    return LLM_MODEL


def get_llm() -> LLM:
    """Build a CrewAI LLM from config. LiteLLM handles provider routing."""
    active_model = _resolve_model()
    kwargs: dict = {
        "model": active_model,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "timeout": LLM_TIMEOUT,
    }

    if _is_ollama_model(active_model):
        kwargs["base_url"] = OLLAMA_BASE_URL
        kwargs["num_ctx"] = OLLAMA_NUM_CTX

    if not _has_model_name(active_model):
        raise ValueError(
            f"Invalid LLM model format: '{active_model}'. Expected 'provider/model-name'."
        )

    return LLM(**kwargs)
