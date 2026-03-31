.PHONY: lint typecheck test run migrate evaluate ci

lint:
	ruff check app tests scripts

typecheck:
	mypy app

test:
	pytest tests/ -q

migrate:
	alembic upgrade head

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

evaluate:
	PYTHONPATH=. python scripts/evaluate.py --jsonl eval/test_set.jsonl --report eval/report.json

# Local parity with CI (lint + types + tests + golden eval)
ci: lint typecheck test evaluate
