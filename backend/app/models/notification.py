"""Notificaciones push/in-app para los usuarios."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutils import utcnow
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Notification(Base):
    """Aviso dirigido a un usuario.

    Ejemplo clave: al registrar una partida en estado PENDING se crea una
    notificación MATCH_CONFIRMATION para cada otro participante."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    # Deep link para que el frontend abra la partida/grupo correspondiente
    link: Mapped[str | None] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()
