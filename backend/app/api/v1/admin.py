"""Panel del Administrador Global: moderación de usuarios y métricas."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_global_admin
from app.core.timeutils import utcnow
from app.db.session import get_db
from app.models import Group, Match, RefreshToken, Role, User
from app.models.enums import MatchStatus
from app.schemas.auth import UserOut
from app.schemas.stats import PlatformOverview, UserAdminUpdate

router = APIRouter(
    prefix="/admin",
    tags=["Administración"],
    dependencies=[Depends(require_global_admin)],  # todo el router exige ADMIN
)


@router.get("/overview", response_model=PlatformOverview, summary="Métricas globales")
def overview(db: Session = Depends(get_db)) -> PlatformOverview:
    return PlatformOverview(
        users=db.scalar(select(func.count(User.id))) or 0,
        groups=db.scalar(select(func.count(Group.id))) or 0,
        matches_pending=db.scalar(
            select(func.count(Match.id)).where(
                Match.status == MatchStatus.PENDING.value
            )
        )
        or 0,
        matches_confirmed=db.scalar(
            select(func.count(Match.id)).where(
                Match.status == MatchStatus.CONFIRMED.value
            )
        )
        or 0,
    )


@router.get("/users", response_model=list[UserOut], summary="Listar usuarios")
def list_users(
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[User]:
    stmt = select(User)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(User.username.ilike(pattern) | User.email.ilike(pattern))
    return list(db.scalars(stmt.order_by(User.id.asc()).offset(offset).limit(limit)).all())


@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    summary="Moderar usuario: activar/desactivar o cambiar rol",
)
def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_user),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    if payload.is_active is False and target.id == admin.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "No puedes desactivar tu propia cuenta"
        )

    if payload.role is not None:
        role = db.scalar(select(Role).where(Role.name == payload.role))
        if role is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Rol no válido")
        target.role_id = role.id

    if payload.is_active is not None:
        target.is_active = payload.is_active
        if not payload.is_active:
            # Cuenta suspendida: revoca todos sus refresh tokens activos
            db.execute(
                RefreshToken.__table__.update()
                .where(
                    RefreshToken.user_id == target.id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=utcnow())
            )

    db.commit()
    db.refresh(target)
    return target


@router.get(
    "/roles",
    summary="Roles globales disponibles",
)
def list_roles(db: Session = Depends(get_db)) -> list[dict]:
    roles = db.scalars(select(Role).order_by(Role.id)).all()
    return [{"id": r.id, "name": r.name, "description": r.description} for r in roles]
