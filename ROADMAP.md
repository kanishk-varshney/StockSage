# Roadmap

## Scope and non-goals

StockSage is a local-first, run-it-yourself analysis tool. It is not a hosted SaaS and not personalized investment advice.

### In scope
- Improve analysis quality, reliability, and explainability.
- Keep model-provider setup simple across local (Ollama) and cloud APIs.
- Maintain contributor-friendly docs and tests for core flows.

### Out of scope (for now)
- Multi-tenant auth, billing, and hosted account management.
- Broker integrations or automated trade execution.
- Guaranteed real-time market data SLAs.

## Near-term priorities

1. ~~Extend integration tests for download and Crew failure edge cases.~~ (baseline in `tests/core/test_download_pipeline.py`, `tests/crew/test_pipeline_failure.py`; expand as needed.)
2. ~~Add lightweight lint/type checks in CI.~~ (scoped `mypy` on structured-output modules; widen coverage over time.)
3. Improve UX discoverability with real screenshots/GIF in README (assets + `scripts/capture_readme_assets.sh`; optional GIF).
4. Add `good first issue` backlog and contributor onboarding issues (GitHub labels/issues after publish — see `docs/oss-launch-checklist.md`).

## License

Released under the MIT License.
