# ADR 0002: Fraud scoring design

## Status

Accepted

## Context

We need a **repeatable** fraud signal for observability and queue risk that does not depend on opaque model scores for compliance. Inputs should be explainable (flags, thresholds) and tunable per environment.

## Decision

- Fraud is scored in `app/services/fraud_service.py` using **only** structured history: return frequency, aggregate and average order value, and recency within a sliding window (`fraud_window_days`).
- Weights and thresholds are **configuration** (`Settings`): frequency / value / recency weights, medium/high risk cutoffs, and `fraud_flagged_processing_threshold` for metrics.
- **No LLM** in the fraud path; `customer_id` is keyed by email or `"anonymous"` when absent.

## Consequences

**Positive:** Same history + clock → same score; easy to unit test and to extend with new flags.  
**Negative:** Does not use graph/network fraud signals; must be extended deliberately if product requirements grow.
