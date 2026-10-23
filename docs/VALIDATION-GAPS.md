# Validation gaps

This document tracks verification work that must be completed before the application is called production-ready.

## Implemented in the feature branch

- Added mocked tests for successful Grok drafting, request payload construction, missing-key behavior, malformed responses, and custom instruction loading.
- Configured GitHub Actions to run pytest and Ruff on Ubuntu and Windows with Python 3.11 and 3.12.
- Updated the default xAI model to `grok-4.7`, listed by current xAI documentation.

## Still unverified

- The current execution environment cannot resolve `github.com`, so I have not run pytest or Ruff locally.
- No successful GitHub Actions run has yet been observed for the latest commits. The matrix is configured but is not evidence of a passing build.
- Exercise the Textual UI with its test pilot, including draft persistence and contact creation, on actual dependency versions.
- Verify every Moltbook route and payload against the current official API documentation before relying on it in production.
- Exercise credential storage on Linux and Windows; never write API keys into SQLite or logs.
- Test installation and startup on supported Linux and Windows versions.
- Keep public posting behind explicit per-action confirmation. Do not enable direct messaging until the documented API and consent flow have been reviewed.

No validation item should be marked complete without a recorded command, environment, and result.
