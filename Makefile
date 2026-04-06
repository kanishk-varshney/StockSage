.DEFAULT_GOAL := help

.PHONY: install run dev test lint check clean help

install: ## Install dependencies from uv.lock (recommended)
	uv sync

run: ## Start the app in production mode (http://127.0.0.1:8000)
	uv run uvicorn src.app.main:app --reload

dev: ## Start the app in dev/mock-stream mode
	STOCKSAGE_APP_MODE=dev uv run uvicorn src.app.main:app --reload

test: ## Run the test suite
	uv run python -m pytest

lint: ## Lint with ruff
	uv run python -m ruff check .

check: ## Validate .env config and LLM connectivity
	uv run python -m src.core.config.check

clean: ## Remove __pycache__ and .pytest_cache (never touches .market_data)
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
	rm -rf .pytest_cache

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'
