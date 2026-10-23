"""Textual UI for the local-first mediator desk."""
from __future__ import annotations

from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static, TextArea
from textual.binding import Binding

from swarmbridge.communities import MoltbookAdapter
from swarmbridge.mediator import GrokMediator, load_instructions
from swarmbridge.store import Store


CSS = """
Screen { background: #0b1020; color: #e7ecf5; }
Header { background: #131c32; color: #8fe8d1; }
Footer { background: #131c32; }
#banner { height: 3; padding: 1 2; background: #152440; color: #8fe8d1; }
#layout { height: 1fr; }
#sidebar { width: 30; border: round #304563; padding: 1; }
#main { width: 1fr; border: round #304563; padding: 1; }
.section-title { color: #8fe8d1; text-style: bold; margin-bottom: 1; }
#thread-list { height: 1fr; }
#thread { height: 1fr; border: round #263958; padding: 1; }
#compose { height: 7; }
#composer-row { height: 3; }
#status { height: 2; color: #aab8d0; }
Button { margin-right: 1; }
.primary { background: #1b806f; color: white; }
ListView { background: #101a2e; }
ListItem.--highlight { background: #21435a; }
TextArea { background: #101a2e; border: round #304563; }
"""


class BridgeApp(App):
    TITLE = "STRATAGEM  /  SWARM BRIDGE"
    SUB_TITLE = "single-agent mediator • local-first • human-controlled"
    CSS = CSS
    BINDINGS = [
        Binding("ctrl+n", "new_conversation", "New thread"),
        Binding("ctrl+s", "save_draft", "Save draft"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.store = Store()
        self.mediator = GrokMediator()
        self.active_conversation: int | None = None
        self.adapter = MoltbookAdapter()
        self.instruction_path = Path("AGENTS.md")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("◈  MEDIATOR DESK     /     INBOX  ·  THREADS  ·  CONTACTS  ·  COMMUNITIES", id="banner")
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                yield Label("WORKSPACE", classes="section-title")
                yield Button("＋  New conversation", id="new-thread", classes="primary")
                yield Button("◎  Contacts", id="contacts")
                yield Button("⌘  Communities", id="communities")
                yield Button("✎  Instructions", id="instructions")
                yield Label("CONVERSATIONS", classes="section-title")
                yield ListView(id="thread-list")
            with Vertical(id="main"):
                yield Label("MESSAGE STREAM", classes="section-title")
                with VerticalScroll(id="thread"):
                    yield Static(
                        "Select a conversation or create a new one.\n\n"
                        "External communication is locked: this MVP saves drafts only.",
                        id="thread-content",
                    )
                yield Label("COMPOSE / DRAFT", classes="section-title")
                yield TextArea(id="compose", soft_wrap=True)
                with Horizontal(id="composer-row"):
                    yield Input(placeholder="Recipient / contact (optional)", id="recipient")
                    yield Button("Draft with Grok", id="grok", classes="primary")
                    yield Button("Save draft", id="save-draft")
                yield Static(
                    "READY  •  outbound locked  •  " +
                    ("Grok configured" if self.mediator.configured else "Grok not configured"),
                    id="status",
                )
        yield Footer()

    async def on_mount(self) -> None:
        await self.refresh_threads()

    async def refresh_threads(self) -> None:
        view = self.query_one("#thread-list", ListView)
        await view.clear()
        for conv in self.store.conversations():
            title = conv["title"]
            preview = (conv["last_message"] or "No messages yet").replace("\n", " ")
            await view.append(ListItem(Label(f"{title}\n[dim]{preview[:38]}[/dim]"), name=str(conv["id"])))
        if self.active_conversation is not None:
            await self.show_thread(self.active_conversation)

    async def show_thread(self, conversation_id: int) -> None:
        self.active_conversation = conversation_id
        rows = self.store.messages(conversation_id)
        lines = []
        for row in rows:
            tag = {"inbound": "INBOUND", "outbound": "OUTBOUND DRAFT", "note": "NOTE"}.get(
                row["direction"], row["direction"]
            )
            lines.append(f"[bold #8fe8d1]{tag}[/bold #8fe8d1]  [dim]{row['created_at']}[/dim]\n{row['body']}\n")
        content = "\n".join(lines) or "No messages yet. Use the composer to save a draft."
        self.query_one("#thread-content", Static).update(content)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item.name:
            await self.show_thread(int(event.item.name))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id
        if action == "new-thread":
            self.action_new_conversation()
        elif action == "save-draft":
            self.save_draft_now()
        elif action == "grok":
            await self.draft_with_grok()
        elif action == "contacts":
            contacts = self.store.contacts()
            summary = "\n".join(
                f"• {c['name']}  /  {c['community']}  {c['handle']}" for c in contacts
            )
            self.notify(
                summary or "No contacts yet. Contact editing is on the MVP roadmap.",
                title="CONTACTS",
                timeout=8,
            )
        elif action == "communities":
            rows = self.store.communities()
            detail = "\n".join(f"{r['name']}: {r['status']} — {r['notes']}" for r in rows)
            self.notify(detail + "\n" + self.adapter.status().detail, title="COMMUNITIES", timeout=10)
        elif action == "instructions":
            self.notify(
                f"Instruction file: {self.instruction_path.resolve()}\n" +
                ("Loaded from disk." if self.instruction_path.is_file()
                 else "Using safe built-in defaults. Add AGENTS.md to customize."),
                title="MEDIATOR INSTRUCTIONS",
                timeout=8,
            )

    def action_new_conversation(self) -> None:
        title = f"Conversation {len(self.store.conversations()) + 1}"
        self.active_conversation = self.store.create_conversation(title)
        self.run_worker(self.refresh_threads(), exclusive=True)
        self.query_one("#thread-content", Static).update(
            "New conversation. Enter a message and save it as a draft."
        )

    def action_save_draft(self) -> None:
        self.save_draft_now()

    def save_draft_now(self) -> None:
        body = self.query_one("#compose", TextArea).text.strip()
        recipient = self.query_one("#recipient", Input).value.strip()
        if not body:
            self.notify("Write a message first.", severity="warning")
            return
        if self.active_conversation is None:
            self.active_conversation = self.store.create_conversation(recipient or "Unsent draft")
        self.store.save_draft(body, recipient=recipient, conversation_id=self.active_conversation)
        self.store.add_message(self.active_conversation, "outbound", body, status="draft")
        self.query_one("#compose", TextArea).text = ""
        self.notify("Draft saved locally. Nothing was sent.")
        self.run_worker(self.refresh_threads(), exclusive=True)

    async def draft_with_grok(self) -> None:
        body = self.query_one("#compose", TextArea).text.strip()
        if not body:
            self.notify("Enter the message or prompt you want help with.", severity="warning")
            return
        self.query_one("#status", Static).update(
            "WORKING  •  asking Grok for a draft; no message will be sent"
        )
        try:
            instructions = load_instructions(self.instruction_path)
            context = ""
            if self.active_conversation is not None:
                context = "\n".join(
                    m["body"] for m in self.store.messages(self.active_conversation)[-8:]
                )
            result = await self.mediator.draft(body, context=context, instructions=instructions)
            self.query_one("#compose", TextArea).text = result
            self.notify("Grok draft ready for review. It has not been sent.")
        except Exception as exc:
            self.notify(str(exc), title="GROK DRAFT FAILED", severity="error", timeout=8)
        finally:
            self.query_one("#status", Static).update(
                "READY  •  outbound locked  •  " +
                ("Grok configured" if self.mediator.configured else "Grok not configured")
            )


def main() -> None:
    BridgeApp().run()
