"""
Orchestrator: runs the full return processing pipeline in one call.

process_return(record) is the single entry point for all pipeline logic.
It is a pure function — no I/O, no side effects — so it is independently
testable without a database or HTTP layer.

Pipeline stages
---------------
ingestion       → already done by caller (ReturnRecord created from schema)
validation      → policy checks (window, product type)
classification  → reason category + confidence
scoring         → composite risk/confidence score
decision        → approved | rejected | manual_review
routing         → downstream team / system
"""

from dataclasses import dataclass

from app.models.returns import ReturnRecord
from app.services import classification as cls_svc
from app.services import decision as dec_svc
from app.services import routing as rte_svc
from app.services import scoring as scr_svc
from app.services import validation as val_svc
from app.services.classification import ClassificationResult
from app.services.decision import DecisionResult
from app.services.scoring import ScoreResult
from app.services.validation import ValidationResult


@dataclass
class PipelineResult:
    """Full output of the return processing pipeline."""

    validation: ValidationResult
    classification: ClassificationResult
    score: ScoreResult
    decision: DecisionResult
    routing_outcome: str


def process_return(record: ReturnRecord) -> PipelineResult:
    """
    Execute the complete return processing pipeline.

    Args:
        record: A ReturnRecord populated by the ingestion layer.
                Decision/routing fields are NOT yet set on this object —
                the caller is responsible for applying the result.

    Returns:
        PipelineResult containing each stage's output.
    """
    validation = val_svc.validate(record)
    classification = cls_svc.classify(record)
    score = scr_svc.score(record, validation, classification)
    decision = dec_svc.decide(record, validation, score)
    routing_outcome = rte_svc.route(record, classification, decision)

    return PipelineResult(
        validation=validation,
        classification=classification,
        score=score,
        decision=decision,
        routing_outcome=routing_outcome,
    )
