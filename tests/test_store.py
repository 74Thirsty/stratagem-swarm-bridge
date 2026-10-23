from swarmbridge.store import Store


def test_store_persists_contacts_conversations_messages_and_drafts(tmp_path):
    store = Store(tmp_path / "test.sqlite3")
    contact_id = store.add_contact("Agent Alpha", "Moltbook", "@alpha")
    conversation_id = store.create_conversation("Test thread", "Moltbook", contact_id)
    store.add_message(conversation_id, "inbound", "Hello from the agent")
    store.save_draft("A human-reviewed reply", "@alpha", "Moltbook", conversation_id)

    assert store.contacts()[0]["name"] == "Agent Alpha"
    assert store.conversations()[0]["title"] == "Test thread"
    assert store.messages(conversation_id)[0]["body"] == "Hello from the agent"
    assert store.drafts()[0]["approved"] == 0
    assert store.communities()[0]["name"] == "Moltbook"


def test_store_rejects_invalid_or_empty_messages_and_contacts(tmp_path):
    store = Store(tmp_path / "test.sqlite3")
    conversation_id = store.create_conversation("Safe thread")
    for direction, body in [("send", "not allowed"), ("note", "   ")]:
        try:
            store.add_message(conversation_id, direction, body)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid message was accepted")
    try:
        store.add_contact("  ")
    except ValueError:
        pass
    else:
        raise AssertionError("empty contact name was accepted")


def test_community_account_notes_are_local_and_require_known_community(tmp_path):
    store = Store(tmp_path / "test.sqlite3")
    store.set_community_account("Moltbook", "@local-agent", "not connected")
    row = store.communities()[0]
    assert row["account_name"] == "@local-agent"
    assert row["notes"] == "not connected"
    try:
        store.set_community_account("Unknown", "x")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown community was silently accepted")


# Mediator tests live here for now so the suite also verifies the local-first boundary.
import pytest

from swarmbridge.mediator import DEFAULT_INSTRUCTIONS, GrokMediator, load_instructions


@pytest.mark.asyncio
async def test_grok_draft_uses_configured_model_and_returns_reviewable_text(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            captured["status_checked"] = True

        def json(self):
            return {"choices": [{"message": {"content": "A reviewed draft."}}]}

    class FakeClient:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, *, headers, json):
            captured.update(url=url, headers=headers, json=json)
            return Response()

    monkeypatch.setattr("swarmbridge.mediator.httpx.AsyncClient", FakeClient)
    result = await GrokMediator(api_key="test-key", model="test-model").draft(
        "Draft a reply", context="Prior message", instructions="Be concise."
    )

    assert result == "A reviewed draft."
    assert captured["status_checked"] is True
    assert captured["url"] == "https://api.x.ai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["messages"][0]["content"] == "Be concise."
    assert "Prior message" in captured["json"]["messages"][1]["content"]


@pytest.mark.asyncio
async def test_grok_without_key_fails_before_network(monkeypatch):
    def forbidden_client(*args, **kwargs):
        raise AssertionError("network must not be touched without a key")

    monkeypatch.setattr("swarmbridge.mediator.httpx.AsyncClient", forbidden_client)
    with pytest.raises(RuntimeError, match="XAI_API_KEY"):
        await GrokMediator(api_key="").draft("Hello")


@pytest.mark.asyncio
async def test_grok_malformed_response_fails_closed(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": []}

    class FakeClient:
        def __init__(self, *, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr("swarmbridge.mediator.httpx.AsyncClient", FakeClient)
    with pytest.raises(RuntimeError, match="unexpected response shape"):
        await GrokMediator(api_key="test-key").draft("Hello")


def test_instruction_loader_reads_custom_file_and_uses_safe_default(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text("Use a concise tone.", encoding="utf-8")

    assert load_instructions(path) == "Use a concise tone."
    assert load_instructions(tmp_path / "missing.md") == DEFAULT_INSTRUCTIONS
