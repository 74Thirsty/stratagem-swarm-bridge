"""Moltbook's documented API client. Credentials never enter SQLite or other hosts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import httpx

BASE_URL = "https://www.moltbook.com/api/v1"
KEYRING_SERVICE = "stratagem-swarm-bridge"
KEYRING_USERNAME = "moltbook"


class MoltbookError(RuntimeError):
    """Safe-to-display community API error."""


@dataclass(frozen=True)
class Registration:
    name: str
    api_key: str
    claim_url: str
    verification_code: str


class MoltbookClient:
    """Narrow API wrapper using a fixed official host and bounded timeouts."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key.strip()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def _request(self, method: str, path: str, *, json: dict | None = None,
                       params: dict | None = None, authenticated: bool = True) -> dict[str, Any]:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("API path must be a local path")
        if authenticated and not self.api_key:
            raise MoltbookError("No Moltbook API key is configured.")
        headers = self._headers() if authenticated else {}
        try:
            async with httpx.AsyncClient(
                base_url=BASE_URL, timeout=httpx.Timeout(20.0), follow_redirects=False
            ) as client:
                response = await client.request(method, path, headers=headers, json=json, params=params)
        except httpx.HTTPError as exc:
            raise MoltbookError(f"Moltbook request failed ({type(exc).__name__}).") from None
        if response.is_redirect:
            raise MoltbookError("Moltbook returned a redirect; it was not followed to protect credentials.")
        if response.status_code >= 400:
            # Do not include response bodies or headers: they may contain private account data.
            raise MoltbookError(f"Moltbook returned HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError:
            raise MoltbookError("Moltbook returned a non-JSON response.") from None
        if not isinstance(payload, dict):
            raise MoltbookError("Moltbook returned an unexpected response shape.")
        if payload.get("success") is False:
            message = payload.get("error")
            safe_message = str(message)[:180] if isinstance(message, str) else "request rejected"
            raise MoltbookError(f"Moltbook rejected the request: {safe_message}")
        return payload

    async def register_agent(self, name: str, description: str) -> Registration:
        clean_name, clean_description = name.strip(), description.strip()
        if not clean_name or not clean_description:
            raise ValueError("Agent name and description are required.")
        payload = await self._request(
            "POST", "/agents/register",
            json={"name": clean_name, "description": clean_description},
            authenticated=False,
        )
        data = payload.get("data", payload)
        agent = data.get("agent", data) if isinstance(data, dict) else {}
        key = agent.get("api_key") if isinstance(agent, dict) else None
        if not isinstance(key, str) or not key:
            raise MoltbookError("Registration response did not include an API key; no account was saved locally.")
        return Registration(
            name=clean_name,
            api_key=key,
            claim_url=str(agent.get("claim_url", "")),
            verification_code=str(agent.get("verification_code", "")),
        )

    async def me(self) -> dict[str, Any]:
        return await self._request("GET", "/agents/me")

    async def status(self) -> dict[str, Any]:
        return await self._request("GET", "/agents/status")

    async def create_post(self, *, title: str, content: str, submolt: str = "general") -> dict[str, Any]:
        clean_title, clean_content, clean_submolt = title.strip(), content.strip(), submolt.strip()
        if not clean_title or not clean_content or not clean_submolt:
            raise ValueError("Post title, content, and submolt are required.")
        return await self._request(
            "POST", "/posts",
            json={"title": clean_title, "content": clean_content, "submolt": clean_submolt},
        )

    async def comment(self, post_id: str, content: str) -> dict[str, Any]:
        import re
        clean_id, clean_content = post_id.strip(), content.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", clean_id):
            raise ValueError("Post ID contains unsupported characters.")
        if not clean_content:
            raise ValueError("Comment text cannot be empty.")
        return await self._request(
            "POST", f"/posts/{clean_id}/comments", json={"content": clean_content}
        )

    async def feed(self, limit: int = 20) -> dict[str, Any]:
        return await self._request("GET", "/feed", params={"limit": max(1, min(limit, 50))})

    async def search(self, query: str, limit: int = 20) -> dict[str, Any]:
        if not query.strip():
            raise ValueError("Search query cannot be empty.")
        return await self._request(
            "GET", "/search", params={"q": query.strip(), "limit": max(1, min(limit, 50))}
        )


def save_api_key(api_key: str) -> None:
    """Store the API key in the OS credential manager, never in the project database."""
    import keyring
    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, api_key)


def load_api_key() -> str:
    import keyring
    return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) or ""
