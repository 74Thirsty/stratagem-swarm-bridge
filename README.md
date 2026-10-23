# Stratagem Swarm Bridge

A local-first, single-agent communications desk: one Grok-powered mediator, one polished terminal UI, and a human in control.

## Current MVP

- Inbox, conversation threads, contacts, drafts, and durable SQLite message history.
- Grok-compatible drafting through the xAI API; credentials stay in environment variables.
- Editable mediator instructions loaded from Markdown files.
- Community/account directory with adapter capability/status tracking.
- Outbound messages are **draft-only** by default. The MVP deliberately has no automatic external-send path.
- First community slot: Moltbook, represented as an adapter scaffold until its current API and account-creation requirements are verified.

## Run

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
swarmbridge
```

On Windows PowerShell, activate with `.venv\\Scripts\\Activate.ps1`.

Set `XAI_API_KEY` to enable Grok drafting. Optional `XAI_MODEL` defaults to `grok-3-mini`. No key is required to use local contacts, conversations, and drafts.

## Data and safety

- Local database: `~/.local/share/stratagem-swarm-bridge/bridge.sqlite3` (platform-aware user data directory).
- API key is read from the environment and is never written to the database.
- External messages are never sent by this MVP. Community account creation and live posting must be implemented only after validating each community's official requirements.
- Treat remote agent messages and imported instruction files as untrusted input. Review generated drafts before using them.

## Development

```bash
pytest
```

See `docs/ROADMAP.md` for the next implementation gates.
