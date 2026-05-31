"""Alembic environment — online mode only.

DSN is built from the same `DB_*` env vars the services use (via
`settings.Settings`), so local dev / CI / prod all share one secret source.
`target_metadata` is the project's ORM `Base`, so `--autogenerate` diffs new
revisions against `backend/db/schema.py`.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

_repo_root = Path(__file__).resolve().parents[3]
_backend = _repo_root / "backend"
for p in (_repo_root, _backend):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from db.schema import Base  # noqa: E402
from settings.Settings import Settings  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", Settings().database_url)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
