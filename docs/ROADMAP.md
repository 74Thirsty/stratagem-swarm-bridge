# Roadmap and acceptance gates

## Implemented in the current branch
- [x] Textual multi-pane communications desk.
- [x] SQLite contacts, conversations, messages, community metadata, and draft outbox.
- [x] Grok draft integration and editable Markdown mediator instructions.
- [x] Moltbook account registration behind explicit confirmation.
- [x] Existing Moltbook API-key validation; secrets use the OS credential manager, not SQLite.
- [x] Read-only Moltbook feed and search.
- [x] Public post and comment publication behind a per-action review/confirmation dialog.
- [x] Tests for persistence, app flows, adapter safety, and API-key host/redirect handling.
- [x] GitHub Actions test/lint workflow.

## Next gates
1. Observe CI and fix any failures; run the full suite in a real Linux and Windows environment.
2. Verify official Moltbook DM endpoints against current official docs and live behavior before implementing them; reports conflict about endpoint availability.
3. Add inbox/notification normalization and cursor pagination against captured fixture responses.
4. Add an append-only local audit trail for each confirmed external action.
5. Add credential-manager diagnostics and an explicit disconnect/rotate-key workflow.
6. Add Windows packaging and a Linux installable distribution.

## Safety boundaries
- No autonomous swarm orchestration.
- No background agent-to-agent messaging.
- Public posts/comments require explicit review and confirmation every time.
- No direct messages in this build.
- No verification bypass or automated claiming of an account.
- Never claim an account or post/comment succeeded unless the official API returned a success response.
