# Database Migrations

Currently using SQLAlchemy `create_all()` for SQLite in development.

## Upgrading to PostgreSQL + Alembic

When ready to move to production with PostgreSQL:

1. Install Alembic: `pip install alembic`
2. Init: `alembic init alembic`
3. Update `alembic.ini` with your PostgreSQL `DATABASE_URL`
4. Set `target_metadata = Base.metadata` in `alembic/env.py`
5. Generate first migration: `alembic revision --autogenerate -m "initial"`
6. Apply: `alembic upgrade head`

Note: SQLAlchemy `JSON` columns stored as TEXT in SQLite map to native `JSONB` in PostgreSQL
automatically — no schema changes needed for the `plans` table.
