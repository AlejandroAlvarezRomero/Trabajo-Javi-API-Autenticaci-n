"""Endpoints de grupos privados: crear, unirse, miembros y eliminación."""
from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_global_admin, require_group_role
from app.core.timeutils import utcnow
from app.db.seed import seed_popular_games
from app.db.session import get_db
from app.models import Game, Group, GroupMembership, Season, SeasonRating, User
from app.models.enums import GlobalRole, GroupRole
from app.models.season import SEASON_DURATION_DAYS, SEASON_START_ELO
from app.schemas.group import (
    GroupCreate,
    GroupJoinRequest,
    GroupOut,
    GroupTransferOwnership,
    MemberOut,
    MemberRoleUpdate,
)
from app.services import season_service

router = APIRouter(prefix="/groups", tags=["Grupos"])

# Sin 0/O ni 1/I para evitar confusiones al teclear el código
_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _new_invite_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(6))
        exists = db.scalar(select(Group.id).where(Group.invite_code == code))
        if exists is None:
            return code


def _group_out(db: Session, group: Group, user: User) -> GroupOut:
    membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group.id,
            GroupMembership.user_id == user.id,
        )
    )
    member_count = (
        db.scalar(
            select(func.count(GroupMembership.id)).where(
                GroupMembership.group_id == group.id
            )
        )
        or 0
    )
    game_count = (
        db.scalar(select(func.count(Game.id)).where(Game.group_id == group.id)) or 0
    )
    return GroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        invite_code=group.invite_code,
        owner_id=group.owner_id,
        created_at=group.created_at,
        my_role=membership.role if membership else None,
        member_count=member_count,
        game_count=game_count,
    )


@router.post(
    "",
    response_model=GroupOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un grupo privado (el creador queda como Gestor)",
)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GroupOut:
    group = Group(
        name=payload.name,
        description=payload.description,
        invite_code=_new_invite_code(db),
        owner_id=user.id,
    )
    db.add(group)
    db.flush()
    db.add(
        GroupMembership(
            group_id=group.id, user_id=user.id, role=GroupRole.MANAGER.value
        )
    )
    # Primera temporada activa desde el minuto cero
    season = Season(
        group_id=group.id,
        number=1,
        name="Temporada 1",
        start_date=utcnow(),
        end_date=utcnow() + timedelta(days=SEASON_DURATION_DAYS),
        is_active=True,
    )
    db.add(season)
    db.flush()
    db.add(
        SeasonRating(
            season_id=season.id,
            group_id=group.id,
            user_id=user.id,
            elo=SEASON_START_ELO,
        )
    )
    if payload.seed_popular:
        seed_popular_games(db, group_id=group.id, added_by_id=user.id)
    db.commit()
    db.refresh(group)
    return _group_out(db, group, user)



@router.get("", response_model=list[GroupOut], summary="Grupos del usuario actual")
def list_my_groups(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[GroupOut]:
    groups = db.scalars(
        select(Group)
        .join(GroupMembership, GroupMembership.group_id == Group.id)
        .where(GroupMembership.user_id == user.id)
        .order_by(Group.id.desc())
    ).all()
    return [_group_out(db, group, user) for group in groups]


@router.post(
    "/join",
    response_model=GroupOut,
    summary="Unirse a un grupo con su código de invitación",
)
def join_group(
    payload: GroupJoinRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GroupOut:
    code = payload.invite_code.strip().upper()
    group = db.scalar(select(Group).where(Group.invite_code == code))
    if group is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Código de invitación no válido"
        )

    existing = db.scalar(
        select(GroupMembership.id).where(
            GroupMembership.group_id == group.id,
            GroupMembership.user_id == user.id,
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya eres miembro de este grupo")

    db.add(
        GroupMembership(
            group_id=group.id,
            user_id=user.id,
            role=GroupRole.MEMBER.value,
            joined_by_id=group.owner_id,
        )
    )
    db.flush()
    # Rating de la temporada vigente para aparezar en la clasificación
    active = season_service.ensure_active_season(db, group.id)
    season_service.get_or_create_rating(db, group.id, active, user.id)
    db.commit()
    db.refresh(group)
    return _group_out(db, group, user)


@router.get(
    "/{group_id}",
    response_model=GroupOut,
    summary="Detalle del grupo",
)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> GroupOut:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")
    return _group_out(db, group, user)


@router.get(
    "/{group_id}/members",
    response_model=list[MemberOut],
    summary="Miembros del grupo",
)
def list_members(
    group_id: int,
    db: Session = Depends(get_db),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> list[MemberOut]:
    rows = db.execute(
        select(GroupMembership, User)
        .join(User, User.id == GroupMembership.user_id)
        .where(GroupMembership.group_id == group_id)
        .order_by(GroupMembership.joined_at.asc())
    ).all()
    return [
        MemberOut(
            user_id=u.id,
            username=u.username,
            display_name=u.display_name,
            avatar_url=u.avatar_url,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m, u in rows
    ]


@router.patch(
    "/{group_id}/members/{user_id}",
    response_model=MemberOut,
    summary="Cambiar el rol de un miembro (solo Gestor)",
)
def update_member_role(
    group_id: int,
    user_id: int,
    payload: MemberRoleUpdate,
    db: Session = Depends(get_db),
    _manager: GroupMembership = Depends(require_group_role(GroupRole.MANAGER)),
) -> MemberOut:
    membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Miembro no encontrado")
    group = db.get(Group, group_id)
    if group is not None and group.owner_id == user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "No se puede cambiar el rol del propietario"
        )

    membership.role = payload.role
    db.commit()
    db.refresh(membership)
    target = db.get(User, user_id)
    return MemberOut(
        user_id=target.id,
        username=target.username,
        display_name=target.display_name,
        avatar_url=target.avatar_url,
        role=membership.role,
        joined_at=membership.joined_at,
    )



@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Expulsar a un miembro (solo Gestor)",
)
def remove_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _manager: GroupMembership = Depends(require_group_role(GroupRole.MANAGER)),
) -> None:
    if user_id == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Usa el endpoint de salida del grupo"
        )
    group = db.get(Group, group_id)
    if group is not None and group.owner_id == user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "No se puede expulsar al propietario"
        )
    membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Miembro no encontrado")
    db.delete(membership)
    db.commit()


@router.post(
    "/{group_id}/leave",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Salir del grupo",
)
def leave_group(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _member: GroupMembership = Depends(require_group_role(GroupRole.MEMBER)),
) -> None:
    group = db.get(Group, group_id)
    if group is not None and group.owner_id == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "El propietario no puede salir; transfiere o elimina el grupo",
        )
    db.delete(_member)
    db.commit()


@router.post(
    "/{group_id}/transfer-ownership",
    response_model=GroupOut,
    summary="Transferir la propiedad del grupo a otro miembro (solo propietario o Administrador Global)",
)
def transfer_group_ownership(
    group_id: int,
    payload: GroupTransferOwnership,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _manager: GroupMembership = Depends(require_group_role(GroupRole.MANAGER)),
) -> GroupOut:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")

    is_admin = user.role is not None and user.role.name == GlobalRole.ADMIN.value
    if group.owner_id != user.id and not is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el propietario actual o un Administrador Global pueden transferir la propiedad",
        )

    if payload.new_owner_id == group.owner_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "El usuario ya es el propietario del grupo"
        )

    new_owner_membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == payload.new_owner_id,
        )
    )
    if new_owner_membership is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "El nuevo propietario debe ser un miembro activo del grupo",
        )

    # El nuevo propietario debe ser MANAGER
    new_owner_membership.role = GroupRole.MANAGER.value
    group.owner_id = payload.new_owner_id
    db.commit()
    db.refresh(group)
    return _group_out(db, group, user)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar el grupo (propietario o Administrador Global)",
)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _manager: GroupMembership = Depends(require_group_role(GroupRole.MANAGER)),
) -> None:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")
    is_admin = user.role is not None and user.role.name == GlobalRole.ADMIN.value
    if group.owner_id != user.id and not is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el propietario o un Administrador Global pueden eliminar el grupo",
        )
    db.delete(group)  # cascada: miembros, juegos, temporadas, ratings y partidas
    db.commit()
