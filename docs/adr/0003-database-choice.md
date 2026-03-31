# ADR 0003: Database choice

## Status

Accepted

## Context

The service needs async persistence for `ReturnRecord`, optional Postgres in production, and simple local development without external services.

## Decision

- **SQLAlchemy 2.x async** with `AsyncSession`; URL from `DATABASE_URL` / `database_url` in `Settings`.
- **Default development:** `sqlite+aiosqlite` file (`./returns.db`) for zero-setup runs and CI/tests (in-memory SQLite with `StaticPool` in tests).
- **Production target:** `postgresql+asyncpg://...` with the same models and **Alembic** migrations for schema evolution.
- **Startup:** `init_db()` creates tables if missing (dev ergonomics); migrations are the source of truth for long-lived environments.

## Consequences

**Positive:** One ORM model set; easy swap of URL per environment.  
**Negative:** SQLite and Postgres differ slightly in types/constraints; migrations must be validated against Postgres before production rollout.
