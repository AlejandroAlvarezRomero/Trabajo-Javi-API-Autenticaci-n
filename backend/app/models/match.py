"""Partidas: registro, participantes y verificación por confirmación."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutils import utcnow
from app.db.base import Base
from app.models.enums import MatchStatus

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.group import Group
    from app.models.season import Season
    from app.models.user import User


class Match(Base):
    """Partida terminada registrada por un jugador.

    Flujo: PENDING -> (todos confirman) CONFIRMED | (alguien rechaza) REJECTED.
    Solo las CONFIRMED afectan a ELO y estadísticas."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("group_games.id"), nullable=False, index=True)
    # Congela la temporada vigente en el momento de registrar (evita carreras)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False, index=True)
    registered_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    winner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        String(20), default=MatchStatus.PENDING.value, nullable=False, index=True
    )
    played_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)  # cuando pasó a CONFIRMED

    group: Mapped["Group"] = relationship(back_populates="matches")
    game: Mapped["Game"] = relationship()
    season: Mapped["Season"] = relationship()
    registered_by: Mapped["User"] = relationship(foreign_keys=[registered_by_id])
    winner: Mapped["User"] = relationship(foreign_keys=[winner_id])

    participants: Mapped[list["MatchParticipant"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )
    confirmations: Mapped[list["MatchConfirmation"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )

    @property
    def is_verified(self) -> bool:
        return self.status == MatchStatus.CONFIRMED.value


class MatchParticipant(Base):
    """Jugador que participó en la partida (y su variación de ELO al confirmar)."""

    __tablename__ = "match_participants"
    __table_args__ = (
        UniqueConstraint("match_id", "user_id", name="uq_match_participant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    placement: Mapped[int | None] = mapped_column(Integer)  # 1 = ganador
    elo_delta: Mapped[int | None] = mapped_column(Integer)  # aplicado al confirmar

    match: Mapped["Match"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship()


class MatchConfirmation(Base):
    """Verificación de cada jugador implicado en la partida.

    Se considera CONFIRMED cuando todos los participantes distintos del
    registrador tienen confirmed=True (el registrador da por hecho su visto)."""

    __tablename__ = "match_confirmations"
    __table_args__ = (
        UniqueConstraint("match_id", "user_id", name="uq_match_confirmation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    confirmed: Mapped[bool | None] = mapped_column()  # True = acepta, False = rechaza
    responded_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )

    match: Mapped["Match"] = relationship(back_populates="confirmations")
    user: Mapped["User"] = relationship()
