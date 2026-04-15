.DEFAULT_GOAL := help

.PHONY: install run dev test lint format typecheck security check clean help

install: ## Install dependencies and pre-commit hooks
	uv sync --extra dev
	uv run pre-commit install

run: ## Start the app in production mode (http://127.0.0.1:8000)
	uv run uvicorn src.app.main:app --reload

dev: ## Start the app in dev/mock-stream mode
	STOCKSAGE_APP_MODE=dev uv run uvicorn src.app.main:app --reload

test: ## Run the test suite with coverage
	uv run python -m pytest

lint: ## Lint with ruff
	uv run python -m ruff check .

format: ## Auto-fix lint + format with ruff
	uv run python -m ruff check --fix .
	uv run python -m ruff format .

typecheck: ## Run mypy over the full src/ package
	uv run mypy src/ --ignore-missing-imports --explicit-package-bases

security: ## Run pip-audit (dependency CVEs) and bandit (static analysis)
	uv run pip-audit
	uv run bandit -r src/ -ll -q

check: ## Validate .env config and LLM connectivity
	uv run python -m src.core.config.check

clean: ## Remove __pycache__, .pytest_cache, and coverage artifacts
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
	rm -rf .pytest_cache .coverage coverage.xml htmlcov/

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
