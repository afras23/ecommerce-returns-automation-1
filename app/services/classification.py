"""
Classification: categorises the return reason into a canonical label.
Operates on free-text reason + structured damaged flag.
"""

from app.models.returns import ReturnRecord

_REASON_KEYWORDS: dict[str, list[str]] = {
    "damaged":          ["damaged", "broken", "defective", "cracked", "torn", "faulty", "shattered"],
    "wrong_item":       ["wrong item", "wrong product", "incorrect item", "not what i ordered", "not what was ordered"],
    "not_as_described": ["not as described", "different from", "misleading", "inaccurate description"],
    "sizing":           ["too big", "too small", "wrong size", "doesn't fit", "does not fit"],
    "changed_mind":     ["changed my mind", "no longer need", "don't want", "don't need", "no longer want"],
}


def classify(record: ReturnRecord) -> str:
    # Structural flag takes priority over free-text
    if record.damaged:
        return "damaged"

    reason_lower = record.reason.lower()
    for category, keywords in _REASON_KEYWORDS.items():
        if any(kw in reason_lower for kw in keywords):
            return category

    return "other"
