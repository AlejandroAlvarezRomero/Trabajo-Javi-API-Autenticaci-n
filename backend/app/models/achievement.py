"""Logros/insignias desbloqueables y su asignación automática."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutils import utcnow
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Achievement(Base):
    """Catálogo maestro de insignias.

    `condition` guarda la regla en JSON que evalúa el AchievementService
    tras cada partida confirmada, p.ej.:
      {"type": "first_win_game", "game_id": 12}
      {"type": "win_streak", "streak": 5}
      {"type": "games_played", "threshold": 50}"""

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # FIRST_BLOOD...
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(500))
    condition: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )

    user_unlocks: Mapped[list["UserAchievement"]] = relationship(
        back_populates="achievement", cascade="all, delete-orphan"
    )


class UserAchievement(Base):
    """Desbloqueo concreto de una insignia por un usuario."""

    __tablename__ = "user_achievements"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "achievement_id", "group_id", name="uq_user_achievement_group"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievements.id"), nullable=False, index=True
    )
    # None = logro global de la plataforma; con valor = logro dentro del grupo
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), index=True)
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="achievements")
    achievement: Mapped["Achievement"] = relationship(back_populates="user_unlocks")
