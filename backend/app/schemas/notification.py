"""Esquemas Pydantic de notificaciones y logros."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    body: str | None = None
    link: str | None = None
    is_read: bool
    created_at: datetime


class AchievementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    icon_url: str | None = None


class UserAchievementOut(BaseModel):
    achievement: AchievementOut
    group_id: int | None = None
    unlocked_at: datetime
