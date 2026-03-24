"""Configuration settings — single source of truth for all app config."""

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env")

# ── Data settings ──────────────────────────────────────────
DEFAULT_PERIOD = "1y"
DEFAULT_OUTPUT_DIR = ".market_data"
OUTPUT_DIR_PATH = (_PROJECT_ROOT / DEFAULT_OUTPUT_DIR).resolve()

# ── LLM Configuration ─────────────────────────────────────
# Uses LiteLLM model format: "provider/model-name"
# LiteLLM handles provider routing, auth, and API differences automatically.
# Docs: https://docs.litellm.ai/docs/providers
#
# To switch models, set LLM_MODEL env var — nothing else needed.
# API keys are read from environment variables automatically by LiteLLM.

LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-chat")
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "gemini/gemini-2.5-flash")

# ── Model options (set LLM_MODEL env var to one of these) ──
#
# Recommended for deployed use (cheap, no throttling):
#   deepseek/deepseek-chat          ~$0.01-0.05 per analysis, needs DEEPSEEK_API_KEY
#
# Free tier options:
#   gemini/gemini-2.5-flash         Free (10 RPM, 250 RPD), needs GEMINI_API_KEY
#   groq/llama-3.3-70b-versatile    Free (tight TPM limits), needs GROQ_API_KEY
#
# Local (dev only, no API key, needs Ollama running):
#   ollama/qwen2.5:14b-instruct     Best local quality for structured output
#   ollama/llama3.1:8b              Good general purpose
#   ollama/deepseek-r1:8b           Strong at math/finance
#
# Premium (higher cost):
#   openai/gpt-4o-mini              ~$0.15/$0.60 per M tokens, needs OPENAI_API_KEY
#   openai/gpt-4o                   Best OpenAI quality, expensive
#   anthropic/claude-sonnet-4-20250514   Needs ANTHROPIC_API_KEY
#   gemini/gemini-2.5-pro           Best Gemini quality

# ── LLM Parameters ────────────────────────────────────────
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "300"))

# ── Ollama-specific settings ──────────────────────────────
# Only relevant when using an ollama/ model (local dev).
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))

# ── Crew settings ─────────────────────────────────────────
CREW_VERBOSE = os.getenv("CREW_VERBOSE", "false").strip().lower() == "true"

# ── App runtime mode (UI iteration) ────────────────────────
APP_MODE = (os.getenv("STOCKSAGE_APP_MODE", "prod") or "prod").strip().lower()
if APP_MODE not in {"dev", "prod"}:
    APP_MODE = "prod"

DEV_STREAM_MODE = (os.getenv("STOCKSAGE_DEV_STREAM_MODE", "mock") or "mock").strip().lower()
if DEV_STREAM_MODE not in {"live", "mock"}:
    DEV_STREAM_MODE = "mock"
