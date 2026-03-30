"""
Fraud and abuse detection service interface.

Future implementation will combine signals (history, velocity, AI flags).
"""

from dataclasses import dataclass
from typing import Protocol

from app.models.returns import ReturnRecord


@dataclass(frozen=True)
class FraudAssessmentInput:
    """Context for fraud scoring."""

    record: ReturnRecord


@dataclass(frozen=True)
class FraudAssessmentOutput:
    """Risk bucket and optional reasons for review."""

    risk_tier: str  # low | medium | high
    reasons: tuple[str, ...]


class FraudService(Protocol):
    """
    Evaluates fraud and abuse risk for a return.

    Expected behavior:
        - Deterministic or explainable scores suitable for audit.
        - Escalate ambiguous cases to higher tiers rather than silent approval.
    """

    def assess(self, data: FraudAssessmentInput) -> FraudAssessmentOutput:
        ...
