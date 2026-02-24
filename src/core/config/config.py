"""Configuration settings — single source of truth for all app config."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load local .env (if present) so API keys like SERPER_API_KEY work
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
# To switch models, change LLM_MODEL below — nothing else needed.
# API keys are read from environment variables automatically by LiteLLM.

LLM_MODEL = os.getenv("LLM_MODEL", "ollama/llama3.1:8b")
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "openai/gpt-4o-mini")

# ── Alternative models (uncomment one to switch) ──────────
#
# Ollama (local, free, no API key needed):
# LLM_MODEL = "ollama/llama3.1:8b"            # Default — good general purpose
# LLM_MODEL = "ollama/qwen2.5:7b"             # Strong at structured analysis
# LLM_MODEL = "ollama/mistral:7b"             # Fast, decent reasoning
# LLM_MODEL = "ollama/deepseek-r1:8b"         # Strong at math/finance
# LLM_MODEL = "ollama/gemma2:9b"              # Google's open model
# LLM_MODEL = "ollama/llama3.1:70b"           # Best local quality (needs ~40GB RAM)
#
# OpenAI (needs OPENAI_API_KEY env var):
# LLM_MODEL = "openai/gpt-4o-mini"            # Cheap, fast, good enough
# LLM_MODEL = "openai/gpt-4o"                 # Best quality, higher cost
# LLM_MODEL = "openai/o1-mini"                # Reasoning-focused
#
# Anthropic (needs ANTHROPIC_API_KEY env var):
# LLM_MODEL = "anthropic/claude-sonnet-4-20250514"
# LLM_MODEL = "anthropic/claude-3-5-haiku-20241022"   # Fast, cheaper
#
# Google Gemini (needs GEMINI_API_KEY env var):
# LLM_MODEL = "gemini/gemini-2.0-flash"       # Fast, good quality
# LLM_MODEL = "gemini/gemini-2.5-pro"         # Best Gemini quality
#
# Groq (needs GROQ_API_KEY env var — very fast inference):
# LLM_MODEL = "groq/llama-3.1-70b-versatile"
# LLM_MODEL = "groq/mixtral-8x7b-32768"

# ── LLM Parameters ────────────────────────────────────────
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))  # Low for factual analysis
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))     # Max response length per agent
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "300"))            # Seconds — local/remote model may cold start

# ── Ollama-specific settings ──────────────────────────────
# Only relevant when using an ollama/ model.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# OLLAMA_BASE_URL = "http://192.168.1.100:11434"  # Remote Ollama server
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))    # Context window size

# ── API Keys ──────────────────────────────────────────────
# Set as environment variables (LiteLLM auto-detects them):
#   OPENAI_API_KEY=sk-...
#   ANTHROPIC_API_KEY=sk-ant-...
#   GEMINI_API_KEY=...
#   GROQ_API_KEY=gsk_...
#   SERPER_API_KEY=...        (for live news search via SerperDevTool)
#
# Ollama requires no API key — runs locally.

# ── Output Quality Guardrails ─────────────────────────────
# Optional fallback cleanup pass if output is too noisy/low-evidence.
# Keep disabled by default to avoid over-filtering valid content.
ENABLE_OUTPUT_CLEANUP_FALLBACK = False
