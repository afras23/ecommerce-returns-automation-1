# Operations runbook

## Debug a failed or surprising return

1. **Get the correlation ID**  
   - Response header: `X-Correlation-ID` (also echoed in `ProcessReturnResponse.correlation_id` for `/returns/process` and batch).  
   - Search structured logs for that value (JSON logs include `correlation_id`).

2. **Fetch the persisted record**  
   - `GET /api/v1/returns/{return_id}` returns decision, reasons, classification, fraud fields, processing time, optional shipping label JSON.

3. **Read the audit line**  
   - Logger `audit`, message `return_decision`, includes validation, classification, `risk_score`, `score_factors`, routing.

4. **Common causes**  
   - **Rejected:** validation failed (window, restricted product type, bad date).  
   - **Manual review:** low composite score, high-value rule, damaged/wrong-item style clarity, or vague reason.  
   - **Approved:** valid + score ≥ `AUTO_APPROVE_SCORE` and no blocking rule.

5. **Reproduce offline**  
   - Run `python` with `ReturnRecord` + `process_return` from `app/services/orchestrator.py` (pure function, no DB).  
   - Or run `make evaluate` to validate classification / fraud / refund components against `eval/test_set.jsonl`.

## Reprocess returns

There is no separate “replay” queue in this codebase. Reprocessing is **client-driven**:

- **Single:** `POST /api/v1/returns/process` with the same or corrected payload (new row each time; idempotent business logic is not assumed on `order_id`).
- **Batch:** `POST /api/v1/returns/batch` with up to 50 items in `items[]`.
- **Data fix:** If the DB row must be corrected, use your DB tooling or add an internal admin path (not shipped here).

For **deterministic debugging**, use the same `purchase_date` and inputs; policy uses `Settings` at process time.

## Monitor metrics

- **HTTP:** `GET /metrics` (disabled body if `METRICS_ENABLED=false`).  
  Returns decision counters (`approval_rate`, `rejection_rate`, `manual_review_rate`) and observability snapshot: returns processed, fraud flagged count/rate, average processing time.

- **Logs:** Structured JSON (`classification`, `fraud_scoring`, `refund_calculation`, `pipeline_decision`, `http_request`).  
  Filter by `correlation_id` or `return_id`.

- **Health:** `GET /health` (liveness), `GET /health/ready` (DB session check).

## Evaluation regression (release gate)

```bash
make evaluate
```

Writes `eval/report.json` (gitignored). Exit code non-zero if any golden case fails.

## Secrets and configuration

- Never commit `.env`. Use `.env.example` as the template.  
- Rotate `AI_API_KEY` if leaked; restrict network egress for production API keys.
