"""Servicio de transmisión en tiempo real de eventos y notificaciones (Server-Sent Events)."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

# user_id -> lista de colas suscritas
_subscribers: dict[int, list[asyncio.Queue[dict]]] = {}
_lock = asyncio.Lock() if hasattr(asyncio, "Lock") else None


def publish_user_event(user_id: int, event_data: dict) -> None:
    """Envía un evento en tiempo real a todas las conexiones activas del usuario."""
    queues = _subscribers.get(user_id, [])
    for q in queues:
        try:
            q.put_nowait(event_data)
        except Exception:
            pass


async def subscribe_user_events(
    user_id: int, ping_interval: int = 25
) -> AsyncGenerator[str, None]:
    """Generador asíncrono para Server-Sent Events (SSE) formateado para el cliente."""
    q: asyncio.Queue[dict] = asyncio.Queue()

    if user_id not in _subscribers:
        _subscribers[user_id] = []
    _subscribers[user_id].append(q)

    # Evento de bienvenida / confirmación de conexión
    yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'user_id': user_id})}\n\n"

    try:
        while True:
            try:
                # Esperar evento con timeout para enviar ping keep-alive
                event_data = await asyncio.wait_for(q.get(), timeout=ping_interval)
                payload = json.dumps(event_data)
                yield f"event: notification\ndata: {payload}\n\n"
            except asyncio.TimeoutError:
                # Ping keep-alive para mantener abierta la conexión HTTP
                yield ": keep-alive\n\n"
    finally:
        # Limpieza al desconectarse el cliente
        if user_id in _subscribers:
            try:
                _subscribers[user_id].remove(q)
                if not _subscribers[user_id]:
                    del _subscribers[user_id]
            except ValueError:
                pass
