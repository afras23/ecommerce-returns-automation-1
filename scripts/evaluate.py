#!/usr/bin/env python3
"""
Offline evaluation: compare golden JSONL expectations against deterministic services.

Metrics: classification category, fraud risk level, refund amount (per-field + overall).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.models.returns import ReturnRecord
from app.services.classification import classify
from app.services.fraud_service import (
    FraudAssessmentInput,
    ReturnHistoryEntry,
    assess_fraud,
)
from app.services.product_condition_service import ProductCondition
from app.services.refund_service import RefundComputationInput, compute_refund


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _record_from_row(record: dict[str, Any]) -> ReturnRecord:
    return ReturnRecord(
        id=record.get("id", "00000000-0000-0000-0000-000000000001"),
        order_id=record["order_id"],
        customer_email=record.get("customer_email"),
        reason=record["reason"],
        preference=record.get("preference", "refund"),
        purchase_date=record.get("purchase_date", "2026-03-01"),
        order_amount=record.get("order_amount"),
        damaged=record.get("damaged", False),
        product_type=record.get("product_type"),
        product_id=record.get("product_id"),
        customer_segment=record.get("customer_segment"),
    )


def _settings_for_row(row: dict[str, Any]) -> Settings:
    base = Settings()
    overrides = row.get("settings_overrides") or {}
    if not overrides:
        return base
    return base.model_copy(update=overrides)


def _run_fraud(record: ReturnRecord, fraud_ctx: dict[str, Any], settings: Settings) -> Any:
    now = _parse_dt(fraud_ctx["now"])
    history: list[ReturnHistoryEntry] = []
    for h in fraud_ctx.get("history", []):
        history.append(
            ReturnHistoryEntry(
                return_id=h["return_id"],
                order_amount=float(h["order_amount"]),
                created_at=_parse_dt(h["created_at"]),
            )
        )
    cust = record.customer_email or "anonymous"
    return assess_fraud(
        FraudAssessmentInput(customer_id=cust, return_history=tuple(history)),
        settings=settings,
        now=now,
    )


def _run_refund(
    record: ReturnRecord,
    refund_spec: dict[str, Any],
    settings: Settings,
) -> float:
    cond = ProductCondition(refund_spec["condition"])
    amt = float(record.order_amount or 0.0)
    out = compute_refund(
        RefundComputationInput(order_amount=amt, condition=cond),
        settings=settings,
    )
    return float(out.refund_amount)


def evaluate_row(row: dict[str, Any]) -> dict[str, Any]:
    settings = _settings_for_row(row)
    rec = _record_from_row(row["record"])
    cls = classify(rec)
    fraud = _run_fraud(rec, row["fraud_context"], settings)
    refund_amt = _run_refund(rec, row["refund"], settings)
    return {
        "classification_category": cls.category,
        "classification_confidence": cls.confidence,
        "fraud_score": fraud.fraud_score,
        "fraud_risk_level": fraud.risk_level,
        "fraud_flags": sorted(fraud.flags),
        "refund_amount": round(refund_amt, 2),
    }


def _close(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


@dataclass
class FieldResult:
    name: str
    correct: int
    total: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


def main() -> int:
    _root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Evaluate golden JSONL against services.")
    parser.add_argument(
        "--jsonl",
        type=Path,
        default=_root / "eval" / "test_set.jsonl",
        help="Path to JSONL test set",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=_root / "eval" / "report.json",
        help="Where to write JSON report",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-case actual vs expected",
    )
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    with open(args.jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))

    failures: list[dict[str, Any]] = []
    fc_cls = FieldResult("classification_category", 0, len(rows))
    fc_fraud = FieldResult("fraud_risk_level", 0, len(rows))
    fc_refund = FieldResult("refund_amount", 0, len(rows))
    all_pass = 0

    settings_fp = Settings().model_dump()

    for row in rows:
        case_id = row.get("id", "?")
        exp = row["expected"]
        actual = evaluate_row(row)

        cls_ok = actual["classification_category"] == exp["classification_category"]
        fraud_ok = actual["fraud_risk_level"] == exp["fraud_risk_level"]
        refund_ok = _close(actual["refund_amount"], float(exp["refund_amount"]))

        if cls_ok:
            fc_cls.correct += 1
        if fraud_ok:
            fc_fraud.correct += 1
        if refund_ok:
            fc_refund.correct += 1

        if cls_ok and fraud_ok and refund_ok:
            all_pass += 1
        else:
            failures.append(
                {
                    "id": case_id,
                    "description": row.get("description"),
                    "expected": {
                        "classification_category": exp["classification_category"],
                        "fraud_risk_level": exp["fraud_risk_level"],
                        "refund_amount": exp["refund_amount"],
                    },
                    "actual": {
                        "classification_category": actual["classification_category"],
                        "fraud_risk_level": actual["fraud_risk_level"],
                        "refund_amount": actual["refund_amount"],
                    },
                    "miss": [
                        m
                        for m, ok in (
                            ("classification", cls_ok),
                            ("fraud_risk_level", fraud_ok),
                            ("refund_amount", refund_ok),
                        )
                        if not ok
                    ],
                }
            )

        if args.verbose:
            ac = actual["classification_category"]
            fr = actual["fraud_risk_level"]
            ra = actual["refund_amount"]
            print(f"[{case_id}] cls={ac} fraud={fr} refund={ra}")

    total = len(rows)
    overall = all_pass / total if total else 0.0

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "jsonl": str(args.jsonl.resolve()),
        "settings_fingerprint": settings_fp,
        "summary": {
            "total_cases": total,
            "overall_pass_rate": round(overall, 6),
            "overall_pass_percent": round(overall * 100, 4),
            "classification_accuracy": round(fc_cls.accuracy, 6),
            "classification_accuracy_percent": round(fc_cls.accuracy * 100, 4),
            "fraud_detection_consistency": round(fc_fraud.accuracy, 6),
            "fraud_detection_consistency_percent": round(fc_fraud.accuracy * 100, 4),
            "refund_correctness": round(fc_refund.accuracy, 6),
            "refund_correctness_percent": round(fc_refund.accuracy * 100, 4),
        },
        "per_field": {
            "classification_category": {
                "correct": fc_cls.correct,
                "total": fc_cls.total,
                "accuracy": round(fc_cls.accuracy, 6),
                "accuracy_percent": round(fc_cls.accuracy * 100, 4),
            },
            "fraud_risk_level": {
                "correct": fc_fraud.correct,
                "total": fc_fraud.total,
                "accuracy": round(fc_fraud.accuracy, 6),
                "accuracy_percent": round(fc_fraud.accuracy * 100, 4),
            },
            "refund_amount": {
                "correct": fc_refund.correct,
                "total": fc_refund.total,
                "accuracy": round(fc_refund.accuracy, 6),
                "accuracy_percent": round(fc_refund.accuracy * 100, 4),
            },
        },
        "failures": failures,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as rf:
        json.dump(report, rf, indent=2)
        rf.write("\n")

    # Console summary
    s = report["summary"]
    pf = report["per_field"]
    print("Evaluation complete")
    print(f"  Cases:              {total}")
    print(f"  Overall pass rate:  {s['overall_pass_percent']:.2f}% ({all_pass}/{total})")
    print(f"  Classification:     {pf['classification_category']['accuracy_percent']:.2f}%")
    print(f"  Fraud risk level:   {pf['fraud_risk_level']['accuracy_percent']:.2f}%")
    print(f"  Refund amount:      {pf['refund_amount']['accuracy_percent']:.2f}%")
    print(f"  Report written:     {args.report.resolve()}")
    if failures:
        print(f"\nFailure cases ({len(failures)}):")
        for f in failures:
            print(f"  - {f['id']}: {f['miss']} — {f.get('description', '')}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
