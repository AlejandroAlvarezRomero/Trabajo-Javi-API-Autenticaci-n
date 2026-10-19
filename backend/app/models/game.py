"""Catálogo de juegos de cada grupo (metadatos enriquecidos desde BGG)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutils import utcnow
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.group import Group


class Game(Base):
    """Juego dentro del catálogo de un grupo.

    Al añadirlo, el backend llama a la API de BoardGameGeek (xmlapi2)
    y rellena imagen, descripción, número de jugadores y duración."""

    __tablename__ = "group_games"
    __table_args__ = (
        UniqueConstraint("group_id", "bgg_id", name="uq_group_bgg_game"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False, index=True)

    # --- Metadatos de BoardGameGeek ---
    bgg_id: Mapped[int | None] = mapped_column(Integer, index=True)  # id en BGG (thing/XXXX)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    min_players: Mapped[int | None] = mapped_column(Integer)
    max_players: Mapped[int | None] = mapped_column(Integer)
    avg_playtime_minutes: Mapped[int | None] = mapped_column(Integer)
    year_published: Mapped[int | None] = mapped_column(Integer)
    bgg_ranking: Mapped[int | None] = mapped_column(Integer)
    bgg_rating: Mapped[float | None] = mapped_column()  # rating medio BGG

    added_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, server_default=func.now(), nullable=False
    )

    group: Mapped["Group"] = relationship(back_populates="games")
