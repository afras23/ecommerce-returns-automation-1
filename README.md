# Returns Processing System

An internal backend system for automating ecommerce returns decisions.

Replaces manual triage with a deterministic pipeline that validates, classifies, scores, and routes return requests — with a full audit trail for every decision.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Problem Context](#2-problem-context)
3. [Architecture](#3-architecture)
4. [Return Processing Flow](#4-return-processing-flow)
5. [Decision Logic](#5-decision-logic)
6. [Risk and Safeguards](#6-risk-and-safeguards)
7. [Failure Modes](#7-failure-modes)
8. [Running the System](#8-running-the-system)
9. [Project Structure](#9-project-structure)
10. [Configuration Reference](#10-configuration-reference)

---

## 1. System Overview

The returns processing system receives an inbound return request via HTTP, runs it through a fixed pipeline of validation and decision stages, and produces a structured outcome: approve, reject, or escalate to manual review. Every decision is logged with the full intermediate state so it can be audited, replayed, or disputed.

**What it does:**

- Accepts return requests through a REST API
- Validates them against configurable business rules (return window, product eligibility)
- Classifies the return reason into a canonical category with a confidence score
- Computes a composite risk score from classification confidence, order value, reason clarity, and return history
- Makes a final decision: `approved`, `rejected`, or `manual_review`
- Routes the outcome to the appropriate downstream system or team
- Logs the complete pipeline state as structured JSON for every request

**Where it fits:**

The system sits between the customer-facing return request form (or support inbox) and the fulfillment/finance systems. It does not process payments, generate shipping labels, or communicate with customers directly. It produces a decision and a routing destination; downstream systems act on those.

```
Customer Return Request
        │
        ▼
Returns Processing System  ◄── this system
        │
        ├── approved ──────► finance:refund_processing
        │                    warehouse:exchange_processing
        │
        ├── rejected ──────► notify_customer:rejected
        │
        └── manual_review ─► damage_claims_team
                             warehouse_investigation
                             customer_disputes_team
                             senior_support_review
                             manual_review_queue
```

---

## 2. Problem Context

**Inconsistency.** When returns are processed manually, decisions depend on who handles the request and what mood they are in. The same request submitted twice can get two different outcomes. Policy is applied unevenly.

**Audit gaps.** Manual triage leaves no machine-readable record of why a decision was made. When a customer disputes a rejection, there is no decision trail to review.

**Fraud exposure.** Without structured checks, serial returners and misrepresented claims pass through. High-value returns may receive the same level of scrutiny as low-value ones.

**Operational cost.** A team processing 100–500 returns per day spends a large fraction of its time on cases that could be decided deterministically. Manual review should be reserved for cases that genuinely require human judgment.

This system handles the deterministic cases automatically and routes the rest — ensuring human review is applied where it adds value, not as a default for everything.

---

## 3. Architecture

The pipeline is linear and stateless. Each stage receives the output of the previous stage and produces a structured result. There is no branching logic in the route handlers; all decision-making is in the service layer.

```
POST /api/v1/returns
        │
        ▼
   [ingestion]          ReturnRequest schema → ReturnRecord (no logic)
        │
        ▼
   [validation]         Policy checks: return window, product eligibility
        │               Output: ValidationResult(valid, reasons[])
        ▼
  [classification]      Keyword matching → canonical category + confidence
        │               Output: ClassificationResult(category, confidence)
        ▼
    [scoring]           Composite risk score from 4 weighted factors
        │               Output: ScoreResult(score, factor breakdown)
        ▼
    [decision]          Hard rules + score threshold → final decision
        │               Output: DecisionResult(decision, reason)
        ▼
    [routing]           Decision + category → downstream destination
        │               Output: routing_outcome (string identifier)
        ▼
     [audit]            Full pipeline state → structured JSON log
        │
        ▼
   [database]           ReturnRecord persisted with all pipeline outputs
        │
        ▼
   HTTP 201 response
```

Each stage is an independent pure function. The orchestrator (`services/orchestrator.py`) calls them in sequence and returns a `PipelineResult` containing all intermediate outputs. The route handler applies the result to the record and handles persistence — no I/O happens inside the pipeline itself.

---

## 4. Return Processing Flow

The following example walks through a complete request.

**Input:**

```json
{
  "order_id": "ORD-4421",
  "reason": "No longer need this item",
  "preference": "refund",
  "purchase_date": "2026-03-01",
  "order_amount": 49.99,
  "damaged": false
}
```

**Stage 1 — Validation**

Purchase date is 20 days before today. The configured window is 30 days. No restricted product type. Both checks pass.

```
ValidationResult(valid=True, reasons=[])
```

**Stage 2 — Classification**

The reason text is scanned against keyword lists. `"no longer need"` matches the `buyer_remorse` category with a confidence of 0.85.

```
ClassificationResult(category="buyer_remorse", confidence=0.85)
```

**Stage 3 — Scoring**

Four factors are computed and combined using fixed weights:

| Factor | Raw value | Weight | Contribution |
|---|---|---|---|
| classification_factor | 0.85 (confidence) | 0.35 | 0.2975 |
| value_factor | 1.00 ($49.99 < $250) | 0.15 | 0.1500 |
| clarity_factor | 0.85 (buyer_remorse) | 0.40 | 0.3400 |
| history_factor | 1.00 (no history) | 0.10 | 0.1000 |
| **composite score** | | | **0.8875** |

```
ScoreResult(score=0.8875, classification_factor=0.85, value_factor=1.0,
            clarity_factor=0.85, history_factor=1.0)
```

**Stage 4 — Decision**

The system checks three conditions in order:

1. Validation failed? No → continue
2. High-value order (> $500)? No → continue
3. Score (0.8875) ≥ auto_approve_score (0.70)? **Yes → APPROVE**

```
DecisionResult(decision="approved", reason="score:0.888")
```

**Stage 5 — Routing**

Decision is `approved`, preference is `refund`.

```
routing_outcome = "finance:refund_processing"
```

**Stage 6 — Audit**

A structured log entry is emitted with the full pipeline state:

```json
{
  "timestamp": "2026-03-21T09:14:22.341Z",
  "level": "INFO",
  "logger": "audit",
  "message": "return_decision",
  "return_id": "a3f4c2d1-...",
  "order_id": "ORD-4421",
  "decision": "approved",
  "decision_reason": "score:0.888",
  "routing_outcome": "finance:refund_processing",
  "validation_valid": true,
  "validation_reasons": [],
  "classification_category": "buyer_remorse",
  "classification_confidence": 0.85,
  "risk_score": 0.8875,
  "score_factors": {
    "classification": 0.85,
    "value": 1.0,
    "clarity": 0.85,
    "history": 1.0
  },
  "purchase_date": "2026-03-01",
  "order_amount": 49.99,
  "damaged": false,
  "preference": "refund"
}
```

**HTTP Response (201):**

```json
{
  "id": "a3f4c2d1-...",
  "order_id": "ORD-4421",
  "decision": "approved",
  "decision_reason": "score:0.888",
  "routing_outcome": "finance:refund_processing",
  "classification_category": "buyer_remorse",
  "classification_confidence": 0.85,
  "risk_score": 0.8875,
  "created_at": "2026-03-21T09:14:22.341Z"
}
```

---

## 5. Decision Logic

The decision engine (`services/decision.py`) applies three rules in priority order. Later rules only run if earlier ones did not trigger.

### Rule 1 — Validation failure → REJECT

If any validation check fails, the return is rejected immediately. The `decision_reason` contains all failure codes joined by `;`.

Conditions that trigger rejection:
- Purchase date is unparseable → `invalid_purchase_date`
- Days since purchase exceeds `RETURN_WINDOW_DAYS` → `outside_return_window:N_days`
- Product type is in `RESTRICTED_PRODUCT_TYPES` → `restricted_product_type:TYPE`

Multiple failures are reported together:

```
decision_reason = "validation_failed:outside_return_window:45_days;restricted_product_type:digital"
```

### Rule 2 — High-value order → MANUAL_REVIEW

If `order_amount > REFUND_THRESHOLD_AMOUNT` and `HIGH_VALUE_MANUAL_REVIEW` is enabled, the return goes to senior support review regardless of its score. This is an explicit business rule, not a score-based outcome.

```
decision_reason = "high_value_order"
routing_outcome = "senior_support_review"
```

### Rule 3 — Score threshold → APPROVE or MANUAL_REVIEW

All other valid returns are decided by the composite score:

- `score >= AUTO_APPROVE_SCORE` (default 0.70) → `approved`
- `score < AUTO_APPROVE_SCORE` → `manual_review`

There is no score-based rejection path for valid returns. A valid return that scores very low still goes to manual review — not rejection — because validation passing means policy conditions are met; human judgment resolves ambiguity.

---

## 6. Risk and Safeguards

### Classification categories and clarity

The scoring model's dominant factor (weight 0.40) is category clarity — how objectively auto-processable the return reason is. Categories that require physical verification or involve subjective judgment receive low clarity scores, which pull the composite score below the auto-approve threshold regardless of classification confidence.

| Category | Clarity | Rationale |
|---|---|---|
| `sizing` | 0.90 | Objective, policy-standard |
| `buyer_remorse` | 0.85 | Clear motivation, no verification needed |
| `not_as_described` | 0.25 | Subjective — requires human judgment |
| `wrong_item` | 0.25 | Needs warehouse verification before approving |
| `damaged` | 0.10 | Requires physical inspection |
| `other` | 0.20 | Unknown reason — cautious default |

This means a return claiming a `damaged` item, even if classified with 0.95 confidence, will score approximately 0.62 — below the 0.70 approval threshold — and will be routed to `damage_claims_team`.

### Value factor

Orders above 50% of `REFUND_THRESHOLD_AMOUNT` receive a reduced value factor:

- `order_amount > REFUND_THRESHOLD_AMOUNT ($500)` → value_factor = 0.50
- `order_amount > $250` → value_factor = 0.75
- `order_amount <= $250` or `null` → value_factor = 1.00

The value factor alone cannot push a return below the approval threshold — it works in combination with classification confidence and clarity.

### Confidence threshold

The `AUTO_APPROVE_SCORE` threshold of 0.70 is not a global percentile target. It is the minimum composite score below which human review adds more value than automation. It is configurable per deployment. Lowering it increases automation rate; raising it reduces it. Changes should be informed by reviewing the manual queue composition over time.

### Return history (simulated)

The `history_factor` currently returns 1.0 for all customers (clean record assumed). The scoring module documents the interface: replace `_simulate_history()` with a DB lookup on `customer_email` or `order_id` to factor in a customer's return frequency, prior rejections, or fraud flags. The weight is 0.10 — enough to tip borderline cases without dominating the outcome.

### Unknown reasons

A return submitted with an unrecognisable reason is classified as `other` with confidence 0.30 and a clarity factor of 0.20. The resulting composite score is approximately 0.44, which routes it to `manual_review_queue`. This is the designed fallback: unknown does not mean rejected, it means reviewed.

---

## 7. Failure Modes

**Return submitted outside the window.**
The validation layer catches this and rejects with `outside_return_window:N_days`. No score is computed.

**Unparseable purchase date.**
Validation returns `invalid_purchase_date` and exits early. No subsequent stages run. This protects scoring and decision from operating on garbage inputs.

**Product type missing.**
`product_type=null` is treated as unrestricted. Restriction checks are skipped. This is the safe default — missing information should not trigger a rejection.

**Order amount missing.**
`order_amount=null` is treated as $0.00 for the value factor (value_factor = 1.0). The high-value rule does not trigger. If order amount tracking is required for a deployment, validation should be extended to require the field.

**Reason text that matches nothing.**
The classifier falls back to `other` with confidence 0.30. The low clarity factor (0.20) produces a score below the approval threshold. The return goes to `manual_review_queue`.

**Reason text that partially matches multiple categories.**
The classifier takes the highest-confidence keyword match across all categories. If two keywords from different categories match, the one with higher confidence wins. In practice, reasons strong enough to drive a score above 0.70 (buyer remorse, sizing) are unlikely to ambiguously match damage or wrong-item terms.

**Database unavailable.**
The `/health/ready` endpoint returns 503. Requests to `/api/v1/returns` will fail at the DB write step after the pipeline has already run. The audit log entry is emitted before the DB write, so the decision is not lost even if persistence fails. This is the current behaviour; for production use, the audit write should be decoupled from the HTTP response path.

**Config value not set.**
All settings have safe defaults. A deployment that omits `AUTO_APPROVE_SCORE` gets 0.70. A deployment that omits `RESTRICTED_PRODUCT_TYPES` gets an empty list (no restrictions). Settings are validated at startup by Pydantic.

---

## 8. Running the System

### Local

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server (database created automatically on first run)
uvicorn app.main:app --reload --port 8000

# API docs
open http://localhost:8000/docs
```

### Docker

```bash
# Build
docker build -t returns-api .

# Run
docker run -p 8000:8000 --env-file .env returns-api
```

Copy `.env.example` to `.env` and adjust values before starting.

### Tests

```bash
pytest                          # all tests
pytest tests/test_scoring.py    # single module
pytest -v --tb=short            # verbose with short tracebacks
```

### API

**Submit a return:**

```bash
curl -X POST http://localhost:8000/api/v1/returns \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-1234",
    "reason": "Item arrived damaged",
    "preference": "refund",
    "purchase_date": "2026-03-01",
    "order_amount": 89.99,
    "damaged": true
  }'
```

Response:

```json
{
  "id": "c7a2f1b3-...",
  "order_id": "ORD-1234",
  "decision": "manual_review",
  "decision_reason": "low_confidence_score:0.622",
  "routing_outcome": "damage_claims_team",
  "classification_category": "damaged",
  "classification_confidence": 0.95,
  "risk_score": 0.622,
  "created_at": "2026-03-21T09:14:22.341Z"
}
```

**Retrieve a return:**

```bash
curl http://localhost:8000/api/v1/returns/c7a2f1b3-...
```

**Health:**

```bash
curl http://localhost:8000/health           # liveness
curl http://localhost:8000/health/ready     # readiness (DB check)
curl http://localhost:8000/metrics          # decision rate counters
```

---

## 9. Project Structure

```
app/
├── main.py              FastAPI application, lifespan (DB init on startup)
├── config.py            All settings, read from environment / .env file
├── database.py          Async SQLAlchemy engine and session factory
│
├── core/
│   ├── logging.py       Structured JSON formatter, get_logger()
│   └── metrics.py       In-process counters: approval / rejection / manual_review rates
│
├── models/
│   └── returns.py       SQLAlchemy ReturnRecord — persisted schema
│
├── schemas/
│   └── returns.py       Pydantic request/response schemas
│
├── services/
│   ├── ingestion.py     Schema → model mapping. No logic.
│   ├── validation.py    Policy checks. Accumulates all failures.
│   ├── classification.py  Keyword-based reason classification + confidence.
│   ├── scoring.py       Composite risk score from 4 weighted factors.
│   ├── decision.py      Two hard rules + score threshold → final decision.
│   ├── routing.py       Decision + classification → downstream destination.
│   ├── audit.py         Structured log of full pipeline state per return.
│   └── orchestrator.py  process_return() — pure function, no I/O.
│
└── routes/
    ├── health.py        GET /health, GET /health/ready
    └── returns.py       POST /api/v1/returns, GET /api/v1/returns/{id}

tests/
├── conftest.py          In-memory SQLite per test, metrics reset fixture
├── test_health.py       Liveness and readiness endpoints
├── test_validation.py   Window boundaries, bad dates, multi-failure accumulation
├── test_classification.py  All categories, confidence bounds, flag override
├── test_scoring.py      Score invariants, value factor, threshold alignment
├── test_decision.py     All three decision paths, hard rule behaviour
└── test_return_flow.py  End-to-end pipeline via HTTP
```

**Dependency flow** (each layer only imports downward):

```
routes → orchestrator → validation, classification, scoring, decision, routing
routes → audit, ingestion, database
core → (no app imports)
```

The orchestrator does not import from routes or audit. The pipeline has no knowledge of HTTP or persistence. This means any stage can be tested in isolation with plain Python objects.

---

## 10. Configuration Reference

All values are set via environment variables or an `.env` file. See `.env.example` for a template.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./returns.db` | SQLAlchemy async database URL. Swap for `postgresql+asyncpg://...` in production. |
| `RETURN_WINDOW_DAYS` | `30` | Days after purchase within which returns are accepted. |
| `REFUND_THRESHOLD_AMOUNT` | `500.0` | Orders above this amount are sent to senior support review regardless of score. |
| `HIGH_VALUE_MANUAL_REVIEW` | `true` | Enable or disable the high-value hard rule. Disable only for testing. |
| `AUTO_APPROVE_SCORE` | `0.70` | Composite score at or above which a valid return is auto-approved. |
| `RESTRICTED_PRODUCT_TYPES` | `[]` | JSON list of product type strings that cannot be returned. E.g. `["digital","perishable"]`. |

No configuration value is hardcoded in service logic. All business rules are read from `settings` at runtime.
