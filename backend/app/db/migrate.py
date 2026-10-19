"""Ejecución de migraciones Alembic desde la propia app (lifespan).

Equivale al comando manual `alembic upgrade head` lanzado desde backend/.
"""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/


def run_migrations() -> None:
    """Aplica todas las migraciones pendientes (crea el esquema si no existe)."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    # No reconfigurar el logging al migrar (evita desactivar los loggers
    # de uvicorn al arrancar la app).
    cfg.attributes["skip_logging_config"] = True
    command.upgrade(cfg, "head")
