"""Esquemas Pydantic del catálogo de juegos (integración BGG)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GameCreate(BaseModel):
    bgg_id: int = Field(gt=0, description="ID del juego en BoardGameGeek (thing/XXXX)")


class GameOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    bgg_id: int | None
    name: str
    description: str | None
    image_url: str | None
    thumbnail_url: str | None
    min_players: int | None
    max_players: int | None
    avg_playtime_minutes: int | None
    year_published: int | None
    bgg_ranking: int | None
    bgg_rating: float | None
    created_at: datetime


class BGGSearchResultOut(BaseModel):
    bgg_id: int
    name: str
    year_published: int | None = None
