# Database Migrations

This project currently auto-creates tables during backend startup for local demo use.

For production-like deployments, use Alembic migrations so schema changes are controlled and reviewable.

## 1. Current Database Contract

The ORM models live in:

```text
backend/app/models/models.py
```

Main tables:

- `users`
- `user_sessions`
- `chat_messages`
- `approval_requests`
- `executions`
- `workflow_failures`
- `repository_installations`
- `automation_rules`

## 2. Migration Policy

Use migrations when:

- changing a column type,
- adding a table,
- removing a table,
- adding indexes or constraints,
- deploying beyond local demo mode.

Avoid relying only on auto-create behavior outside local development.

## 3. Safety Notes

- Back up production-like databases before migration.
- Do not store secrets in migration files.
- Review generated migrations before applying them.
- Keep migrations focused on schema changes only.

## 4. Recommended Future Setup

The repository already includes Alembic as a backend dependency. A production-ready migration setup should include:

- Alembic environment configured for `DATABASE_URL`,
- one initial migration matching current ORM models,
- tests or verification for upgrade/downgrade paths,
- documented release process.
