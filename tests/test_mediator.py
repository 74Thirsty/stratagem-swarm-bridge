import pytest

from swarmbridge import mediator
from swarmbridge.communities import MoltbookAdapter
from swarmbridge.mediator import DEFAULT_INSTRUCTIONS, GrokMediator, load_instructions


def test_missing_key_fails_closed():
    model = GrokMediator(api_key="")
    assert model.configured is False


def test_instruction_loader_reads_custom_file(tmp_path):
    instructions = tmp_path / "AGENTS.md"
    instructions.write_text("Only draft; never send.", encoding="utf-8")
    assert load_instructions(instructions) == "Only draft; never send."
    assert "single communications mediator" in DEFAULT_INSTRUCTIONS


def test_instruction_loader_uses_safe_defaults_for_missing_file(tmp_path):
    assert load_instructions(tmp_path / "missing.md") == DEFAULT_INSTRUCTIONS


def test_moltbook_is_scaffolded_without_network_capabilities():
    status = MoltbookAdapter().status()
    assert status.status == "scaffold"
    assert status.can_read is False
    assert status.can_send is False
    assert status.can_create_account is False


@pytest.mark.asyncio
async def test_grok_draft_uses_configured_model_and_never_has_send_tool(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "A reviewed reply."}}]}

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers, json):
            captured.update(url=url, headers=headers, payload=json)
            return FakeResponse()

    monkeypatch.setattr(mediator.httpx, "AsyncClient", FakeClient)
    model = GrokMediator(api_key="test-key", model="test-model")
    result = await model.draft("Agent message", context="Earlier context", instructions="Draft only.")

    assert result == "A reviewed reply."
    assert captured["url"] == "https://api.x.ai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["messages"][0]["content"] == "Draft only."
    assert "Earlier context" in captured["payload"]["messages"][1]["content"]
