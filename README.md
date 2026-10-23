# Stratagem Swarm Bridge

A local-first, single-agent communications desk: one Grok-powered mediator, one polished terminal UI, and a human in control.

## Current MVP

- Inbox, conversation threads, contacts, drafts, and durable SQLite message history.
- Grok response drafting through the xAI API.
- Editable mediator instructions loaded from Markdown files.
- Moltbook agent registration with an explicit confirmation step.
- Existing Moltbook API-key validation and OS credential-manager storage.
- Read-only Moltbook feed and search.
- Public posts and comments require a separate review/confirmation dialog before publication.
- Direct messages and automated/background messaging remain disabled.
- Community account metadata is local; API keys are not stored in SQLite.

## Run

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
swarmbridge
```

On Windows PowerShell, activate with `.venv\\Scripts\\Activate.ps1`.

Set `XAI_API_KEY` to enable Grok drafting. Optional `XAI_MODEL` defaults to `grok-4.7`, the current xAI flagship model at the time of this update. You can override it with any model available to your xAI API key. No xAI key is required for local contacts, conversations, or drafts.

## Moltbook

Use the Communities & Accounts view to register an agent or connect an existing key. Registration creates a real external account only after the confirmation dialog. Complete Moltbook's claim/owner verification steps yourself.

Moltbook keys are stored using the operating system credential manager via Python keyring. If the credential manager is unavailable, fix that before connecting. The app never sends the key to any host other than `https://www.moltbook.com/api/v1`, refuses redirects, and does not save the key in SQLite. Review claim links and verification codes after registration.

The adapter supports registration, profile validation, read-only feed/search, and human-confirmed public posts/comments. Direct messaging is deliberately disabled until current official endpoint behavior can be verified.

## Data and safety

- Local database: platform-specific user data directory, file `bridge.sqlite3`.
- API keys are not written to the database.
- Remote messages and imported instruction files are untrusted input.
- Generated replies are drafts; review before use.
- Registration and publication are explicit external actions with confirmation dialogs.

## Development

```bash
pytest
ruff check src tests
```

See `docs/ROADMAP.md` for remaining gates.
