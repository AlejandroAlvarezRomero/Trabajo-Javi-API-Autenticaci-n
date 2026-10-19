"""Seguridad: hash de contraseñas (passlib + bcrypt) y tokens JWT dual."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt incluye salt automático en cada hash (no hace falta guardarlo aparte)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

REFRESH_TOKEN_TYPE = "refresh"
ACCESS_TOKEN_TYPE = "access"
RESET_PASSWORD_TOKEN_TYPE = "pwd_reset"


class AuthError(Exception):
    """Error de autenticación controlado (se traduce a HTTP 401 en deps)."""

    def __init__(self, detail: str = "Token inválido o expirado") -> None:
        self.detail = detail
        super().__init__(detail)


# ------------------------------------------------------------------
# Contraseñas
# ------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Genera un hash con salt integrado (bcrypt)."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara en texto plano con el hash almacenado de forma segura."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------
# Tokens JWT
# ------------------------------------------------------------------
def _encode(claims: dict, lifetime: timedelta) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": now + lifetime,
    }
    # jti (token id) permite revocar tokens concretos (rotación del refresh)
    claims.setdefault("jti", uuid.uuid4().hex)
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    """Access Token de corta duración: se envía en la cabecera Authorization."""
    return _encode(
        {"sub": str(user_id), "type": ACCESS_TOKEN_TYPE, "role": role},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> tuple[str, str]:
    """Refresh Token de larga duración: se guarda en cookie HttpOnly.
    Devuelve (token, jti) para persistir el jti y poder revocarlo."""
    jti = uuid.uuid4().hex
    token = _encode(
        {"sub": str(user_id), "type": REFRESH_TOKEN_TYPE, "jti": jti},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return token, jti


def create_reset_password_token(user_id: int, pwd_fingerprint: str) -> str:
    """Token de recuperación de contraseña temporal (15 min) e invalidable tras cambio."""
    return _encode(
        {"sub": str(user_id), "type": RESET_PASSWORD_TOKEN_TYPE, "pfp": pwd_fingerprint},
        timedelta(minutes=15),
    )


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """Decodifica y valida firma + expiración. Lanza AuthError si falla."""
    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:  # expirado, firma inválida, mal formado...
        raise AuthError("Token inválido o expirado") from exc

    if expected_type is not None and claims.get("type") != expected_type:
        raise AuthError("Tipo de token incorrecto")
    return claims
