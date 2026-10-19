"""Utilidades de fecha. Todos los timestamps internos son UTC "naive"
para ser compatibles tanto con SQLite como con PostgreSQL."""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
