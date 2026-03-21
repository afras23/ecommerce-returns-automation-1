"""
Classification: categorises the return reason and assigns a confidence score.

Confidence reflects how clearly the reason maps to the category — a strong
keyword match with structural signals scores higher than a weak keyword match.
"""

from dataclasses import dataclass

from app.models.returns import ReturnRecord

# (keyword, confidence) pairs per category — order within each list matters
# because we take the highest-confidence match, not the first match.
_KEYWORDS: dict[str, list[tuple[str, float]]] = {
    "damaged": [
        ("arrived damaged", 0.95),
        ("shattered", 0.95),
        ("broken beyond repair", 0.95),
        ("broken", 0.85),
        ("damaged", 0.85),
        ("defective", 0.85),
        ("cracked", 0.80),
        ("torn", 0.80),
        ("faulty", 0.80),
    ],
    "wrong_item": [
        ("wrong item", 0.95),
        ("wrong product", 0.95),
        ("incorrect item", 0.90),
        ("not what i ordered", 0.90),
        ("not what was ordered", 0.90),
    ],
    "not_as_described": [
        ("not as described", 0.90),
        ("misleading description", 0.85),
        ("inaccurate description", 0.85),
        ("different from the description", 0.85),
        ("different from", 0.70),
        ("not what was advertised", 0.80),
    ],
    "sizing": [
        ("wrong size", 0.90),
        ("doesn't fit", 0.85),
        ("does not fit", 0.85),
        ("too big", 0.85),
        ("too small", 0.85),
        ("too large", 0.85),
        ("too tight", 0.85),
        ("too loose", 0.85),
    ],
    "buyer_remorse": [
        ("ordered by mistake", 0.90),
        ("bought by mistake", 0.90),
        ("accidental purchase", 0.90),
        ("purchased accidentally", 0.85),
        ("changed my mind", 0.85),
        ("no longer need", 0.85),
        ("no longer want", 0.80),
        ("don't want", 0.75),
        ("don't need", 0.75),
    ],
}

_OTHER_CONFIDENCE = 0.30


@dataclass
class ClassificationResult:
    category: str   # damaged | wrong_item | not_as_described | sizing | buyer_remorse | other
    confidence: float  # 0.0 – 1.0


def classify(record: ReturnRecord) -> ClassificationResult:
    """
    Classify a return reason into a canonical category with confidence.

    The structural `damaged` flag takes priority over free-text matching
    and is treated as high-confidence evidence of a damage claim.

    Args:
        record: The return record whose reason field will be classified.

    Returns:
        ClassificationResult with the best-matching category and its confidence.
    """
    if record.damaged:
        return ClassificationResult(category="damaged", confidence=0.95)

    reason_lower = record.reason.lower()

    best_category = "other"
    best_confidence = _OTHER_CONFIDENCE

    for category, keyword_list in _KEYWORDS.items():
        for keyword, confidence in keyword_list:
            if keyword in reason_lower and confidence > best_confidence:
                best_category = category
                best_confidence = confidence

    return ClassificationResult(category=best_category, confidence=best_confidence)
