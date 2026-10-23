# Validation gaps

This document tracks verification work that must be completed before the application is called production-ready.

## Verified by GitHub Actions

- Workflow run [#45](https://github.com/74Thirsty/stratagem-swarm-bridge/actions/runs/39905656223), commit `fe108e6e3c7119610b2c5205d7a58b835ceae953`: all four matrix jobs completed successfully — Ubuntu and Windows, Python 3.11 and 3.12. Each job runs `pytest -q` and `ruff check src tests`.
- The above run validates the code at that commit only. Subsequent commits migrating the Grok mediator to the Responses API and expanding response parsing require a new successful run before those changes are considered validated.

## Implemented in the feature branch

- Added mocked tests for Grok drafting, request payload construction, missing-key behavior, malformed responses, structured output parsing, and custom instruction loading.
- Configured GitHub Actions to run pytest and Ruff on Ubuntu and Windows with Python 3.11 and 3.12.
- Updated the default xAI model to `grok-4.7`.
- Migrated the Grok mediator from the legacy Chat Completions endpoint to the xAI Responses API. Requests explicitly set `store: false`; this is intended to keep mediator prompts and drafts out of xAI's stored response history.
- Checked the documented Moltbook endpoints against the official Moltbook skill documentation: registration, `/agents/me`, `/agents/status`, `/feed`, `/search`, `/posts`, and `/posts/{id}/comments` are documented. This is source-level verification, not a live API integration test.

## Still unverified

- No local pytest or Ruff run has been performed in this environment; GitHub Actions is the test evidence.
- The latest Responses API migration commits need a completed passing CI run.
- Exercise the Textual UI with its test pilot, including draft persistence and contact creation, on actual dependency versions.
- Live Moltbook API behavior is not tested. In particular, community reports have described intermittent authentication failures for comment publication; do not assume comments succeed just because the endpoint is documented.
- Exercise credential storage on Linux and Windows; never write API keys into SQLite or logs.
- Test installation and startup on supported Linux and Windows versions. CI test execution is not a packaged-install smoke test.
- Keep public posting and commenting behind explicit per-action confirmation. Do not enable direct messaging until current official endpoint behavior and the consent flow have been reviewed.

No validation item should be marked complete without a recorded command, environment, and result.
