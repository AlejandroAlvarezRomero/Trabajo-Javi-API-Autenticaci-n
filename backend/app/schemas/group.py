"""Esquemas Pydantic de grupos, membresías y temporadas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    seed_popular: bool = Field(
        default=False,
        description="Si es True, precarga el catálogo con juegos populares (Catan, Carcassonne, Pandemic, etc.)",
    )



class GroupOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    invite_code: str
    owner_id: int
    created_at: datetime
    # Información contextual del usuario que pide
    my_role: str | None = None
    member_count: int = 0
    game_count: int = 0


class GroupJoinRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=12)


class MemberOut(BaseModel):
    user_id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    role: str  # MANAGER | MEMBER
    joined_at: datetime



class MemberRoleUpdate(BaseModel):
    role: str = Field(pattern="^(MANAGER|MEMBER)$")


class GroupTransferOwnership(BaseModel):
    new_owner_id: int = Field(gt=0, description="ID del miembro que será el nuevo propietario")


class SeasonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    name: str
    start_date: datetime
    end_date: datetime
    is_active: bool
