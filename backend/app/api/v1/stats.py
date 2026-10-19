"""Estadísticas: win rate, ELO, rangos y tiempo jugado por grupo."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_group_role
from app.db.session import get_db
from app.models import GroupMembership, SeasonRating, User
from app.models.enums import GroupRole
from app.schemas.stats import GroupStatsOut, LeaderboardOut
from app.services import season_service
from app.services.season_service import base_stats_out

router = APIRouter(prefix="/groups/{group_id}", tags=["Estadísticas"])

_TOP_LIMIT = 50


def _stats_out(db: Session, rating: SeasonRating | None, user: User) -> GroupStatsOut:
    if rating is None:
        return GroupStatsOut(**base_stats_out(user.id, user.username, user.display_name, user.avatar_url))
    return GroupStatsOut(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        elo=rating.elo,
        rank=rating.rank,
        wins=rating.wins,
        losses=rating.losses,
        games_played=rating.games_played,
        win_rate=rating.win_rate,
        total_play_minutes=rating.total_play_minutes,
    )



@router.get(
    "/leaderboard",
    response_model=LeaderboardOut,
    summary="Clasificación ELO de la temporada vigente",
)
def leaderboard(
    group_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> LeaderboardOut:
    season = season_service.ensure_active_season(db, group_id)
    ratings = db.scalars(
        select(SeasonRating)
        .where(SeasonRating.season_id == season.id)
        .order_by(SeasonRating.elo.desc(), SeasonRating.wins.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    users = {
        u.id: u
        for u in db.scalars(
            select(User).where(User.id.in_([r.user_id for r in ratings]))
        ).all()
    } if ratings else {}
    return LeaderboardOut(
        season=season,
        entries=[
            _stats_out(db, rating, users[rating.user_id])
            for rating in ratings
            if rating.user_id in users
        ],
    )


@router.get(
    "/stats/me",
    response_model=GroupStatsOut,
    summary="Mis estadísticas en el grupo (temporada vigente)",
)
def my_stats(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> GroupStatsOut:
    season = season_service.ensure_active_season(db, group_id)
    rating = db.scalar(
        select(SeasonRating).where(
            SeasonRating.season_id == season.id,
            SeasonRating.user_id == user.id,
        )
    )
    return _stats_out(db, rating, user)


@router.get(
    "/stats/users/{user_id}",
    response_model=GroupStatsOut,
    summary="Estadísticas de otro miembro del grupo",
)
def user_stats(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> GroupStatsOut:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    is_member = db.scalar(
        select(GroupMembership.id).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    if is_member is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Ese usuario no pertenece al grupo"
        )
    season = season_service.ensure_active_season(db, group_id)
    rating = db.scalar(
        select(SeasonRating).where(
            SeasonRating.season_id == season.id,
            SeasonRating.user_id == user_id,
        )
    )
    return _stats_out(db, rating, target)
