# OSS launch checklist

## Repository settings

- Enable **Discussions** in GitHub repository settings for setup and usage Q&A.
- Keep Issues focused on bugs/features; redirect support questions to Discussions.
- Add repository topics: `llm`, `crewai`, `fastapi`, `finance`, `ollama`, `agents`.

## Starter issue backlog (`good first issue`)

Create and label these issues after publishing:

1. ~~Add integration test for `DownloadPipeline` failure branches with mocked fetchers.~~ (See `tests/core/test_download_pipeline.py`.)
2. ~~Add screenshot/GIF capture script and embed final assets in README.~~ (Script: `scripts/capture_readme_assets.sh`; GIF still optional.)
3. Add provider smoke checks for OpenAI/Gemini/Groq in `src/core/config/check.py`.
4. Add pagination/collapse behavior for long UI analysis cards.
5. ~~Add typed API response model for `/stream` and `/stream/mock` event payload docs.~~ (See `docs/stream-api.md` — documents events and logical `LogEntry` mapping; payloads remain HTML.)

## Publishing notes

- If history was rewritten, share `docs/history-rewrite-checklist.md` in release notes.
- Ask contributors to re-clone to avoid stale commit references.
