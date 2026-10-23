"""Polished Textual communications desk for one human-controlled mediator."""
from __future__ import annotations

from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button, ContentSwitcher, Footer, Header, Input, Label, ListItem, ListView,
    Static, TextArea,
)

from swarmbridge.communities import MoltbookAdapter
from swarmbridge.mediator import GrokMediator, load_instructions
from swarmbridge.store import Store


CSS = """
Screen { background: #0b1020; color: #e7ecf5; }
Header { background: #131c32; color: #8fe8d1; }
Footer { background: #131c32; }
#banner { height: 3; padding: 1 2; background: #152440; color: #8fe8d1; }
#layout { height: 1fr; }
#sidebar { width: 29; border: round #304563; padding: 1; }
#main { width: 1fr; border: round #304563; padding: 1; }
.section-title { color: #8fe8d1; text-style: bold; margin: 1 0; }
#workspace { height: 1fr; }
#inbox-pane, #contacts-pane, #communities-pane, #instructions-pane, #drafts-pane { height: 1fr; }
#thread-list { height: 1fr; min-height: 6; }
#thread { height: 1fr; min-height: 6; border: round #263958; padding: 1; }
#compose { height: 7; }
#composer-row { height: 3; }
#status { height: 2; color: #aab8d0; }
#contact-list, #draft-list { height: 1fr; min-height: 5; }
#instruction-editor { height: 1fr; }
#community-notes { height: 6; }
Input { margin-bottom: 1; }
Button { margin-right: 1; }
.primary { background: #1b806f; color: white; }
.warning { background: #7c4d20; color: white; }
ListView { background: #101a2e; }
ListItem.--highlight { background: #21435a; }
TextArea { background: #101a2e; border: round #304563; }
"""


class BridgeApp(App):
    TITLE = "STRATAGEM  /  SWARM BRIDGE"
    SUB_TITLE = "single-agent mediator • local-first • human-controlled"
    CSS = CSS
    BINDINGS = [
        ("ctrl+n", "new_conversation", "New thread"),
        ("ctrl+s", "save_draft", "Save draft"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, store: Store | None = None, mediator: GrokMediator | None = None) -> None:
        super().__init__()
        self.store = store or Store()
        self.mediator = mediator or GrokMediator()
        self.active_conversation: int | None = None
        self.selected_draft_id: int | None = None
        self.adapter = MoltbookAdapter()
        self.instruction_path = Path("AGENTS.md")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("◈  MEDIATOR DESK     /     INBOX  ·  CONTACTS  ·  COMMUNITIES  ·  INSTRUCTIONS  ·  DRAFTS", id="banner")
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                yield Label("WORKSPACE", classes="section-title")
                yield Button("◈  Inbox & conversations", id="nav-inbox", classes="primary")
                yield Button("◎  Contacts", id="nav-contacts")
                yield Button("⌘  Communities & accounts", id="nav-communities")
                yield Button("✎  Mediator instructions", id="nav-instructions")
                yield Button("▤  Draft outbox", id="nav-drafts")
                yield Label("CONVERSATIONS", classes="section-title")
                yield Button("＋  New conversation", id="new-thread")
                yield ListView(id="thread-list")
                yield Static("● OUTBOUND LOCKED", id="lock-label")
            with Vertical(id="main"):
                with ContentSwitcher(initial="inbox-pane", id="workspace"):
                    with Vertical(id="inbox-pane"):
                        yield Label("MESSAGE STREAM", classes="section-title")
                        with VerticalScroll(id="thread"):
                            yield Static(
                                "Select a conversation or create a new one.\n\n"
                                "External communication is locked. This build only saves drafts.",
                                id="thread-content",
                                markup=False,
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
                    with Vertical(id="contacts-pane"):
                        yield Label("CONTACT DIRECTORY", classes="section-title")
                        yield Static("Keep agent handles and community identities in one local directory.")
                        yield Input(placeholder="Contact / agent display name", id="contact-name")
                        yield Input(placeholder="Community (e.g. Moltbook)", id="contact-community")
                        yield Input(placeholder="Handle or profile identifier", id="contact-handle")
                        yield Input(placeholder="Notes (optional)", id="contact-notes")
                        yield Button("＋  Save contact", id="add-contact", classes="primary")
                        yield ListView(id="contact-list")
                    with Vertical(id="communities-pane"):
                        yield Label("COMMUNITY ACCOUNTS", classes="section-title")
                        yield Static(
                            "Adapters remain disconnected until their official API and account rules are verified."
                        )
                        yield Label("Moltbook • scaffold only", classes="section-title")
                        yield Input(placeholder="Your account / handle (optional)", id="community-account")
                        yield TextArea(id="community-notes", soft_wrap=True)
                        yield Button("Save local account notes", id="save-community", classes="primary")
                        yield Static("Connection status: NOT CONNECTED • no requests will be sent.", id="community-status")
                    with Vertical(id="instructions-pane"):
                        yield Label("MEDIATOR INSTRUCTIONS", classes="section-title")
                        yield Static(
                            "These instructions are sent as the system guidance for Grok drafts. "
                            "Imported agent messages remain untrusted."
                        )
                        yield TextArea(id="instruction-editor", soft_wrap=True)
                        yield Button("Save AGENTS.md", id="save-instructions", classes="primary")
                    with Vertical(id="drafts-pane"):
                        yield Label("DRAFT OUTBOX", classes="section-title")
                        yield Static("Saved drafts are local only. Selecting a draft loads it back into the composer.")
                        yield ListView(id="draft-list")
                        yield Button("Open selected draft in composer", id="open-draft", classes="primary")
        yield Footer()

    async def on_mount(self) -> None:
        await self.load_instruction_editor()
        await self.refresh_all()

    async def refresh_all(self) -> None:
        await self.refresh_threads()
        await self.refresh_contacts()
        await self.refresh_drafts()
        rows = self.store.communities()
        if rows:
            self.query_one("#community-account", Input).value = rows[0]["account_name"]
            self.query_one("#community-notes", TextArea).text = rows[0]["notes"]

    async def refresh_threads(self) -> None:
        view = self.query_one("#thread-list", ListView)
        await view.clear()
        for conv in self.store.conversations():
            preview = (conv["last_message"] or "No messages yet").replace("\n", " ")
            await view.append(ListItem(Label(f"{conv['title']}\n{preview[:42]}"), name=str(conv["id"])))
        if self.active_conversation is not None:
            await self.show_thread(self.active_conversation)

    async def refresh_contacts(self) -> None:
        view = self.query_one("#contact-list", ListView)
        await view.clear()
        for contact in self.store.contacts():
            label = f"{contact['name']}  ·  {contact['community']}  ·  {contact['handle']}"
            await view.append(ListItem(Label(label), name=str(contact["id"])))

    async def refresh_drafts(self) -> None:
        view = self.query_one("#draft-list", ListView)
        await view.clear()
        for draft in self.store.drafts():
            label = f"{draft['community']} → {draft['recipient'] or '(no recipient)'}\n{draft['body'][:72]}"
            await view.append(ListItem(Label(label), name=str(draft["id"])))

    async def show_thread(self, conversation_id: int) -> None:
        self.active_conversation = conversation_id
        rows = self.store.messages(conversation_id)
        lines = []
        for row in rows:
            tag = {"inbound": "INBOUND", "outbound": "OUTBOUND DRAFT", "note": "NOTE"}.get(
                row["direction"], row["direction"]
            )
            lines.append(f"{tag}  ·  {row['created_at']}\n{row['body']}\n")
        self.query_one("#thread-content", Static).update(
            "\n".join(lines) or "No messages yet. Use the composer to save a draft."
        )

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "thread-list" and event.item.name:
            await self.show_thread(int(event.item.name))
        elif event.list_view.id == "draft-list":
            self.selected_draft_id = int(event.item.name) if event.item.name else None
            if self.selected_draft_id is not None:
                draft = next((d for d in self.store.drafts() if d["id"] == self.selected_draft_id), None)
                if draft:
                    self.query_one("#compose", TextArea).text = draft["body"]
                    self.query_one("#recipient", Input).value = draft["recipient"]

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id or ""
        nav = {
            "nav-inbox": "inbox-pane",
            "nav-contacts": "contacts-pane",
            "nav-communities": "communities-pane",
            "nav-instructions": "instructions-pane",
            "nav-drafts": "drafts-pane",
        }
        if action in nav:
            self.query_one("#workspace", ContentSwitcher).current = nav[action]
            return
        if action == "new-thread":
            self.action_new_conversation()
        elif action == "save-draft":
            self.save_draft_now()
        elif action == "grok":
            await self.draft_with_grok()
        elif action == "add-contact":
            name = self.query_one("#contact-name", Input).value.strip()
            if not name:
                self.notify("A contact name is required.", severity="warning")
                return
            self.store.add_contact(
                name,
                self.query_one("#contact-community", Input).value.strip() or "local",
                self.query_one("#contact-handle", Input).value.strip(),
                self.query_one("#contact-notes", Input).value.strip(),
            )
            for widget_id in ("contact-name", "contact-community", "contact-handle", "contact-notes"):
                self.query_one(f"#{widget_id}", Input).value = ""
            await self.refresh_contacts()
            self.notify("Contact saved locally.")
        elif action == "save-community":
            self.store.set_community_account(
                "Moltbook",
                self.query_one("#community-account", Input).value,
                self.query_one("#community-notes", TextArea).text,
            )
            self.notify("Account notes saved locally. Moltbook is still disconnected.")
        elif action == "save-instructions":
            content = self.query_one("#instruction-editor", TextArea).text
            self.instruction_path.write_text(content.rstrip() + "\n", encoding="utf-8")
            self.notify(f"Saved {self.instruction_path.resolve()}")
        elif action == "open-draft":
            draft_id = self.selected_draft_id
            draft = next((d for d in self.store.drafts() if d["id"] == draft_id), None)
            if draft is None:
                self.notify("Select a draft first.", severity="warning")
                return
            self.query_one("#workspace", ContentSwitcher).current = "inbox-pane"
            self.query_one("#compose", TextArea).text = draft["body"]
            self.query_one("#recipient", Input).value = draft["recipient"]
            self.notify("Draft loaded. It has not been sent.")

    def action_new_conversation(self) -> None:
        title = f"Conversation {len(self.store.conversations()) + 1}"
        self.active_conversation = self.store.create_conversation(title)
        self.query_one("#workspace", ContentSwitcher).current = "inbox-pane"
        self.run_worker(self.refresh_threads(), exclusive=True)
        self.query_one("#thread-content", Static).update("New conversation. Enter a message and save it as a draft.")

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
        self.store.save_draft(body, recipient=recipient, community="Moltbook" if recipient else "local",
                              conversation_id=self.active_conversation)
        self.store.add_message(self.active_conversation, "outbound", body, status="draft")
        self.query_one("#compose", TextArea).text = ""
        self.notify("Draft saved locally. Nothing was sent.")
        self.run_worker(self.refresh_threads(), exclusive=True)
        self.run_worker(self.refresh_drafts(), exclusive=False)

    async def draft_with_grok(self) -> None:
        body = self.query_one("#compose", TextArea).text.strip()
        if not body:
            self.notify("Enter the message or prompt you want help with.", severity="warning")
            return
        self.query_one("#status", Static).update("WORKING  •  asking Grok for a draft; no message will be sent")
        try:
            instructions = self.query_one("#instruction-editor", TextArea).text.strip() or load_instructions(self.instruction_path)
            context = ""
            if self.active_conversation is not None:
                context = "\n".join(m["body"] for m in self.store.messages(self.active_conversation)[-8:])
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
