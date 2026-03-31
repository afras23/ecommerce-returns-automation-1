# ADR 0001: AI vs rule-based refund calculation

## Status

Accepted

## Context

Return processing must compute **refund amounts** that are auditable, dispute-resistant, and identical for the same inputs (regression-testable). LLMs can paraphrase customer communications and assist classification, but they are poor choices for **monetary policy** because outputs can drift, hallucinate dollar figures, and are hard to certify for finance.

## Decision

- **Refund dollar amounts** are computed **only** by deterministic rules in `app/services/refund_service.py`: product condition → percentage, optional restocking fee from config, fixed rounding.
- **AI** is used for optional **customer communications** (`communication_service.py`) with explicit FACTS blocks so amounts are injected by the caller, not invented by the model.
- **Approval / routing** uses a **hybrid**: keyword classification + composite score + hard rules (`validation`, `decision`), not an LLM judge for money.

## Consequences

**Positive:** Refunds match policy tables; golden tests and `eval/test_set.jsonl` can assert exact amounts.  
**Negative:** Condition must be supplied or derived outside the refund engine (e.g. default condition in pipeline); changing policy requires code or config changes, not prompt edits.
