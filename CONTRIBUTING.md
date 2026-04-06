# Contributing to StockSage

Thanks for helping improve StockSage. This project is **local-first**: contributors run the app on their own machine with their own API keys or Ollama.

## Before you start

- Read [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
- For security-sensitive reports, see [`SECURITY.md`](SECURITY.md).

## Development setup

1. **Clone** the repository.
2. **Install Python** `>=3.13` (see [`pyproject.toml`](pyproject.toml)).
   - CI intentionally runs only Python 3.13 to keep one deterministic runtime and avoid provider/tooling drift across versions.
3. **Install dependencies** (pick one):

   ```bash
   uv sync          # recommended — installs exact versions from uv.lock
   ```

   Or (minimum-version install, no lock file):

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

   Use `uv sync` when you want a reproducible environment matching CI. Use `pip install -e ".[dev]"` if you don't have `uv` or want to test against the minimum declared versions.

4. **Configure environment**:

   ```bash
   cp .env.example .env
   ```

   Set `LLM_MODEL` and any required API keys (see [`docs/model-providers.md`](docs/model-providers.md)).

5. **Validate config** (optional but recommended):

   ```bash
   python -m src.core.config.check
   ```

6. **Run the app**:

   ```bash
   make run
   ```

   Or: `uv run uvicorn src.app.main:app --reload` / `uvicorn src.app.main:app --reload` from an activated venv.

## Lint

```bash
make lint
```

Or: `python -m ruff check .`

## AI-assisted contributions

This project was built with AI coding assistance (Claude Code). AI-assisted contributions are welcome — use whatever tools help you. The only requirement is that **you understand and can explain what you're submitting**. Don't paste-and-run without reading: broken AI output that passes review is worse than no contribution.

## Tests

```bash
make test
```

Or: `python -m pytest` / `uv run pytest`

Keep new behavior covered when it is easy to test; UI-heavy changes may rely on manual checks—note that in your PR.

## Pull requests

- **Scope:** One logical change per PR when possible.
- **Describe:** What changed, why, and how you tested it.
- **UI changes:** Screenshots or short screen recording help.
- **Docs:** Update README or `docs/` if behavior or setup changes.

## Code style

- Match existing patterns in the touched files.
- Avoid drive-by refactors unrelated to the PR.
- Do not commit secrets or machine-specific paths.

## Questions

Open an issue on this repository (use the question template if available) or Discussions if maintainers enable it.
