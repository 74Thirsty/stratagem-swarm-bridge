"""Small SQLite persistence layer. Secrets are intentionally not stored here."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from platformdirs import user_data_path


def default_db_path() -> Path:
    return Path(user_data_path("stratagem-swarm-bridge", appauthor=False)) / "bridge.sqlite3"


class Store:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a short-lived connection and always close it."""
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _init_db(self) -> None:
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    community TEXT NOT NULL DEFAULT 'local',
                    handle TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
                    community TEXT NOT NULL DEFAULT 'local',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    direction TEXT NOT NULL CHECK(direction IN ('inbound','outbound','note')),
                    body TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'saved',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS communities (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'scaffold',
                    account_name TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY,
                    conversation_id INTEGER REFERENCES conversations(id) ON DELETE SET NULL,
                    recipient TEXT NOT NULL DEFAULT '',
                    community TEXT NOT NULL DEFAULT 'local',
                    body TEXT NOT NULL,
                    approved INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
            db.execute(
                "INSERT OR IGNORE INTO communities(name, enabled, status, notes) VALUES "
                "('Moltbook', 0, 'scaffold', 'Adapter pending official API and account-flow validation.')"
            )

    def add_contact(self, name: str, community: str = "local", handle: str = "", notes: str = "") -> int:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("contact name cannot be empty")
        with self.connect() as db:
            cur = db.execute(
                "INSERT INTO contacts(name, community, handle, notes) VALUES (?, ?, ?, ?)",
                (clean_name, community.strip() or "local", handle.strip(), notes.strip()),
            )
            return int(cur.lastrowid)

    def contacts(self):
        with self.connect() as db:
            return db.execute("SELECT * FROM contacts ORDER BY name COLLATE NOCASE").fetchall()

    def create_conversation(self, title: str, community: str = "local", contact_id: int | None = None) -> int:
        with self.connect() as db:
            cur = db.execute(
                "INSERT INTO conversations(title, community, contact_id) VALUES (?, ?, ?)",
                (title.strip() or "Untitled conversation", community, contact_id),
            )
            return int(cur.lastrowid)

    def conversations(self):
        with self.connect() as db:
            return db.execute(
                "SELECT c.*, (SELECT body FROM messages m WHERE m.conversation_id=c.id "
                "ORDER BY m.id DESC LIMIT 1) AS last_message FROM conversations c "
                "ORDER BY c.updated_at DESC, c.id DESC"
            ).fetchall()

    def messages(self, conversation_id: int):
        with self.connect() as db:
            return db.execute(
                "SELECT * FROM messages WHERE conversation_id=? ORDER BY id", (conversation_id,)
            ).fetchall()

    def add_message(self, conversation_id: int, direction: str, body: str, status: str = "saved") -> int:
        if direction not in {"inbound", "outbound", "note"}:
            raise ValueError("direction must be inbound, outbound, or note")
        if not body.strip():
            raise ValueError("message body cannot be empty")
        with self.connect() as db:
            cur = db.execute(
                "INSERT INTO messages(conversation_id, direction, body, status) VALUES (?, ?, ?, ?)",
                (conversation_id, direction, body, status),
            )
            db.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (conversation_id,))
            return int(cur.lastrowid)

    def save_draft(self, body: str, recipient: str = "", community: str = "local",
                   conversation_id: int | None = None) -> int:
        if not body.strip():
            raise ValueError("draft body cannot be empty")
        with self.connect() as db:
            cur = db.execute(
                "INSERT INTO drafts(conversation_id, recipient, community, body) VALUES (?, ?, ?, ?)",
                (conversation_id, recipient.strip(), community.strip() or "local", body),
            )
            return int(cur.lastrowid)

    def drafts(self):
        with self.connect() as db:
            return db.execute("SELECT * FROM drafts ORDER BY updated_at DESC, id DESC").fetchall()

    def communities(self):
        with self.connect() as db:
            return db.execute("SELECT * FROM communities ORDER BY name").fetchall()

    def set_community_account(self, name: str, account_name: str, notes: str = "") -> None:
        with self.connect() as db:
            result = db.execute(
                "UPDATE communities SET account_name=?, notes=? WHERE name=?",
                (account_name.strip(), notes.strip(), name),
            )
            if result.rowcount == 0:
                raise ValueError(f"unknown community: {name}")
