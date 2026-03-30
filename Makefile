.PHONY: lint typecheck test run migrate

lint:
	ruff check app tests

typecheck:
	mypy app

test:
	pytest tests/ -q

migrate:
	alembic upgrade head

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
