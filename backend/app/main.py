"""Punto de entrada de la aplicación FastAPI (Swagger en /docs)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from app.api.v1 import (
    achievements,
    admin,
    auth,
    games,
    groups,
    matches,
    notifications,
    seasons,
    stats,
)
from app.core.config import settings
from app.db.migrate import run_migrations
from app.db.seed import seed_achievements, seed_roles
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aplica las migraciones pendientes (crea el esquema si la BD no existe)
    # y siembra los datos maestros: roles (ADMIN/PLAYER) y logros.
    run_migrations()
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_achievements(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "API para registrar y gestionar partidas de juegos de mesa: "
        "grupos privados, catálogo BGG, verificación de resultados, "
        "ELO, temporadas y logros."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,  # necesario para la cookie HttpOnly del refresh
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(groups.router, prefix=settings.API_V1_PREFIX)
app.include_router(games.router, prefix=settings.API_V1_PREFIX)
app.include_router(matches.router, prefix=settings.API_V1_PREFIX)
app.include_router(seasons.router, prefix=settings.API_V1_PREFIX)
app.include_router(stats.router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)
app.include_router(achievements.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)

_UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"
(_UPLOADS_DIR / "avatars").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")


@app.get("/health", tags=["Sistema"])

def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.PROJECT_NAME}
