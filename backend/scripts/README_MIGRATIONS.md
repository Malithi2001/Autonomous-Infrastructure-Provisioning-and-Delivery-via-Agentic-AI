# Database Migrations (Alembic)

This directory contains Alembic database migration files.

## Setup

```bash
cd backend
alembic init alembic   # Already initialized
```

## Create a migration

```bash
alembic revision --autogenerate -m "create users table"
```

## Apply migrations

```bash
alembic upgrade head
```

## Rollback

```bash
alembic downgrade -1
```

In development, the app auto-creates tables via `init_db()` on startup.
Use Alembic for production schema migrations.
