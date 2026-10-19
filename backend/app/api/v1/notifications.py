"""Notificaciones in-app del usuario autenticado."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import Notification, User
from app.schemas.notification import NotificationOut

router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


@router.get("", response_model=list[NotificationOut], summary="Mis notificaciones")
def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    return list(
        db.scalars(stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)).all()
    )


@router.post(
    "/{notification_id}/read",
    response_model=NotificationOut,
    summary="Marcar una notificación como leída",
)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificación no encontrada")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/read-all", summary="Marcar todas como leídas")
def mark_all_read(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int]:
    result = db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
    return {"updated": result.rowcount or 0}


@router.get(
    "/stream",
    summary="Canal en tiempo real de notificaciones (Server-Sent Events / SSE)",
)
async def notification_stream(
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    from fastapi.responses import StreamingResponse
    from app.services.event_service import subscribe_user_events

    return StreamingResponse(
        subscribe_user_events(user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

