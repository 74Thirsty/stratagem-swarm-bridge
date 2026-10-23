# Roadmap and acceptance gates

## Implemented in the current branch
- [x] Textual multi-pane communications desk.
- [x] SQLite contacts, conversations, messages, community metadata, and draft outbox.
- [x] Grok draft integration and editable Markdown mediator instructions.
- [x] Moltbook account registration behind explicit confirmation.
- [x] Existing Moltbook API-key validation; secrets use the OS credential manager, not SQLite.
- [x] Read-only Moltbook feed and search.
- [x] Tests for persistence, app flows, adapter safety, and API-key host/redirect handling.
- [x] GitHub Actions test/lint workflow.

## Next gates
1. Observe CI and fix any failures; run the full suite in a real Linux and Windows environment.
2. Verify official Moltbook DM and messaging endpoints against current official docs and live behavior before implementing them; community posts report endpoint inconsistencies.
3. Add human-reviewed public post/comment composition with a second confirmation and an audit log.
4. Add robust message/thread normalization and pagination against captured fixture responses.
5. Add credential-manager diagnostics and an explicit disconnect/rotate-key workflow.
6. Add Windows packaging and a Linux installable distribution.

## Safety boundaries
- No autonomous swarm orchestration.
- No background agent-to-agent messaging.
- No automatic posting/commenting/DMs in this build.
- No verification bypass or automated claiming of an account.
- Never claim an account was created unless the official API returned a valid key and registration details.
