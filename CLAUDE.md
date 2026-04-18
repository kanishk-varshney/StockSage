## Environment

- Python **3.13+** (project baseline; see `pyproject.toml` / CI for the exact version used).
- Dependencies managed with `uv` (`uv.lock` is authoritative). Prefer `uv sync --extra dev` over pip.
- Runtime config comes from `.env` (see `.env.example`). `make check` must fail fast on invalid `.env` or LLM connectivity issues.

## Common commands

Use the Makefile; it wraps `uv run` so commands pick up the project venv.

| Task | Command |
|------|---------|
| Install deps + pre-commit | `make install` |
| Run prod server (SSE live) | `make run` (http://127.0.0.1:8000) |
| Run dev/mock-stream server | `make dev` (sets `STOCKSAGE_APP_MODE=dev`) |
| Test with coverage | `make test` |
| Single test | `uv run pytest <path>::<TestClass>::<test_case>` |
| Lint / format | `make lint` / `make format` |
| Typecheck | `make typecheck` (mypy on `src/`) |
| Security audit | `make security` (pip-audit + bandit) |
| Config/LLM check | `make check` |

Tests must mirror `src/` layout (`tests/app`, `tests/core`, `tests/crew`). `conftest.py` is at the tests root.

**Before any push**, run the same checks CI will:

```bash
uv run pre-commit run --all-files && make lint && make typecheck && make test && make security
```

Run `make install` once per clone so the pre-commit git hook blocks bad commits locally.

## Architecture (big picture)

 -  `core` and `crew` must remain side-effect free except at defined I/O boundaries.

### Data flow

- Task ordering is defined in tasks.yaml; any mapping (e.g., substage mapping) must stay in sync and be enforced via tests.
- Cache invalidation must be explicit (symbol refresh or TTL); stale cache must not be served silently.


### SSE contract

- Default events are **unnamed**, `data:` carries a single-line HTML fragment with `data-stage`/`data-substage` attributes.
- Named events: `stream_error` (sanitized message + reference id), `complete` (empty).
- Full contract: `docs/stream-api.md`.
- HTML must be safe-escaped, single-line, and SSE-compliant (no multiline payloads).

## Conventions specific to this repo

- **Non-critical download failures** (news, trends) are logged and the pipeline continues; only core price/financials failures abort the run. Don't turn soft failures into hard ones.
- Error messages sent to the browser are always sanitized; full details are logged server-side with a short reference id.
- Tests must cover failure paths and edge cases, not only happy paths.
- Do not commit, add, or push code unless explicitly instructed; commit messages must always be reviewed and approved before committing.

## Workflow & Safety
- **Before Coding**: Explore the file tree. For tasks affecting > 2 files, output a Plan first.
- **Secrets**: Never hardcode. Use `.env` with `pydantic-settings`.

## Docs worth reading before deep changes

- `docs/architecture.md` — module boundaries and runtime flow.
- `docs/stream-api.md` — SSE event framing and caching.
- `docs/model-providers.md` — `.env` recipes per LLM provider.
- `src/crew/schemas/SCHEMAS.md` — structured-output contracts per agent.

## Git & Style
- **Commits**: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`.
- **Naming**: `snake_case` for variables/functions, `PascalCase` for classes.
