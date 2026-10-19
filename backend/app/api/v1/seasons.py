"""Temporadas del grupo: histórico y rollover manual (soft reset)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_group_role
from app.db.session import get_db
from app.models import GroupMembership, Season
from app.models.enums import GroupRole
from app.schemas.group import SeasonOut
from app.services import season_service

router = APIRouter(prefix="/groups/{group_id}/seasons", tags=["Temporadas"])


@router.get("", response_model=list[SeasonOut], summary="Histórico de temporadas")
def list_seasons(
    group_id: int,
    db: Session = Depends(get_db),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> list[Season]:
    return list(
        db.scalars(
            select(Season)
            .where(Season.group_id == group_id)
            .order_by(Season.number.desc())
        ).all()
    )


@router.post(
    "/rollover",
    response_model=SeasonOut,
    status_code=status.HTTP_201_CREATED,
    summary="Iniciar la siguiente temporada ya mismo (Gestor)",
    description=(
        "Cierra la temporada activa, aplica soft reset del ELO "
        "(regresión 50% a la media) y conserva el histórico anterior."
    ),
)
def force_rollover(
    group_id: int,
    db: Session = Depends(get_db),
    _manager: GroupMembership = Depends(require_group_role(GroupRole.MANAGER)),
) -> Season:
    return season_service.rollover(db, group_id)
