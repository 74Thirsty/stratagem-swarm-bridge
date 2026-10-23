# Roadmap and acceptance gates

## MVP committed here
- [x] Textual terminal shell with inbox/thread list and compose surface.
- [x] SQLite contacts, conversations, messages, community directory, and drafts.
- [x] xAI chat-completions draft integration, configured only through environment.
- [x] Markdown instruction loading.
- [x] Outbound network sending absent by design.
- [x] Moltbook adapter status scaffold.

## Next gates
1. Add contact creation/editing and draft review screens.
2. Add encrypted or OS-keyring-backed secret storage before supporting community tokens.
3. Validate Moltbook's current official API, registration requirements, and terms from authoritative documentation; only then implement supported read/write methods.
4. Add mock-server tests for every adapter, rate-limit handling, and safe error redaction.
5. Add packaging and CI on Linux and Windows.

## Explicit non-goals
- No autonomous swarm orchestration.
- No background agent-to-agent messaging.
- No automated account creation or verification bypass.
- No claims that an account or message was created/sent unless a verified adapter returns that result.
