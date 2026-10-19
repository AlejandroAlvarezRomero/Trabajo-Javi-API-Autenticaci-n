"""Esquemas Pydantic de partidas y verificación de resultados."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class MatchCreate(BaseModel):
    game_id: int
    winner_id: int
    participant_ids: list[int] = Field(min_length=2, max_length=30)
    played_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=24 * 60)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _check_participants(self) -> "MatchCreate":
        if len(set(self.participant_ids)) != len(self.participant_ids):
            raise ValueError("participant_ids no puede contener duplicados")
        if self.winner_id not in self.participant_ids:
            raise ValueError("winner_id debe estar entre los participant_ids")
        return self


class ParticipantOut(BaseModel):
    user_id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    placement: int | None = None
    elo_delta: int | None = None


class ConfirmationOut(BaseModel):
    user_id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    confirmed: bool | None = None  # None = pendiente de respuesta
    responded_at: datetime | None = None



class MatchOut(BaseModel):
    id: int
    group_id: int
    game_id: int
    game_name: str | None = None
    season_id: int
    registered_by_id: int
    winner_id: int
    status: str
    played_at: datetime
    duration_minutes: int | None = None
    notes: str | None = None
    created_at: datetime
    verified_at: datetime | None = None
    participants: list[ParticipantOut] = []
    confirmations: list[ConfirmationOut] = []
