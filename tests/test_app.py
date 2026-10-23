from textual.widgets import Input, TextArea

from swarmbridge.app import BridgeApp
from swarmbridge.mediator import GrokMediator
from swarmbridge.store import Store


async def test_app_mounts_and_contact_can_be_added(tmp_path):
    store = Store(tmp_path / "app.sqlite3")
    app = BridgeApp(store=store, mediator=GrokMediator(api_key=""))
    app.instruction_path = tmp_path / "AGENTS.md"

    async with app.run_test(size=(120, 42)) as pilot:
        app.query_one("#contact-name", Input).value = "Agent North"
        app.query_one("#contact-community", Input).value = "Moltbook"
        app.query_one("#contact-handle", Input).value = "@north"
        await pilot.click("#add-contact")
        assert store.contacts()[0]["name"] == "Agent North"
        assert app.query_one("#workspace").current == "inbox-pane"
        await pilot.click("#nav-contacts")
        assert app.query_one("#workspace").current == "contacts-pane"


async def test_app_saves_draft_without_sending(tmp_path):
    store = Store(tmp_path / "app.sqlite3")
    app = BridgeApp(store=store, mediator=GrokMediator(api_key=""))
    app.instruction_path = tmp_path / "AGENTS.md"

    async with app.run_test(size=(120, 42)) as pilot:
        app.query_one("#compose", TextArea).text = "Human-reviewed message"
        app.query_one("#recipient", Input).value = "@agent"
        await pilot.click("#save-draft")
        assert store.drafts()[0]["body"] == "Human-reviewed message"
        assert store.drafts()[0]["approved"] == 0
        assert store.messages(store.conversations()[0]["id"])[0]["status"] == "draft"
