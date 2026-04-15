# Model providers

StockSage uses [LiteLLM](https://docs.litellm.ai/docs/providers) via `LLM_MODEL` in `provider/model-name` form. Keys are standard LiteLLM env vars.

Run **`python -m src.core.config.check`** after editing `.env` to catch missing keys or unreachable Ollama.

## Ollama (local, no API key)

1. Install [Ollama](https://ollama.com/) and start it.
2. Pull a model, e.g. `ollama pull qwen2.5:14b-instruct`.
3. In `.env`:

```env
LLM_MODEL=ollama/qwen2.5:14b-instruct
OLLAMA_BASE_URL=http://localhost:11434
```

Optional fallback when Ollama is down (requires that provider’s key):

```env
LLM_FALLBACK_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=sk-...
```

## OpenAI

```env
LLM_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=sk-...
```

## DeepSeek

```env
LLM_MODEL=deepseek/deepseek-chat
DEEPSEEK_API_KEY=...
```

## Google Gemini

```env
LLM_MODEL=gemini/gemini-2.5-flash
GEMINI_API_KEY=...
```

## Groq

```env
LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=...
```

## Anthropic

```env
LLM_MODEL=anthropic/claude-3-5-haiku-20241022
ANTHROPIC_API_KEY=...
```

## Serper (news search tool)

Optional but improves live news context:

```env
SERPER_API_KEY=...
```

## Adding a new provider

1. Confirm LiteLLM supports it: [providers](https://docs.litellm.ai/docs/providers).
2. Set `LLM_MODEL=provider/model-id`.
3. Set the API key env var LiteLLM expects for that provider.
4. If you want `check` to validate keys, add a mapping in `src/core/config/check.py` (`_PROVIDER_ENV_KEYS`).
