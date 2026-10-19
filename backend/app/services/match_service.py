"""Servicio de partidas: registro en PENDING y verificación con ELO.

Flujo:
  register_match()       -> Match PENDING + confirmaciones pendientes + notificaciones
  finalize_if_ready()    -> si todos confirman, aplica ELO/stats/logros
  mark_rejected()        -> si alguien rechaza, la partida queda REJECTED"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.timeutils import utcnow
from app.models import (
    Game,
    GroupMembership,
    Match,
    MatchConfirmation,
    MatchParticipant,
    Notification,
    SeasonRating,
    User,
)
from app.models.enums import MatchStatus, NotificationType
from app.schemas.match import MatchCreate
from app.services import achievement_service, season_service
from app.services.elo_service import compute_updates, rank_for
from app.services.event_service import publish_user_event


def register_match(
    db: Session, group_id: int, registrer_id: int, payload: MatchCreate
) -> Match:
    game = db.get(Game, payload.game_id)
    if game is None or game.group_id != group_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Juego no encontrado en este grupo")

    participant_ids = list(dict.fromkeys(payload.participant_ids))
    if registrer_id not in participant_ids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Debes estar entre los participantes"
        )
    if len(participant_ids) < 2:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Una partida necesita al menos 2 participantes"
        )

    # Todos deben ser miembros del grupo
    member_ids = set(
        db.scalars(
            select(GroupMembership.user_id).where(
                GroupMembership.group_id == group_id,
                GroupMembership.user_id.in_(participant_ids),
            )
        ).all()
    )
    if member_ids != set(participant_ids):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Todos los participantes deben ser miembros del grupo",
        )

    season = season_service.ensure_active_season(db, group_id)
    for user_id in participant_ids:
        season_service.get_or_create_rating(db, group_id, season, user_id)

    registrer = db.get(User, registrer_id)
    match = Match(
        group_id=group_id,
        game_id=game.id,
        season_id=season.id,
        registered_by_id=registrer_id,
        winner_id=payload.winner_id,
        status=MatchStatus.PENDING.value,
        played_at=payload.played_at or utcnow(),
        duration_minutes=payload.duration_minutes,
        notes=payload.notes,
    )
    db.add(match)
    db.flush()

    for position, user_id in enumerate(participant_ids, start=1):
        db.add(
            MatchParticipant(
                match_id=match.id,
                user_id=user_id,
                placement=1 if user_id == payload.winner_id else None,
            )
        )
        if user_id != registrer_id:
            # El resto debe verificar el resultado
            db.add(MatchConfirmation(match_id=match.id, user_id=user_id))
            db.add(
                Notification(
                    user_id=user_id,
                    type=NotificationType.MATCH_CONFIRMATION.value,
                    title=f"Confirma la partida de {game.name}",
                    body=(
                        f"{registrer.username if registrer else 'Un jugador'} registró "
                        f"una partida de {game.name} en este grupo. "
                        "Revisa el resultado y confirma o rechaza."
                    ),
                    link=f"/groups/{group_id}/matches/{match.id}",
                )
            )
            publish_user_event(
                user_id,
                {
                    "type": NotificationType.MATCH_CONFIRMATION.value,
                    "title": f"Confirma la partida de {game.name}",
                    "body": f"{registrer.username if registrer else 'Un jugador'} registró una partida de {game.name}.",
                    "link": f"/groups/{group_id}/matches/{match.id}",
                },
            )

    db.commit()
    db.refresh(match)
    return match


def finalize_if_ready(db: Session, match: Match) -> bool:
    """Si no quedan respuestas pendientes ni rechazos, confirma la partida."""
    if match.status != MatchStatus.PENDING.value:
        return False

    pending = (
        db.scalar(
            select(func.count(MatchConfirmation.id)).where(
                MatchConfirmation.match_id == match.id,
                MatchConfirmation.confirmed.is_(None),
            )
        )
        or 0
    )
    rejected = (
        db.scalar(
            select(func.count(MatchConfirmation.id)).where(
                MatchConfirmation.match_id == match.id,
                MatchConfirmation.confirmed.is_(False),
            )
        )
        or 0
    )
    if pending or rejected:
        return False

    _apply_results(db, match)
    return True


def _apply_results(db: Session, match: Match) -> None:
    """Concede la partida: variaciones ELO, estadísticas de temporada y logros."""
    season = _season(db, match)
    ratings: dict[int, SeasonRating] = {}
    for participant in match.participants:
        rating = season_service.get_or_create_rating(
            db, match.group_id, season, participant.user_id
        )
        ratings[participant.user_id] = rating

    current_elos = {uid: r.elo for uid, r in ratings.items()}
    deltas = compute_updates(current_elos, match.winner_id)
    minutes = match.duration_minutes or 0

    for participant in match.participants:
        rating = ratings[participant.user_id]
        delta = deltas[participant.user_id]
        participant.elo_delta = delta
        rating.elo += delta
        rating.rank = rank_for(rating.elo).value
        rating.games_played += 1
        rating.total_play_minutes += minutes
        if participant.user_id == match.winner_id:
            rating.wins += 1
        else:
            rating.losses += 1

    match.status = MatchStatus.CONFIRMED.value
    match.verified_at = utcnow()
    db.flush()

    achievement_service.evaluate(db, match)
    db.commit()


def _season(db: Session, match: Match):
    from app.models import Season

    season = db.get(Season, match.season_id)
    if season is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Temporada de la partida no encontrada"
        )
    return season


def mark_rejected(db: Session, match: Match) -> None:
    """Rechazo de un participante: la partida NO afecta a estadísticas."""
    match.status = MatchStatus.REJECTED.value
    db.add(
        Notification(
            user_id=match.registered_by_id,
            type=NotificationType.MATCH_REJECTED.value,
            title="Resultado rechazado",
            body="Un participante rechazó el resultado de la partida que registraste.",
            link=f"/groups/{match.group_id}/matches/{match.id}",
        )
    )
    publish_user_event(
        match.registered_by_id,
        {
            "type": NotificationType.MATCH_REJECTED.value,
            "title": "Resultado rechazado",
            "body": "Un participante rechazó el resultado de la partida que registraste.",
            "link": f"/groups/{match.group_id}/matches/{match.id}",
        },
    )
    db.commit()


def notify_confirmed(db: Session, match: Match) -> None:
    """Avisa al registrador cuando la partida queda confirmada."""
    db.add(
        Notification(
            user_id=match.registered_by_id,
            type=NotificationType.MATCH_CONFIRMED.value,
            title="Partida confirmada",
            body="Todos los participantes confirmaron el resultado. "
            "Las estadísticas y el ELO ya se han actualizado.",
            link=f"/groups/{match.group_id}/matches/{match.id}",
        )
    )
    publish_user_event(
        match.registered_by_id,
        {
            "type": NotificationType.MATCH_CONFIRMED.value,
            "title": "Partida confirmada",
            "body": "Todos los participantes confirmaron el resultado.",
            "link": f"/groups/{match.group_id}/matches/{match.id}",
        },
    )
    db.commit()
