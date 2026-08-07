# Security and Secrets

## Local Setup

1. Copy `.env.example` to `.env`.
2. Generate unique local values for `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, and `POSTGRES_PASSWORD`.
3. Configure only the providers and integrations required for the features being tested.
4. Never paste real credentials into `.env.example`.
5. Never commit `.env`, certificates, tokens, cookies, service-account files, or storage contents.

## Secret Scanning

The repository uses `detect-secrets` through `.pre-commit-config.yaml` and `.github/workflows/security.yml`.
Run locally with:

```text
python -m pip install pre-commit detect-secrets==1.5.0
pre-commit install
pre-commit run --all-files
```

Review any baseline change manually. Do not resolve a real secret by adding it to the baseline. Rotate it first.

The baseline is intentionally empty. Synthetic test credentials and Alembic revision identifiers are marked with `pragma: allowlist secret` on their exact lines. Application code must not add allowlist comments for real credentials.

Gitleaks scans full Git history. `.gitleaksignore` contains two immutable reviewed fingerprints only: a Python class-name false positive and an empty historical Adzuna placeholder false positive. Any new fingerprint requires manual source inspection before it can be added.

## Production Requirements

Production and staging settings reject the development JWT secret and invalid/placeholder Fernet keys. Use HTTPS for every public callback and webhook URL, restrict OAuth redirect URLs exactly, and rotate provider credentials if they are exposed.

The current `X-User-ID` development identity boundary is not production authentication. Do not expose the application publicly until JWT registration/login and bearer-token enforcement are implemented.
