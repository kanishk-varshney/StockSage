# Local setup

StockSage runs on **your machine**. You supply LLM access via **Ollama** (no API key) or a **cloud provider** (API key).

## Requirements

- Python **3.13+** (see `pyproject.toml`)
- Git

Optional:

- [uv](https://docs.astral.sh/uv/) (recommended)
- [Ollama](https://ollama.com/) for local models

## Install

```bash
git clone https://github.com/<your-user-or-org>/StockSage.git
cd StockSage
uv sync
```

Without uv:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Environment

```bash
cp .env.example .env
```

Edit `.env`: set `LLM_MODEL` and keys per [model-providers.md](model-providers.md).

Validate:

```bash
make check
```

Or: `python -m src.core.config.check`

## Run

```bash
make run
```

Or: `uv run uvicorn src.app.main:app --reload`

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Platform notes

### macOS / Linux

Use `source .venv/bin/activate` as above.

### Windows

Use PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn src.app.main:app --reload
```

### Ollama

1. Install and start Ollama.
2. Pull a model: `ollama pull qwen2.5:14b-instruct` (or another tag you set in `LLM_MODEL`).
3. Set `LLM_MODEL=ollama/qwen2.5:14b-instruct` in `.env`.

## Jupyter (optional)

Not required for the web UI:

```bash
uv sync --extra notebook
```

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| `ModuleNotFoundError` | Run from repo root; ensure venv activated and `pip install -e .` or `uv sync`. |
| Ollama errors | Run `make check`; confirm `ollama serve` and model pulled. |
| API errors | Verify provider env vars; see [model-providers.md](model-providers.md). |
| Heavy RAM use | Use a smaller Ollama model or cloud API; close other apps. |

### UI error decision tree

If you see frequent UI stream errors, run this sequence:

1. Validate configuration:
   ```bash
   make check
   ```
2. Confirm active model settings:
   ```bash
   .venv/bin/python -c "from src.core.config.config import LLM_MODEL, LLM_FALLBACK_MODEL, OLLAMA_BASE_URL; print(LLM_MODEL, LLM_FALLBACK_MODEL, OLLAMA_BASE_URL)"
   ```
3. If using Ollama, verify daemon + model tag:
   ```bash
   curl -sS --max-time 5 http://localhost:11434/api/tags
   ```
4. If UI shows `Reference: <id>`, check server logs for that reference ID; browser errors are sanitized by design.
5. If Ollama is unstable, switch to a known-good cloud model in `.env` temporarily to isolate transport vs model/runtime problems.
