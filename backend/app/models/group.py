"""Grupos privados y membresías (Gestor de Grupo / Jugador)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutils import utcnow
from app.db.base import Base
from app.models.enums import GroupRole

if TYPE_CHECKING:
    from app.models.game import Game
    from app.models.match import Match
    from app.models.season import Season
    from app.models.user import User


class Group(Base):
    """Entorno privado: tiene su catálogo de juegos, miembros y temporadas."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    # Código corto para que otros usuarios se unan sin invitación directa
    invite_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(
        back_populates="owned_groups", foreign_keys=[owner_id]
    )
    memberships: Mapped[list["GroupMembership"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    games: Mapped[list["Game"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    seasons: Mapped[list["Season"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    # Para que borrar un grupo limpie también sus partidas (y sus hijos)
    matches: Mapped[list["Match"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )



class GroupMembership(Base):
    """Unión entre Usuario y Grupo, con rol propio del grupo."""

    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_membership_group_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # GROUP_MANAGER = creador/gestor del grupo, MEMBER = jugador estándar
    role: Mapped[str] = mapped_column(
        String(20), default=GroupRole.MEMBER.value, nullable=False
    )
    joined_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )

    group: Mapped["Group"] = relationship(back_populates="memberships")
    # Hay dos FK hacia users (user_id y joined_by_id): hay que desambiguar
    user: Mapped["User"] = relationship(
        back_populates="memberships", foreign_keys=[user_id]
    )

    @property
    def group_role(self) -> GroupRole:
        return GroupRole(self.role)
