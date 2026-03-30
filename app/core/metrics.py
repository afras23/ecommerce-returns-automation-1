"""
In-process counters for return decision outcomes (approval / rejection / manual review).
"""

from threading import Lock


class DecisionMetrics:
    """In-process counters for return decision outcomes."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.total = 0
        self.approved = 0
        self.rejected = 0
        self.manual_review = 0

    def record(self, decision: str) -> None:
        with self._lock:
            self.total += 1
            if decision == "approved":
                self.approved += 1
            elif decision == "rejected":
                self.rejected += 1
            elif decision == "manual_review":
                self.manual_review += 1

    def snapshot(self) -> dict:
        with self._lock:
            if self.total == 0:
                return {
                    "total": 0,
                    "approval_rate": 0.0,
                    "rejection_rate": 0.0,
                    "manual_review_rate": 0.0,
                }
            return {
                "total": self.total,
                "approved": self.approved,
                "rejected": self.rejected,
                "manual_review": self.manual_review,
                "approval_rate": round(self.approved / self.total, 4),
                "rejection_rate": round(self.rejected / self.total, 4),
                "manual_review_rate": round(self.manual_review / self.total, 4),
            }

    def reset(self) -> None:
        with self._lock:
            self.total = 0
            self.approved = 0
            self.rejected = 0
            self.manual_review = 0


# Module-level singleton
metrics = DecisionMetrics()
