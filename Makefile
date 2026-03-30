.PHONY: lint typecheck test run

lint:
	ruff check app tests

typecheck:
	mypy app

test:
	pytest tests/ -q

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
