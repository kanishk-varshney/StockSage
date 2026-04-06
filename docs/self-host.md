# Optional: self-hosting

StockSage is designed to run **locally**. If you want a **public URL**, you need a long-running server (analyses can take several minutes and use **Server-Sent Events**).

## Why not “serverless only”

Typical serverless platforms cap request duration (often well under a full Crew run). Prefer a **container** or **VM** with enough RAM (**≥1 GB**, often **2 GB** for CrewAI + pandas + numpy).

## Docker

The repo includes a `Dockerfile`. Build and run locally:

```bash
docker build -t stocksage .
docker run --env-file .env -p 8000:8000 stocksage
```

Set `PORT` if your host injects it (some platforms set `PORT` automatically).

## Platform hints

| Platform | Notes |
|----------|--------|
| Railway / Render / Fly.io | Persistent web service; set env vars in dashboard; scale memory if you see `Killed` (OOM). |
| Vercel | Not a fit for long SSE + multi-minute Python workloads. |

## Environment

Use the same variables as local runs: `LLM_MODEL`, provider keys, `SERPER_API_KEY`, etc. See [model-providers.md](model-providers.md).

Do **not** commit `.env` to git; configure secrets in the host’s secret store.
