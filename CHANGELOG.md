# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- `docs/stream-api.md` — SSE event shapes for `/stream` and `/stream/mock`.
- `scripts/capture_readme_assets.sh` — helper to refresh README screenshots (macOS-friendly).
- `.github/dependabot.yml` — weekly pip and GitHub Actions updates.
- Scoped `mypy` in CI and `make typecheck` for `src.crew.schemas._base` and `src.crew.structured_output`.
- Tests: `DownloadPipeline` failure/success branches (`tests/core/test_download_pipeline.py`); crew kickoff failure (`tests/crew/test_pipeline_failure.py`).
- Schema tests for `normalize_payload_lists` via `ValuationOutput` validation.

### Changed
- Packaging: `hatchling` build backend + `src` as an installable package so `uv sync` / `pip install -e .` expose the `src.*` imports (tests and CI rely on this).
- `DownloadPipeline` sets `critical_ok` only after successful critical steps **including** CSV save; `StockProcessor` uses `critical_ok` for `_download_ok` (fixes aborted financials/save still proceeding to analysis).
- Docker image builds with `uv sync --frozen --no-dev` and `uv.lock` for reproducible runtime deps.
- CI installs with `uv sync --frozen --extra dev` to match local lockfile workflows.

### Fixed
- README Quickstart clone URL now points at the canonical GitHub repo.

## [0.1.0] - 2026-04-06

### Added
- OSS community baseline: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`.
- GitHub collaboration scaffolding: issue templates, PR template, and CI workflow.
- Provider-aware environment preflight command: `python -m src.core.config.check`.
- Docs set for setup and architecture:
  - `docs/local-setup.md`
  - `docs/model-providers.md`
  - `docs/architecture.md`
  - `docs/self-host.md`
  - `docs/examples/crew-output-guide.md`
  - `docs/examples/output-preview.md`
- Integration tests for SSE streaming and processor orchestration.
- Manual crew runner moved to `scripts/run_crew.py`.

### Changed
- README refocused around local-first usage with provider matrix and example-output links.
- User-facing stream/pipeline failures now emit sanitized messages with log reference IDs.
- Removed runtime/path bootstrapping hacks (`sys.path.insert`) from app/tests.
- Dependency cleanup in `pyproject.toml`:
  - removed direct `plotly` dependency (unused)
  - removed direct `urllib3<2` pin

### Removed
- Root-level generated artifact docs and machine files:
  - `CREW_OUTPUT.md` moved into `docs/examples/`
  - `.DS_Store` removed
