# Contributing to StockSage

Thanks for helping improve StockSage. This project is **local-first**: contributors run the app on their own machine with their own API keys or Ollama.

## Before you start

- Read [CODE_OF_CONDUCT.md](https://github.com/kanishk-varshney/StockSage/blob/main/CODE_OF_CONDUCT.md).
- For security-sensitive reports, see [SECURITY.md](https://github.com/kanishk-varshney/StockSage/blob/main/SECURITY.md).

## Development setup

1. **Clone** the repository.
2. **Install Python** `>=3.13` (see `pyproject.toml`).
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

   Set `LLM_MODEL` and any required API keys (see [Model Providers](https://kanishk-varshney.github.io/StockSage/model-providers/)).

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

## Typecheck (scoped)

CI runs `mypy` on structured-output modules only. Locally:

```bash
make typecheck
```

## AI-assisted contributions

This project was built with AI coding assistance (Claude Code). AI-assisted contributions are welcome — use whatever tools help you. The only requirement is that **you understand and can explain what you're submitting**. Don't paste-and-run without reading: broken AI output that passes review is worse than no contribution.

## Tests

```bash
make test
```

Or: `python -m pytest` / `uv run pytest`

Keep new behavior covered when it is easy to test; UI-heavy changes may rely on manual checks—note that in your PR.

## Before you push

CI runs these same checks — run them locally first to avoid round-trips:

```bash
make install                         # one-time: installs the pre-commit git hook
uv run pre-commit run --all-files    # formatting, whitespace, YAML/TOML checks
make lint                            # ruff
make typecheck                       # mypy (scoped)
make test                            # pytest with coverage
make security                        # pip-audit + bandit
```

`make install` only needs to run once per clone. After that, failing hook checks block `git commit` locally, so you never push broken formatting or trailing whitespace.

## Branching & commits

StockSage follows **trunk-based development**: `main` is always releasable, and work happens on short-lived branches.

### Branch names

All branches (except `main` and `release`) must match:

```
^(feat|fix|docs|chore|refactor|test)/[a-z0-9][a-z0-9-]*$
```

| Type | When to use | Example |
|------|-------------|---------|
| `feat/` | New user-visible feature | `feat/sector-comparison-card` |
| `fix/` | Bug fix | `fix/flex-item-null-display` |
| `docs/` | Docs-only change | `docs/groq-provider-example` |
| `test/` | Test-only change | `test/download-pipeline-mock` |
| `refactor/` | Internal restructure, no behavior change | `refactor/schema-validators` |
| `chore/` | Tooling, CI, deps, repo hygiene | `chore/repo-hygiene-and-branching` |

Enforced by `.github/workflows/branch-name.yml` on every PR (Dependabot branches are exempt).

### PR titles — Conventional Commits

PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <lowercase subject, no trailing period>
```

Allowed types: `feat, fix, docs, chore, refactor, test, build, ci, perf`.

Enforced by `.github/workflows/semantic-pr.yml`. The title (not individual commits) becomes the squash-merge commit message, which lets us automate `CHANGELOG.md` later.

### Signed commits

`main` has `required_signatures=true`. Every commit merged into `main` must be GPG- or SSH-signed. Locally:

```
git config --global commit.gpgsign true
git config --global user.signingkey <your-key-id>
```

See [GitHub's signing guide](https://docs.github.com/en/authentication/managing-commit-signature-verification) for setup.

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
