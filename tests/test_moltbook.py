import pytest

from swarmbridge import moltbook
from swarmbridge.moltbook import MoltbookClient, MoltbookError, Registration


class FakeResponse:
    def __init__(self, payload, status_code=200, is_redirect=False):
        self._payload = payload
        self.status_code = status_code
        self.is_redirect = is_redirect

    def json(self):
        return self._payload


class FakeClient:
    calls = []
    response = FakeResponse({"success": True, "data": {"posts": []}})

    def __init__(self, *, base_url, timeout, follow_redirects):
        self.base_url = str(base_url)
        self.timeout = timeout
        self.follow_redirects = follow_redirects

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, method, path, **kwargs):
        self.calls.append({
            "base_url": self.base_url,
            "method": method,
            "path": path,
            "kwargs": kwargs,
            "follow_redirects": self.follow_redirects,
        })
        return self.response


@pytest.mark.asyncio
async def test_registration_uses_fixed_official_host_and_does_not_send_auth(monkeypatch):
    FakeClient.calls = []
    FakeClient.response = FakeResponse({
        "success": True,
        "data": {"agent": {
            "name": "BridgeAgent",
            "api_key": "moltbook_secret",
            "claim_url": "https://www.moltbook.com/claim/example",
            "verification_code": "reef-1234",
        }},
    })
    monkeypatch.setattr(moltbook.httpx, "AsyncClient", FakeClient)

    result = await MoltbookClient().register_agent("BridgeAgent", "A mediator agent.")

    assert isinstance(result, Registration)
    assert result.api_key == "moltbook_secret"
    call = FakeClient.calls[0]
    assert call["base_url"] == "https://www.moltbook.com/api/v1"
    assert call["method"] == "POST"
    assert call["path"] == "/agents/register"
    assert call["follow_redirects"] is False
    assert "Authorization" not in call["kwargs"]["headers"]


@pytest.mark.asyncio
async def test_authenticated_requests_only_use_fixed_host_and_bearer_key(monkeypatch):
    FakeClient.calls = []
    FakeClient.response = FakeResponse({"success": True, "data": {"posts": []}})
    monkeypatch.setattr(moltbook.httpx, "AsyncClient", FakeClient)

    await MoltbookClient("moltbook_secret").feed()
    call = FakeClient.calls[0]
    assert call["base_url"] == "https://www.moltbook.com/api/v1"
    assert call["kwargs"]["headers"]["Authorization"] == "Bearer moltbook_secret"
    assert call["kwargs"]["params"]["limit"] == 20


@pytest.mark.asyncio
async def test_redirect_is_rejected_and_not_followed(monkeypatch):
    FakeClient.calls = []
    FakeClient.response = FakeResponse({}, status_code=302, is_redirect=True)
    monkeypatch.setattr(moltbook.httpx, "AsyncClient", FakeClient)

    with pytest.raises(MoltbookError, match="redirect"):
        await MoltbookClient("secret").me()
    assert FakeClient.calls[0]["follow_redirects"] is False


@pytest.mark.asyncio
async def test_missing_registration_key_is_not_accepted(monkeypatch):
    FakeClient.response = FakeResponse({"success": True, "data": {"agent": {"name": "NoKey"}}})
    monkeypatch.setattr(moltbook.httpx, "AsyncClient", FakeClient)

    with pytest.raises(MoltbookError, match="did not include an API key"):
        await MoltbookClient().register_agent("NoKey", "Missing key case")


@pytest.mark.asyncio
async def test_missing_credentials_fail_before_network():
    with pytest.raises(MoltbookError, match="No Moltbook API key"):
        await MoltbookClient().me()


def test_credential_manager_helpers_do_not_write_database(monkeypatch):
    values = {}
    class FakeKeyring:
        @staticmethod
        def set_password(service, username, password):
            values[(service, username)] = password

        @staticmethod
        def get_password(service, username):
            return values.get((service, username))

    import sys
    monkeypatch.setitem(sys.modules, "keyring", FakeKeyring)
    moltbook.save_api_key("secret-key")
    assert moltbook.load_api_key() == "secret-key"
    assert values == {("stratagem-swarm-bridge", "moltbook"): "secret-key"}



@pytest.mark.asyncio
async def test_public_post_and_comment_use_documented_paths_and_payloads(monkeypatch):
    FakeClient.calls = []
    FakeClient.response = FakeResponse({"success": True, "data": {"id": "post-123"}})
    monkeypatch.setattr(moltbook.httpx, "AsyncClient", FakeClient)
    client = MoltbookClient("moltbook_secret")

    await client.create_post(title="Hello", content="A reviewed post", submolt="general")
    await client.comment("post-123", "A reviewed comment")

    post_call, comment_call = FakeClient.calls
    assert post_call["path"] == "/posts"
    assert post_call["method"] == "POST"
    assert post_call["kwargs"]["json"] == {
        "title": "Hello", "content": "A reviewed post", "submolt": "general"
    }
    assert comment_call["path"] == "/posts/post-123/comments"
    assert comment_call["kwargs"]["json"] == {"content": "A reviewed comment"}
    assert all(call["base_url"] == "https://www.moltbook.com/api/v1" for call in FakeClient.calls)


@pytest.mark.asyncio
async def test_comment_rejects_path_injection_before_network(monkeypatch):
    FakeClient.calls = []
    monkeypatch.setattr(moltbook.httpx, "AsyncClient", FakeClient)
    with pytest.raises(ValueError, match="unsupported characters"):
        await MoltbookClient("secret").comment("../agents/me", "Nope")
    assert FakeClient.calls == []
