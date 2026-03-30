"""
RMA (Return Merchandise Authorization) service interface.

Owns lifecycle state for authorized returns and warehouse coordination.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RmaCreateInput:
    """Data needed to open an RMA."""

    return_id: str
    order_id: str


@dataclass(frozen=True)
class RmaCreateOutput:
    """Created RMA identifiers."""

    rma_id: str
    status: str


class RmaService(Protocol):
    """
    Creates and updates RMA records.

    Expected behavior:
        - Persist or delegate persistence of RMA identifiers.
        - Emit events for warehouse and customer communications downstream.
    """

    def create_rma(self, data: RmaCreateInput) -> RmaCreateOutput:
        ...
