# Roadmap

## What StockSage is

A local-first stock analysis tool you run on your own machine with your own model (Ollama or any supported cloud provider). Not a hosted service, not investment advice.

**In scope — what we're investing in**
- Better analysis quality and explainability (stronger agent prompts, clearer reasoning in the final verdict).
- Simple, reliable model-provider setup across local (Ollama) and cloud APIs.
- Contributor-friendly docs and tests for the core pipeline.

**Not planned:** broker integrations, automated trading, hosted multi-user accounts, real-time market data SLAs.

## What's next

Rough priority order. Open an issue if you'd like to pick one up.

1. **Publish to PyPI** so installing becomes `pip install stocksage`.
2. **Automated releases** — on merge to `main`, parse Conventional Commit titles to bump the version in `pyproject.toml`, regenerate `CHANGELOG.md`, and open a release PR; on a `v*.*.*` tag, build and publish the wheel to PyPI.
3. **Troubleshooting guide** — common setup issues (Ollama not reachable, provider rate limits, stale cached data).
4. **More robust tests** for the live SSE stream and higher coverage on the analysis pipeline.
5. **Community surface** — enable GitHub Discussions, seed a few good-first-issues, add searchable repo topics.
6. **New analysis cards or agents** — sector comparison, peer benchmarks, earnings-call sentiment. Ideas welcome in issues.
7. **Concurrent analyses** — support multiple tickers in parallel. Today a second request fails or reports "already in progress"; we want per-request isolation so different users (or tabs) can analyze independently.

## License

MIT. See [LICENSE](LICENSE).
