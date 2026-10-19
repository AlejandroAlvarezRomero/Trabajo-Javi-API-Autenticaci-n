"""Endpoints de logros/insignias: catálogo y desbloqueos del usuario."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Achievement, User, UserAchievement
from app.schemas.notification import AchievementOut, UserAchievementOut

router = APIRouter(tags=["Logros"])


@router.get(
    "/achievements",
    response_model=list[AchievementOut],
    summary="Catálogo de insignias disponibles",
)
def list_achievements(db: Session = Depends(get_db)) -> list[Achievement]:
    return list(db.scalars(select(Achievement).order_by(Achievement.id)).all())


@router.get(
    "/users/me/achievements",
    response_model=list[UserAchievementOut],
    summary="Insignias desbloqueadas por mi",
)
def my_achievements(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[UserAchievement]:
    return list(
        db.scalars(
            select(UserAchievement)
            .options(joinedload(UserAchievement.achievement))
            .where(UserAchievement.user_id == user.id)
            .order_by(UserAchievement.unlocked_at.desc())
        ).unique().all()
    )
