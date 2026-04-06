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

1. Extend integration tests for download and Crew failure edge cases.
2. Add lightweight lint/type checks in CI.
3. Improve UX discoverability with real screenshots/GIF in README.
4. Add `good first issue` backlog and contributor onboarding issues.

## License stance (v0.x)

The project currently stays on the Unlicense for maximum permissiveness during early iteration.  
If contributor or adopter needs change, maintainers may switch to MIT or Apache-2.0 in a future minor release with clear release notes.
