# Changelog

All notable changes to this project will be documented in this file.

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
