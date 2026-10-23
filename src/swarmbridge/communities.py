"""Community adapter contracts and capability-safe initial directory."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CommunityStatus:
    name: str
    status: str
    can_read: bool = False
    can_send: bool = False
    can_create_account: bool = False
    detail: str = ""


class CommunityAdapter:
    """Interface for future adapters. No network side effects are implemented in MVP."""

    name = "Community"

    def status(self) -> CommunityStatus:
        return CommunityStatus(self.name, "scaffold", detail="Adapter not yet connected.")


class MoltbookAdapter(CommunityAdapter):
    name = "Moltbook"

    def status(self) -> CommunityStatus:
        return CommunityStatus(
            name=self.name,
            status="scaffold",
            detail=(
                "Not connected. Verify the current official API, identity, rate limits, "
                "and account-creation flow before enabling any actions."
            ),
        )
