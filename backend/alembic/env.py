"""Configuración de Alembic para el Board Game Tracker.

- La URL de la BD se toma de `app.core.config.settings` (.env), no del .ini.
- `target_metadata` es el metadata real de SQLAlchemy (todos los modelos) para
  que `--autogenerate` detecte tablas, columnas, índices y constraints.
- En SQLite se activa `render_as_batch` para que Alembic emule los ALTER
  recreando la tabla (SQLite no soporta ALTER completo).

Uso (desde backend/):
    .venv\\Scripts\\alembic.exe revision --autogenerate -m "mensaje"
    .venv\\Scripts\\alembic.exe upgrade head
    .venv\\Scripts\\alembic.exe downgrade -1
"""
from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

import app.models  # noqa: F401  (registra todos los modelos en Base.metadata)
from app.core.config import settings
from app.db.base import Base

config = context.config

# La URL siempre sale de settings (.env) y sobrescribe la del alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Logging de Alembic. Cuando las migraciones se lanzan desde la propia app
# (app/db/migrate.py) se omite para no desactivar los loggers de uvicorn/root.
if config.config_file_name is not None and not config.attributes.get("skip_logging_config"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline: solo genera SQL, sin conectar a la BD."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online: conecta a la BD y aplica las migraciones."""
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
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
