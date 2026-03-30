"""
Customer communication service interface (email/SMS/in-app).

Uses ``prompts.customer_communication_v1`` with ``AIClient`` when generating copy.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CommunicationInput:
    """Inputs for outbound customer messaging."""

    return_id: str
    template_key: str
    context: dict[str, str]


@dataclass(frozen=True)
class CommunicationOutput:
    """Result of a send or draft operation."""

    message_id: str | None
    body: str


class CommunicationService(Protocol):
    """
    Drafts or sends customer-facing messages for return outcomes.

    Expected behavior:
        - Respect policy and brand tone; no binding legal commitments in auto text.
        - Log correlation ids for support lookups.
    """

    def send_or_draft(self, data: CommunicationInput) -> CommunicationOutput:
        ...
