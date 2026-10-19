"""Test de migraciones Alembic (Tarea A del backlog).

Verifica sobre una BD temporal aislada (`boardgames_mig_test.db`):
  1. `upgrade head` crea las 14 tablas de dominio + `alembic_version`.
  2. La versión aplicada coincide con la cabeza de revisiones.
  3. Sin "drift": los modelos SQLAlchemy y las migraciones coinciden.
  4. `downgrade base` deja la BD sin tablas de dominio.
  5. Un segundo `upgrade head` reconstruye el esquema completo.

Ejecutar desde `backend/`:
    .venv\\Scripts\\python.exe tests\\migrations_test.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# BD temporal propia del test (no toca boardgames.db) — antes de importar settings
os.environ["DATABASE_URL"] = "sqlite:///./boardgames_mig_test.db"

from alembic import command  # noqa: E402
from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import create_engine, inspect, text  # noqa: E402

import app.models  # noqa: F401,E402  (registra los modelos en Base.metadata)
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402

DOMAIN_TABLES = [
    "achievements",
    "roles",
    "users",
    "groups",
    "notifications",
    "refresh_tokens",
    "group_games",
    "group_memberships",
    "seasons",
    "user_achievements",
    "matches",
    "season_ratings",
    "match_confirmations",
    "match_participants",
]

DB_FILE = ROOT / "boardgames_mig_test.db"
DB_FILE.unlink(missing_ok=True)

cfg = Config(str(ROOT / "alembic.ini"))
cfg.attributes["skip_logging_config"] = True  # no tocar el logging de la consola
head = ScriptDirectory.from_config(cfg).get_current_head()

engine = create_engine(settings.DATABASE_URL)
results = []


def check(name, condition, extra=""):
    results.append(bool(condition))
    print(("OK  " if condition else "FAIL") + f" {name}" + (f" | {extra}" if extra else ""))


def tables():
    return sorted(inspect(engine).get_table_names())


check("BD recien borrada: sin tablas", tables() == [], str(tables()))

# --- 1 y 2: upgrade head sobre BD vacía -------------------------------
command.upgrade(cfg, "head")
expected = sorted(DOMAIN_TABLES + ["alembic_version"])
check(
    f"upgrade head crea {len(expected)} tablas",
    tables() == expected,
    f"{len(tables())}/{len(expected)}",
)

with engine.connect() as conn:
    version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
check("version aplicada = head", version == head, f"{version} / {head}")

# --- 3: sin drift entre modelos y migraciones --------------------------
with engine.connect() as conn:
    ctx = MigrationContext.configure(
        conn, opts={"compare_type": True, "render_as_batch": True}
    )
    diffs = compare_metadata(ctx, Base.metadata)
check("sin drift entre modelos y migraciones", not diffs, str(diffs)[:200])

# --- 4: downgrade completo ---------------------------------------------
command.downgrade(cfg, "base")
check("downgrade base elimina el esquema", tables() == ["alembic_version"], str(tables()))

# --- 5: re-upgrade (idempotencia desde cero) ----------------------------
command.upgrade(cfg, "head")
check("segundo upgrade head reconstruye el esquema", tables() == expected)

engine.dispose()
DB_FILE.unlink(missing_ok=True)

failed = [i for i, ok in enumerate(results) if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} comprobaciones OK")
sys.exit(1 if failed else 0)
