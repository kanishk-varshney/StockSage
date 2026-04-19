# Security policy

## Supported versions

Security fixes are applied to the default branch (`main`) only. Use the latest commit for production-like deployments.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead:

1. Open a **private security advisory** on GitHub (Repository → **Security** → **Advisories** → **Report a vulnerability**), or
2. Contact maintainers through a private channel if one is listed on the repository.

Include:

- Description of the issue and impact
- Steps to reproduce (if possible)
- Suggested fix (if you have one)

We aim to acknowledge reports within a few days.

## Secrets and accidental exposure

- **Never commit** real API keys, tokens, or `.env` files. Use `.env.example` only with placeholders.
- If you accidentally committed a secret:
  1. **Rotate/revoke** the key immediately with the provider (OpenAI, Serper, etc.).
  2. Remove the secret from the latest commit and open a PR.
  3. If the secret was pushed to a public remote, assume it is compromised even after removal from history.

GitHub [secret scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning) may alert on known patterns; treat alerts seriously.

## Scope and threat model

StockSage is a **single-user, local-only tool**. It has no authentication, no session management, and no multi-tenant isolation. The FastAPI server binds to `127.0.0.1:8000` by default — do not expose it on a public interface without adding auth in front (e.g. a reverse proxy with basic auth). If you use `--host 0.0.0.0` or deploy it on a VPS, anyone who can reach that port can trigger LLM calls using your API keys.

Primary threat surface:
- **Dependency vulnerabilities** — `pip-audit` or `uv audit` can scan the lock file.
- **SSRF via misconfigured tools** — the search tool makes outbound HTTP; Ollama base URL is configurable.
- **Accidental secret exposure** — API keys in `.env`, logs, or issue reports.
- **Malicious ticker input** — symbol is validated against a format regex before any I/O, but downstream CSV filenames are derived from the symbol; verify this if you extend the storage layer.
