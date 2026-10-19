"""Temporadas (3 meses) y ratings ELO históricos por temporada."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutils import utcnow
from app.db.base import Base
from app.models.enums import Rank

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.user import User

SEASON_DURATION_DAYS = 92  # ~3 meses
SEASON_START_ELO = 1200    # ELO inicial de cada temporada (soft reset)


class Season(Base):
    """Temporada de 3 meses dentro de un grupo.

    Al finalizar: se marca is_active=False, se crea la siguiente y los
    ratings hacen soft reset (regresión a la media). El histórico se
    conserva en SeasonRating."""

    __tablename__ = "seasons"
    __table_args__ = (
        UniqueConstraint("group_id", "number", name="uq_group_season_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3...
    name: Mapped[str] = mapped_column(String(100), default="Temporada 1")
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )

    group: Mapped["Group"] = relationship(back_populates="seasons")
    ratings: Mapped[list["SeasonRating"]] = relationship(
        back_populates="season", cascade="all, delete-orphan"
    )


class SeasonRating(Base):
    """ELO y estadísticas acumuladas de un usuario en una temporada/grupo.

    Es la fuente de verdad para rangos, win rate y clasificaciones.
    Al terminar la temporada queda congelado como histórico."""

    __tablename__ = "season_ratings"
    __table_args__ = (
        UniqueConstraint("season_id", "user_id", name="uq_season_user_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False, index=True)
    # Denormalizado para consultas de clasificación por grupo sin join a Season
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    elo: Mapped[int] = mapped_column(Integer, default=SEASON_START_ELO, nullable=False)
    rank: Mapped[str] = mapped_column(String(20), default=Rank.HIERRO.value, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    games_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_play_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    season: Mapped["Season"] = relationship(back_populates="ratings")
    user: Mapped["User"] = relationship(back_populates="season_ratings")

    @property
    def win_rate(self) -> float:
        """Porcentaje de victorias (0-100)."""
        if self.games_played == 0:
            return 0.0
        return round(self.wins * 100.0 / self.games_played, 1)
