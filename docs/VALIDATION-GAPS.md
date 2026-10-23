# Validation gaps

This document tracks verification work that must be completed before the application is called production-ready.

- Run the full pytest suite and Ruff against the feature branch.
- Exercise the Textual UI with its test pilot, including draft persistence and contact creation.
- Verify the xAI chat-completions endpoint and configured model against current official documentation.
- Verify every Moltbook API route and payload against current official documentation before relying on it.
- Exercise credential storage on Linux and Windows; never write API keys into SQLite or logs.
- Test installation and startup on supported Linux and Windows versions.
- Keep public posting behind explicit per-action confirmation. Do not enable direct messaging until the documented API and consent flow have been reviewed.

No validation item should be marked complete without a recorded command, environment, and result.