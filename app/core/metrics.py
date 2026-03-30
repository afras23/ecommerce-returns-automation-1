"""
In-process metrics: decisions, observability (processing time, fraud flags, throughput).
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


class ObservabilityMetrics:
    """Counters for pipeline throughput, fraud flag rate, and latency averages."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.returns_processed_total = 0
        self.fraud_flagged_total = 0
        self._processing_ms_sum = 0.0
        self._processing_ms_count = 0

    def record_processing(
        self,
        *,
        processing_time_ms: float,
        fraud_score: float | None,
        fraud_flag_threshold: float,
    ) -> None:
        with self._lock:
            self.returns_processed_total += 1
            self._processing_ms_sum += processing_time_ms
            self._processing_ms_count += 1
            if fraud_score is not None and fraud_score >= fraud_flag_threshold:
                self.fraud_flagged_total += 1

    def snapshot(self) -> dict:
        with self._lock:
            avg_ms = (
                round(self._processing_ms_sum / self._processing_ms_count, 3)
                if self._processing_ms_count
                else 0.0
            )
            fraud_pct = (
                round(self.fraud_flagged_total / self.returns_processed_total, 4)
                if self.returns_processed_total
                else 0.0
            )
            return {
                "returns_processed_total": self.returns_processed_total,
                "fraud_flagged_total": self.fraud_flagged_total,
                "fraud_flagged_pct": fraud_pct,
                "avg_processing_time_ms": avg_ms,
            }

    def reset(self) -> None:
        with self._lock:
            self.returns_processed_total = 0
            self.fraud_flagged_total = 0
            self._processing_ms_sum = 0.0
            self._processing_ms_count = 0


metrics = DecisionMetrics()
observability_metrics = ObservabilityMetrics()


def combined_metrics_snapshot() -> dict:
    """Merge decision and observability counters for /metrics."""
    out = metrics.snapshot()
    out.update(observability_metrics.snapshot())
    return out
