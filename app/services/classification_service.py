"""
Classification service interface: maps return reasons to categories and confidence.

Concrete keyword-based logic lives in ``classification.py`` until AI-backed
classification is wired through ``AIClient``.
"""

from dataclasses import dataclass
from typing import Protocol

from app.models.returns import ReturnRecord


@dataclass(frozen=True)
class ClassificationInput:
    """Input for reason classification."""

    record: ReturnRecord


@dataclass(frozen=True)
class ClassificationOutput:
    """Classifier output: canonical category and model confidence."""

    category: str
    confidence: float


class ClassificationService(Protocol):
    """
    Classifies return reasons for routing and scoring.

    Expected behavior:
        - Prefer structural signals (e.g. damaged flag) over text when applicable.
        - Return confidence in [0.0, 1.0].
        - Use a stable set of category strings agreed with scoring/routing.
    """

    def classify(self, data: ClassificationInput) -> ClassificationOutput:
        ...
