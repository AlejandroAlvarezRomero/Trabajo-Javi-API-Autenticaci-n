"""Ciclo de vida de las temporadas (3 meses) y ratings por temporada.

- ensure_active_season(): si la temporada vigente expiró, hace rollover.
- rollover(): cierra la temporada, crea la siguiente con soft reset del ELO
  y copia a los miembros actuales. El histórico queda intacto en la
  temporada anterior (SeasonRating)."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.models import GroupMembership, Season, SeasonRating
from app.models.season import SEASON_DURATION_DAYS, SEASON_START_ELO
from app.services.elo_service import rank_for, soft_reset


def get_active_season(db: Session, group_id: int) -> Season | None:
    return db.scalar(
        select(Season)
        .where(Season.group_id == group_id, Season.is_active.is_(True))
        .order_by(Season.number.desc())
    )


def get_or_create_rating(
    db: Session, group_id: int, season: Season, user_id: int
) -> SeasonRating:
    rating = db.scalar(
        select(SeasonRating).where(
            SeasonRating.season_id == season.id,
            SeasonRating.user_id == user_id,
        )
    )
    if rating is None:
        rating = SeasonRating(
            season_id=season.id, group_id=group_id, user_id=user_id
        )
        db.add(rating)
        db.flush()
    return rating


def rollover(db: Session, group_id: int) -> Season:
    """Cierra la temporada activa y arranca la siguiente con soft reset."""
    current = get_active_season(db, group_id)
    now = utcnow()

    if current is not None:
        current.is_active = False

    max_number = (
        db.scalar(select(func.max(Season.number)).where(Season.group_id == group_id))
        or 0
    )
    new_season = Season(
        group_id=group_id,
        number=max_number + 1,
        name=f"Temporada {max_number + 1}",
        start_date=now,
        end_date=now + timedelta(days=SEASON_DURATION_DAYS),
        is_active=True,
    )
    db.add(new_season)
    db.flush()

    if current is not None:
        # Soft reset: los ratings de la temporada pasada se guardan como histórico
        previous = db.scalars(
            select(SeasonRating).where(SeasonRating.season_id == current.id)
        ).all()
        for old in previous:
            new_elo = soft_reset(old.elo)
            db.add(
                SeasonRating(
                    season_id=new_season.id,
                    group_id=group_id,
                    user_id=old.user_id,
                    elo=new_elo,
                    rank=rank_for(new_elo).value,
                )
            )
        # Importante: autoflush está desactivado; flushear evita duplicar
        # los ratings en el bloque siguiente (UNIQUE season_id + user_id)
        db.flush()

    # Todos los miembros actuales empiezan la temporada con su rating base
    member_ids = db.scalars(
        select(GroupMembership.user_id).where(GroupMembership.group_id == group_id)
    ).all()
    for user_id in member_ids:
        get_or_create_rating(db, group_id, new_season, user_id)

    db.commit()
    db.refresh(new_season)
    return new_season


def ensure_active_season(db: Session, group_id: int) -> Season:
    """Devuelve la temporada vigente; si expiró (o no existe), inicia la nueva."""
    season = get_active_season(db, group_id)
    now = utcnow()
    if season is not None and season.end_date > now:
        return season
    return rollover(db, group_id)


def current_or_latest_season(db: Session, group_id: int) -> Season | None:
    return db.scalar(
        select(Season)
        .where(Season.group_id == group_id)
        .order_by(Season.is_active.desc(), Season.number.desc())
    )


def base_stats_out(
    user_id: int,
    username: str,
    display_name: str | None = None,
    avatar_url: str | None = None,
) -> dict:
    """Valores por defecto cuando un usuario aún no tiene rating en la temporada."""
    return {
        "user_id": user_id,
        "username": username,
        "display_name": display_name,
        "avatar_url": avatar_url,
        "elo": SEASON_START_ELO,
        "rank": rank_for(SEASON_START_ELO).value,
        "wins": 0,
        "losses": 0,
        "games_played": 0,
        "win_rate": 0.0,
        "total_play_minutes": 0,
    }

