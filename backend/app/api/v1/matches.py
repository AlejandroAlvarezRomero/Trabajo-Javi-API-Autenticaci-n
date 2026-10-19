"""Registro y verificación de partidas (flujo PENDING -> CONFIRMED/REJECTED)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_group_role
from app.core.timeutils import utcnow
from app.db.session import get_db
from app.models import (
    Game,
    GroupMembership,
    Match,
    MatchConfirmation,
    MatchParticipant,
    User,
)
from app.models.enums import GroupRole, MatchStatus
from app.schemas.match import ConfirmationOut, MatchCreate, MatchOut, ParticipantOut
from app.services import match_service

router = APIRouter(prefix="/groups/{group_id}/matches", tags=["Partidas"])


def _load_match(db: Session, group_id: int, match_id: int) -> Match:
    match = db.get(Match, match_id)
    if match is None or match.group_id != group_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Partida no encontrada")
    return match


def match_to_out(db: Session, match: Match) -> MatchOut:
    participant_rows = db.execute(
        select(MatchParticipant, User.username, User.display_name, User.avatar_url)
        .join(User, User.id == MatchParticipant.user_id)
        .where(MatchParticipant.match_id == match.id)
    ).all()
    confirmation_rows = db.execute(
        select(MatchConfirmation, User.username, User.display_name, User.avatar_url)
        .join(User, User.id == MatchConfirmation.user_id)
        .where(MatchConfirmation.match_id == match.id)
    ).all()
    game = db.get(Game, match.game_id)
    return MatchOut(
        id=match.id,
        group_id=match.group_id,
        game_id=match.game_id,
        game_name=game.name if game else None,
        season_id=match.season_id,
        registered_by_id=match.registered_by_id,
        winner_id=match.winner_id,
        status=match.status,
        played_at=match.played_at,
        duration_minutes=match.duration_minutes,
        notes=match.notes,
        created_at=match.created_at,
        verified_at=match.verified_at,
        participants=[
            ParticipantOut(
                user_id=p.user_id,
                username=username,
                display_name=display_name,
                avatar_url=avatar_url,
                placement=p.placement,
                elo_delta=p.elo_delta,
            )
            for p, username, display_name, avatar_url in participant_rows
        ],
        confirmations=[
            ConfirmationOut(
                user_id=c.user_id,
                username=username,
                display_name=display_name,
                avatar_url=avatar_url,
                confirmed=c.confirmed,
                responded_at=c.responded_at,
            )
            for c, username, display_name, avatar_url in confirmation_rows
        ],
    )



@router.get("", response_model=list[MatchOut], summary="Partidas del grupo")
def list_matches(
    group_id: int,
    match_status: MatchStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> list[MatchOut]:
    stmt = select(Match).where(Match.group_id == group_id)
    if match_status is not None:
        stmt = stmt.where(Match.status == match_status.value)
    matches = db.scalars(
        stmt.order_by(Match.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return [match_to_out(db, match) for match in matches]


@router.post(
    "",
    response_model=MatchOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una partida terminada (queda PENDING)",
)
def create_match(
    group_id: int,
    payload: MatchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> MatchOut:
    match = match_service.register_match(
        db, group_id=group_id, registrer_id=user.id, payload=payload
    )
    return match_to_out(db, match)


@router.get("/{match_id}", response_model=MatchOut, summary="Detalle de la partida")
def get_match(
    group_id: int,
    match_id: int,
    db: Session = Depends(get_db),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> MatchOut:
    return match_to_out(db, _load_match(db, group_id, match_id))


@router.post(
    "/{match_id}/confirm",
    response_model=MatchOut,
    summary="Confirmar el resultado (participante)",
)
def confirm_match(
    group_id: int,
    match_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> MatchOut:
    match = _load_match(db, group_id, match_id)
    if match.status != MatchStatus.PENDING.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"La partida ya está en estado {match.status}"
        )

    confirmation = db.scalar(
        select(MatchConfirmation).where(
            MatchConfirmation.match_id == match.id,
            MatchConfirmation.user_id == user.id,
        )
    )
    if confirmation is None:
        if match.registered_by_id == user.id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Tú registraste la partida: se da por confirmada",
            )
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Solo los participantes pueden confirmar"
        )
    if confirmation.confirmed is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya has respondido a esta partida")

    confirmation.confirmed = True
    confirmation.responded_at = utcnow()
    db.commit()

    if match_service.finalize_if_ready(db, match):
        match_service.notify_confirmed(db, match)

    return match_to_out(db, match)


@router.post(
    "/{match_id}/reject",
    response_model=MatchOut,
    summary="Rechazar el resultado (participante)",
)
def reject_match(
    group_id: int,
    match_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> MatchOut:
    match = _load_match(db, group_id, match_id)
    if match.status != MatchStatus.PENDING.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"La partida ya está en estado {match.status}"
        )

    confirmation = db.scalar(
        select(MatchConfirmation).where(
            MatchConfirmation.match_id == match.id,
            MatchConfirmation.user_id == user.id,
        )
    )
    if confirmation is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Solo los participantes pueden rechazar"
        )
    if confirmation.confirmed is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya has respondido a esta partida")

    confirmation.confirmed = False
    confirmation.responded_at = utcnow()
    db.commit()
    match_service.mark_rejected(db, match)

    return match_to_out(db, match)


@router.post(
    "/{match_id}/cancel",
    response_model=MatchOut,
    summary="Anular una partida pendiente (Gestor o Admin)",
)
def cancel_match(
    group_id: int,
    match_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _manager: GroupMembership = Depends(require_group_role(GroupRole.MANAGER)),
) -> MatchOut:
    match = _load_match(db, group_id, match_id)
    if match.status != MatchStatus.PENDING.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"La partida ya está en estado {match.status}"
        )
    # Moderación de resultados: capacidad del Gestor de Grupo
    match.status = MatchStatus.CANCELLED.value
    db.commit()
    return match_to_out(db, match)
