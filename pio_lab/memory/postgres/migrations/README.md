Postgres migrations live here.

M1 uses SQLAlchemy metadata for `scripts/init_db.py` and includes an initial Alembic
revision under `versions/` so the schema has a migration source of truth once Alembic
is wired into deployment.
