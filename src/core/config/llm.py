"""LLM factory — builds a CrewAI LLM instance using LiteLLM under the hood.

CrewAI's LLM class delegates to LiteLLM for provider routing, auth,
retries, and API normalization. This module reads the model config and
returns a ready-to-use LLM instance.

Switching providers requires only changing LLM_MODEL in config.py.
"""

import logging

import litellm
from crewai import LLM

from src.core.config.config import (
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


def get_llm() -> LLM:
    """Build a CrewAI LLM from config. LiteLLM handles provider routing."""
    kwargs: dict = {
        "model": LLM_MODEL,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "timeout": LLM_TIMEOUT,
    }

    if _is_ollama_model(LLM_MODEL):
        kwargs["base_url"] = OLLAMA_BASE_URL
        kwargs["num_ctx"] = OLLAMA_NUM_CTX

    return LLM(**kwargs)
