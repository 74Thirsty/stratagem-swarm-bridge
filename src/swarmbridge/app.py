"""Polished Textual communications desk for one human-controlled mediator."""
from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    TextArea,
)

from swarmbridge.communities import MoltbookAdapter
from swarmbridge.mediator import GrokMediator, load_instructions
from swarmbridge.moltbook import (\n    MoltbookClient,\n    MoltbookError,\n    load_api_key,\n    save_api_key,\n)
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
#recipient { width: 1fr; min-width: 12; }
#composer-row Button { width: auto; min-width: 12; }
#community-search { width: 1fr; min-width: 12; }
#status { height: 2; color: #aab8d0; }
#contact-list, #draft-list { height: 1fr; min-height: 5; }
#instruction-editor { height: 1fr; }
#community-notes { height: 5; }
#community-output { height: 1fr; min-height: 5; border: round #263958; padding: 1; }
#post-content, #comment-content { height: 5; }
Input { margin-bottom: 1; }
Button { margin-right: 1; }
.primary { background: #1b806f; color: white; }
.warning { background: #7c4d20; color: white; }
ListView { background: #101a2e; }
ListItem.--highlight { background: #21435a; }
TextArea { background: #101a2e; border: round #304563; }
ConfirmRegistration { align: center middle; }
#confirm-box { width: 72; height: auto; max-height: 80%; border: thick #8fe8d1; background: #101a2e; padding: 2; }
#confirm-buttons { height: 3; align-horizontal: center; }
"""


class ConfirmRegistration(ModalScreen[bool]):
    """Explicit confirmation before the app creates an external community account."""

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label("CREATE A REAL MOLTBOOK AGENT?", classes="section-title")
            yield Static(
                "This sends the agent name and description to www.moltbook.com and may create "
                "a real account. The returned API key will be saved in your operating system's "
                "credential manager. Continue only if you want to register now."
            )
            with Horizontal(id="confirm-buttons"):
                yield Button("Create account", id="confirm-register", classes="warning")
                yield Button("Cancel", id="cancel-register")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-register":
            self.dismiss(True)
        elif event.button.id == "cancel-register":
            self.dismiss(False)


class ConfirmExternalAction(ModalScreen[bool]):
    """Explicit review gate for a public post or comment."""

    def __init__(self, title: str, details: str, action_label: str) -> None:
        super().__init__()
        self.confirm_title = title
        self.details = details
        self.action_label = action_label

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label(self.confirm_title, classes="section-title")
            yield Static(self.details, markup=False)
            yield Static("This will publish externally under your Moltbook agent identity.")
            with Horizontal(id="confirm-buttons"):
                yield Button(self.action_label, id="confirm-external", classes="warning")
                yield Button("Cancel", id="cancel-external")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-external":
            self.dismiss(True)
        elif event.button.id == "cancel-external":
            self.dismiss(False)


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
                yield Static("● HUMAN APPROVAL REQUIRED", id="lock-label")
            with Vertical(id="main"):
                with ContentSwitcher(initial="inbox-pane", id="workspace"):
                    with Vertical(id="inbox-pane"):
                        yield Label("MESSAGE STREAM", classes="section-title")
                        with VerticalScroll(id="thread"):
                            yield Static(
                                "Select a conversation or create a new one.\n\n"
                                "Public posts and comments require your explicit confirmation. Direct messages remain disabled.",
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
                            "READY  •  human approval required  •  " +
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
                    with VerticalScroll(id="communities-pane"):
                        yield Label("COMMUNITY ACCOUNTS", classes="section-title")
                        yield Static("Moltbook API calls use only the official www.moltbook.com host.")
                        yield Label("CREATE AN AGENT ACCOUNT", classes="section-title")
                        yield Input(placeholder="New Moltbook agent name", id="new-agent-name")
                        yield Input(placeholder="What this agent does", id="new-agent-description")
                        yield Button("Register new Moltbook agent…", id="register-agent", classes="warning")
                        yield Label("CONNECT AN EXISTING ACCOUNT", classes="section-title")
                        yield Input(placeholder="Moltbook API key (stored in OS credential manager)", id="moltbook-key", password=True)
                        yield Button("Validate & connect existing account", id="connect-agent", classes="primary")
                        yield Label("COMMUNITY ACTIVITY", classes="section-title")
                        with Horizontal():
                            yield Button("Load feed", id="load-feed")
                            yield Input(placeholder="Search Moltbook", id="community-search")
                            yield Button("Search", id="search-community")
                        yield Label("PUBLISH A PUBLIC POST", classes="section-title")
                        yield Input(placeholder="Post title", id="post-title")
                        yield Input(placeholder="Submolt (default: general)", id="post-submolt")
                        yield TextArea(id="post-content", soft_wrap=True)
                        yield Button("Review & publish post…", id="review-post", classes="warning")
                        yield Label("COMMENT ON A POST", classes="section-title")
                        yield Input(placeholder="Moltbook post ID", id="comment-post-id")
                        yield TextArea(id="comment-content", soft_wrap=True)
                        yield Button("Review & publish comment…", id="review-comment", classes="warning")
                        yield Static("Not connected. No community requests have been sent.", id="community-status")
                        yield Static("", id="community-output", markup=False)
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
        try:
            key = load_api_key()
            if key:
                self.query_one("#community-status", Static).update("Credential found. Use Load feed to connect.")
        except Exception:
            self.query_one("#community-status", Static).update(
                "OS credential manager unavailable. Connect an account after fixing keyring support."
            )

    async def refresh_all(self) -> None:
        await self.refresh_threads()
        await self.refresh_contacts()
        await self.refresh_drafts()

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
        elif action == "register-agent":
            if not self.query_one("#new-agent-name", Input).value.strip() or not self.query_one("#new-agent-description", Input).value.strip():
                self.notify("Enter both an agent name and description.", severity="warning")
                return
            self.push_screen(ConfirmRegistration(), self.finish_registration_confirmation)
        elif action == "connect-agent":
            await self.connect_existing_account()
        elif action == "load-feed":
            await self.load_community_feed()
        elif action == "search-community":
            await self.search_community()
        elif action == "review-post":
            title = self.query_one("#post-title", Input).value.strip()
            submolt = self.query_one("#post-submolt", Input).value.strip() or "general"
            body = self.query_one("#post-content", TextArea).text.strip()
            if not title or not body:
                self.notify("A public post needs both a title and content.", severity="warning")
                return
            self.pending_external_action = {"kind": "post", "title": title, "submolt": submolt, "content": body}
            self.push_screen(
                ConfirmExternalAction("PUBLISH THIS PUBLIC POST?", f"Submolt: {submolt}\nTitle: {title}\n\n{body[:700]}",
                                      "Publish post"),
                self.finish_external_confirmation,
            )
        elif action == "review-comment":
            post_id = self.query_one("#comment-post-id", Input).value.strip()
            body = self.query_one("#comment-content", TextArea).text.strip()
            if not post_id or not body:
                self.notify("A comment needs a post ID and comment text.", severity="warning")
                return
            self.pending_external_action = {"kind": "comment", "post_id": post_id, "content": body}
            self.push_screen(
                ConfirmExternalAction("PUBLISH THIS COMMENT?", f"Post ID: {post_id}\n\n{body[:700]}",
                                      "Publish comment"),
                self.finish_external_confirmation,
            )
        elif action == "save-instructions":
            content = self.query_one("#instruction-editor", TextArea).text
            self.instruction_path.write_text(content.rstrip() + "\n", encoding="utf-8")
            self.notify(f"Saved {self.instruction_path.resolve()}")
        elif action == "open-draft":
            draft = next((d for d in self.store.drafts() if d["id"] == self.selected_draft_id), None)
            if draft is None:
                self.notify("Select a draft first.", severity="warning")
                return
            self.query_one("#workspace", ContentSwitcher).current = "inbox-pane"
            self.query_one("#compose", TextArea).text = draft["body"]
            self.query_one("#recipient", Input).value = draft["recipient"]
            self.notify("Draft loaded. It has not been sent.")

    def finish_registration_confirmation(self, confirmed: bool | None) -> None:
        if confirmed:
            self.run_worker(self.register_agent(), exclusive=True)

    async def register_agent(self) -> None:
        name = self.query_one("#new-agent-name", Input).value.strip()
        description = self.query_one("#new-agent-description", Input).value.strip()
        output = self.query_one("#community-output", Static)
        output.update("Registering with Moltbook…")
        try:
            registration = await MoltbookClient().register_agent(name, description)
            try:
                save_api_key(registration.api_key)
                key_status = "API key saved to the operating system credential manager."
                key_notice = ""
            except Exception:
                key_status = "OS credential manager failed. Copy this key now and store it securely; it was not saved."
                key_notice = f"\nAPI KEY (shown once): {registration.api_key}"
            self.store.set_community_account(
                "Moltbook", registration.name,
                f"Claim URL: {registration.claim_url}\nVerification code: {registration.verification_code}\n{key_status}"
            )
            output.update(
                f"REGISTRATION RESPONSE\nAgent: {registration.name}\nClaim URL: {registration.claim_url}"
                f"\nVerification code: {registration.verification_code}\n{key_status}{key_notice}"
            )
            self.query_one("#community-status", Static).update("Registration response received. Complete Moltbook's claim/owner verification.")
            self.notify("Moltbook registration request completed. Review the claim instructions.")
        except Exception as exc:
            output.update(f"Registration failed: {exc}")
            self.notify(str(exc), title="MOLTBOOK REGISTRATION FAILED", severity="error")

    async def connect_existing_account(self) -> None:
        api_key = self.query_one("#moltbook-key", Input).value.strip()
        if not api_key:
            self.notify("Paste an existing Moltbook API key first.", severity="warning")
            return
        try:
            client = MoltbookClient(api_key)
            response = await client.me()
            data = response.get("data", response)
            agent = data.get("agent", data) if isinstance(data, dict) else {}
            name = str(agent.get("name", "Connected agent")) if isinstance(agent, dict) else "Connected agent"
            save_api_key(api_key)
            self.store.set_community_account("Moltbook", name, "API key validated and saved in OS credential manager.")
            self.query_one("#moltbook-key", Input).value = ""
            self.query_one("#community-status", Static).update(f"CONNECTED • {name} • key stored in OS credential manager")
            self.notify(f"Connected Moltbook account: {name}")
        except Exception as exc:
            self.notify(str(exc), title="MOLTBOOK CONNECTION FAILED", severity="error")

    def finish_external_confirmation(self, confirmed: bool | None) -> None:
        pending = getattr(self, "pending_external_action", None)
        self.pending_external_action = None
        if confirmed and pending:
            self.run_worker(self.perform_external_action(pending), exclusive=True)

    async def perform_external_action(self, action: dict) -> None:
        output = self.query_one("#community-output", Static)
        try:
            key = load_api_key()
            if not key:
                raise MoltbookError("Connect an account or register an agent first.")
            client = MoltbookClient(key)
            if action["kind"] == "post":
                response = await client.create_post(
                    title=action["title"], content=action["content"], submolt=action["submolt"]
                )
                self.query_one("#post-title", Input).value = ""
                self.query_one("#post-content", TextArea).text = ""
                result = response.get("data", response)
                output.update(f"Post published after confirmation.\n{result}")
            else:
                response = await client.comment(action["post_id"], action["content"])
                self.query_one("#comment-content", TextArea).text = ""
                result = response.get("data", response)
                output.update(f"Comment published after confirmation.\n{result}")
            self.query_one("#community-status", Static).update("External action completed • API success response received")
            self.notify("Moltbook confirmed the publication.")
        except Exception as exc:
            output.update(f"Publication failed: {exc}")
            self.notify(str(exc), title="MOLTBOOK PUBLICATION FAILED", severity="error")

    async def load_community_feed(self) -> None:
        output = self.query_one("#community-output", Static)
        try:
            key = load_api_key()
            if not key:
                raise MoltbookError("Connect an account or register an agent first.")
            response = await MoltbookClient(key).feed()
            data = response.get("data", response)
            posts = data.get("posts", []) if isinstance(data, dict) else []
            if not isinstance(posts, list):
                posts = []
            lines = []
            for post in posts[:30]:
                if not isinstance(post, dict):
                    continue
                author = post.get("author", {})
                author_name = author.get("name", "unknown") if isinstance(author, dict) else "unknown"
                lines.append(f"{post.get('title', '(untitled)')}\nby {author_name}\n{str(post.get('content', ''))[:220]}\n")
            output.update("\n".join(lines) if lines else "Feed loaded; no posts were returned in the expected format.")
            self.query_one("#community-status", Static).update(f"Feed request completed • {len(lines)} posts displayed • read-only")
        except Exception as exc:
            output.update(f"Feed unavailable: {exc}")
            self.notify(str(exc), title="MOLTBOOK FEED FAILED", severity="error")

    async def search_community(self) -> None:
        query = self.query_one("#community-search", Input).value.strip()
        output = self.query_one("#community-output", Static)
        try:
            key = load_api_key()
            if not key:
                raise MoltbookError("Connect an account or register an agent first.")
            response = await MoltbookClient(key).search(query)
            data = response.get("data", response)
            results = data.get("results", data.get("posts", [])) if isinstance(data, dict) else []
            if not isinstance(results, list):
                results = []
            lines = []
            for item in results[:30]:
                if not isinstance(item, dict):
                    continue
                title = item.get("title", item.get("name", "(result)"))
                body = item.get("content", item.get("description", ""))
                lines.append(f"{title}\n{str(body)[:220]}\n")
            output.update("\n".join(lines) if lines else "Search completed; no results in the expected format.")
            self.query_one("#community-status", Static).update(f"Search completed • {len(lines)} results displayed • read-only")
        except Exception as exc:
            output.update(f"Search unavailable: {exc}")
            self.notify(str(exc), title="MOLTBOOK SEARCH FAILED", severity="error")

    async def load_instruction_editor(self) -> None:
        self.query_one("#instruction-editor", TextArea).text = load_instructions(self.instruction_path)

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
                "READY  •  human approval required  •  " +
                ("Grok configured" if self.mediator.configured else "Grok not configured")
            )


def main() -> None:
    BridgeApp().run()
