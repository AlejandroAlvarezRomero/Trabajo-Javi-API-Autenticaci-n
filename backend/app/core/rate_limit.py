"""Limitador de tasa (Rate Limiting) en memoria para protección contra fuerza bruta."""
from __future__ import annotations

import time
from collections import defaultdict
from fastapi import HTTPException, Request, status

# (ip, key) -> lista de marcas de tiempo de intentos fallidos
_failed_attempts: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(
    key: str,
    max_attempts: int = 5,
    window_seconds: int = 60,
) -> None:
    """Verifica si se ha superado el límite de intentos en la ventana de tiempo.
    Lanza HTTP 429 Too Many Requests si se excede."""
    now = time.time()
    attempts = _failed_attempts[key]

    # Filtrar solo los intentos dentro de la ventana de tiempo
    recent = [t for t in attempts if now - t < window_seconds]
    _failed_attempts[key] = recent

    if len(recent) >= max_attempts:
        retry_after = int(window_seconds - (now - recent[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos fallidos. Inténtalo de nuevo en {retry_after} segundos.",
            headers={"Retry-After": str(retry_after)},
        )


def record_failed_attempt(key: str) -> None:
    """Registra un intento fallido."""
    _failed_attempts[key].append(time.time())


def reset_rate_limit(key: str) -> None:
    """Limpia los intentos tras un login exitoso."""
    if key in _failed_attempts:
        del _failed_attempts[key]
