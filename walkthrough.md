# StockSage Walkthrough

---

## 1) Deployment

### Hosting (where the FastAPI app runs)

StockSage needs a **persistent container** — not serverless — because analyses take 2-5 minutes with SSE streaming.

| Platform | Cost | Why |
|----------|------|-----|
| **Railway** | $5/mo | Best value. Persistent Docker containers, GitHub deploy, $5 compute included. |
| **Render** | $7/mo (Starter) | Good alternative. Free tier sleeps after 15 min. |
| **Fly.io** | ~$3-5/mo | Competitive, slightly more setup. |

**Do NOT use:** Vercel (serverless, 10-60s timeouts — won't work), Koyeb free tier (sleeps).

### Deploy to Railway

1. Push repo to GitHub.
2. Create a Railway project, connect GitHub repo.
3. Railway auto-detects the `Dockerfile`.
4. Set env vars in Railway dashboard (see section below).
5. Deploy. Railway assigns a public URL.

### LLM Model (which AI powers the agents)

Set via `LLM_MODEL` env var. The app uses LiteLLM — switching providers is just changing this string.

**Recommended for deployed use:**
```
LLM_MODEL=deepseek/deepseek-chat
LLM_FALLBACK_MODEL=gemini/gemini-2.5-flash
DEEPSEEK_API_KEY=your_key
GEMINI_API_KEY=your_key
```
- DeepSeek: ~$0.01-0.05 per full analysis. No throttling. Get key at https://platform.deepseek.com
- Gemini Flash: free tier fallback (10 RPM, 250 req/day). Get key at https://aistudio.google.com

**Free-only (zero cost):**
```
LLM_MODEL=gemini/gemini-2.5-flash
LLM_FALLBACK_MODEL=groq/llama-3.3-70b-versatile
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
```
- Gemini: 5-8 analyses/day max due to rate limits.
- Groq: very fast but tight token limits. Get key at https://console.groq.com

**Local dev (Ollama, no cost, no API key):**
```
LLM_MODEL=ollama/qwen2.5:14b-instruct
```
Requires Ollama running locally. Won't work on cloud deployments.

### Required env vars for deployment

```
LLM_MODEL=deepseek/deepseek-chat
LLM_FALLBACK_MODEL=gemini/gemini-2.5-flash
DEEPSEEK_API_KEY=...
GEMINI_API_KEY=...
SERPER_API_KEY=...
OTEL_SDK_DISABLED=true
STOCKSAGE_APP_MODE=prod
```

---

## 2) Runtime Modes

- `STOCKSAGE_APP_MODE=prod` (default): full pipeline via `/stream`.
- `STOCKSAGE_APP_MODE=dev`: fast iteration via `/stream/mock`.

If `STOCKSAGE_APP_MODE` is missing or invalid, defaults to `prod`.

```mermaid
flowchart LR
analyzeClick[AnalyzeButton] --> runtimeConfig[ServerInjectedRuntimeConfig]
runtimeConfig -->|prod| liveEndpoint[/stream]
runtimeConfig -->|dev+mock| mockEndpoint[/stream/mock]
liveEndpoint --> sseFrames[SSE data frames]
mockEndpoint --> sseFrames
sseFrames --> formatterHTML[format_log_entry HTML]
formatterHTML --> sharedFrontendRender[main.js render pipeline]
sharedFrontendRender --> uiCards[Cards Progress Verdict]
```

---

## 3) File Map

- UI shell: `src/app/templates/index.html`
- Styles: `src/app/static/css/style.css`
- SSE render / progress: `src/app/static/js/main.js`
- Card HTML generation: `src/app/utils/formatters.py`
- Endpoints: `src/app/main.py`
- Config: `src/core/config/config.py`
- LLM factory: `src/core/config/llm.py`

For look-and-feel changes, you usually only need: `index.html`, `style.css`, `formatters.py`.

---

## 4) Fast Dev Iteration

### Setup

In `.env`:
```
STOCKSAGE_APP_MODE=dev
STOCKSAGE_DEV_STREAM_MODE=mock
```

### How mock stream works

- Endpoint: `/stream/mock`
- First tries cached previous run output: `.market_data/<SYMBOL>/.ui_stream_cache.json`
- If cache exists: replays frames quickly.
- If no cache: falls back to deterministic mock payloads.

### Cache creation

Every successful real run through `/stream` stores HTML frames in `.market_data/<SYMBOL>/.ui_stream_cache.json`. That cache is reused in dev mock mode.

### 2-minute iteration loop

1. Set `.env` to dev mock mode.
2. Start app.
3. Run a symbol (e.g. `AAPL`) — renders in seconds.
4. Edit UI files.
5. Refresh and rerun.
6. When ready: set `STOCKSAGE_APP_MODE=prod`, restart, run real analysis.

---

## 5) Agentic Output Iteration

Use when refining agent prompts and structured outputs:

1. Run crew smoke test: `python tests/test_crew.py`
2. Check per-task output in console (agent name + output keys).
3. Fix prompt/schema mismatches before UI formatting changes.
4. Keep one symbol constant (e.g. `AAPL`) for comparable runs.
5. Set `CREW_VERBOSE=true` in `.env` to see full agent reasoning.

---

## 6) Production Checklist

- `STOCKSAGE_APP_MODE=prod` (or unset).
- `LLM_MODEL` and API key set for chosen provider.
- `SERPER_API_KEY` set for live news search.
- Browser requests go to `/stream` (not `/stream/mock`).
- Full download + analysis runs end-to-end.

---

## 7) Troubleshooting

**App sleeping on cloud:** You're on a free tier that scales to zero. Upgrade to paid (Railway $5/mo, Render $7/mo).

**Rate limit / timeout errors:** Switch from OpenAI to DeepSeek or Gemini. Set `LLM_MODEL=deepseek/deepseek-chat` and add `DEEPSEEK_API_KEY`.

**Ollama not found on cloud:** Ollama is local-only. Cloud deployments must use an API provider (DeepSeek, Gemini, Groq, OpenAI).

**Dev mode feels slow:** Check `.env` has `STOCKSAGE_APP_MODE=dev` and `STOCKSAGE_DEV_STREAM_MODE=mock`. Restart after changes.

**Mock mode not using previous run:** Check `.market_data/<SYMBOL>/.ui_stream_cache.json` exists. Run one real analysis in prod mode to seed it.

**Progress stuck:** Check SSE stream stays open. Confirm analysis step labels match `main.js`.
