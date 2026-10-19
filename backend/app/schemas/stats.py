"""Esquemas Pydantic de estadísticas, clasificación y usuarios (admin)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.group import SeasonOut


class GroupStatsOut(BaseModel):
    user_id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    elo: int

    rank: str
    wins: int
    losses: int
    games_played: int
    win_rate: float
    total_play_minutes: int


class LeaderboardOut(BaseModel):
    season: SeasonOut
    entries: list[GroupStatsOut] = []


class UserAdminUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = Field(default=None, pattern="^(ADMIN|PLAYER)$")


class PlatformOverview(BaseModel):
    users: int = 0
    groups: int = 0
    matches_pending: int = 0
    matches_confirmed: int = 0
