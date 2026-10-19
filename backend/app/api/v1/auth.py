"""Endpoints de autenticación: registro, login, refresh y logout.

Esquema de seguridad dual:
  - Access Token (JWT, 15 min)  -> cabecera Authorization: Bearer
  - Refresh Token (JWT, 14 días)-> cookie HttpOnly (no accesible desde JS)
Cada refresh rota el jti anterior (un solo uso) y lo revoca en BD."""
from __future__ import annotations

import uuid
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session


from app.core.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import (
    check_rate_limit,
    record_failed_attempt,
    reset_rate_limit,
)
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    RESET_PASSWORD_TOKEN_TYPE,
    AuthError,
    create_access_token,
    create_refresh_token,
    create_reset_password_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.timeutils import utcnow
from app.db.session import get_db
from app.models import RefreshToken, Role, User
from app.models.enums import GlobalRole
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserOut,
    UserProfileUpdate,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = f"{settings.API_V1_PREFIX}/auth"  # solo se envía a /auth/*
_GENERIC_LOGIN_ERROR = "Email o contraseña incorrectos"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _set_refresh_cookie(response: Response, token: str) -> None:
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,                       # inaccesible desde JavaScript
        secure=settings.COOKIE_SECURE,       # solo HTTPS en producción
        samesite=settings.COOKIE_SAMESITE,   # mitigación CSRF
        path=REFRESH_COOKIE_PATH,
    )


def _issue_session(db: Session, user: User, response: Response) -> TokenResponse:
    """Crea el par de tokens y persiste el jti del refresh para revocación."""
    access_token = create_access_token(user_id=user.id, role=user.role.name)
    refresh_token, jti = create_refresh_token(user_id=user.id)

    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            expires_at=utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    user.last_login_at = utcnow()
    db.commit()

    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.scalar(
        select(User).where(
            or_(User.email == payload.email, User.username == payload.username)
        )
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El email o el nombre de usuario ya está en uso",
        )

    player_role = db.scalar(select(Role).where(Role.name == GlobalRole.PLAYER.value))
    if player_role is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Rol por defecto no encontrado (falta seed de roles)",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),  # bcrypt + salt
        role=player_role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login: devuelve Access Token y fija cookie de Refresh Token",
)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{payload.email}"
    check_rate_limit(rate_key, max_attempts=5, window_seconds=60)

    user = db.scalar(select(User).where(User.email == payload.email))
    # Mensaje genérico: no revelar si el email existe o no (user enumeration)
    if user is None or not verify_password(payload.password, user.hashed_password):
        record_failed_attempt(rate_key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _GENERIC_LOGIN_ERROR)
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cuenta desactivada")

    reset_rate_limit(rate_key)
    return _issue_session(db, user, response)



@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Intercambia el Refresh Token (cookie) por un nuevo Access Token",
)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Refresh Token no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_token(token, expected_type=REFRESH_TOKEN_TYPE)
    except AuthError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # El jti debe existir en BD, sin revocar y sin expirar (rotación)
    stored = db.scalar(select(RefreshToken).where(RefreshToken.jti == claims["jti"]))
    now = utcnow()
    if stored is None or stored.expires_at < now:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Refresh Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if stored.revoked_at is not None:
        # DETECCIÓN DE REUSO DE REFRESH TOKEN (posible robo de cookie / replay attack)
        # Se revoca inmediatamente toda la familia de sesiones activas del usuario
        user_id = stored.user_id
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        response.delete_cookie(
            key=REFRESH_COOKIE_NAME,
            path=REFRESH_COOKIE_PATH,
            httponly=True,
            samesite=settings.COOKIE_SAMESITE,
            secure=settings.COOKIE_SECURE,
        )
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Intento de reuso de token detectado. Todas las sesiones activas han sido revocadas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no válido")

    stored.revoked_at = now  # consumo del token: solo puede usarse una vez
    db.commit()

    return _issue_session(db, user, response)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoca el Refresh Token y borra la cookie",
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> None:
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if token:
        try:
            claims = decode_token(token, expected_type=REFRESH_TOKEN_TYPE)
            stored = db.scalar(
                select(RefreshToken).where(RefreshToken.jti == claims["jti"])
            )
            if stored is not None and stored.revoked_at is None:
                stored.revoked_at = utcnow()
                db.commit()
        except AuthError:
            pass  # token corrupto/expirado: solo limpiar la cookie

    response.status_code = status.HTTP_204_NO_CONTENT
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
    )


@router.get("/me", response_model=UserOut, summary="Usuario autenticado actual")
def read_current_user(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut, summary="Actualizar perfil y avatar")
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip() or None
    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url.strip() or None
    db.commit()
    db.refresh(user)
    return user


_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
_MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/avatar", response_model=UserOut, summary="Subir imagen de avatar")
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Formato no permitido. Usa una imagen ({', '.join(sorted(_ALLOWED_IMAGE_EXTENSIONS))})",
        )

    content = file.file.read()
    if len(content) > _MAX_AVATAR_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La imagen no puede superar los 5 MB",
        )

    uploads_dir = Path(__file__).resolve().parents[3] / "uploads" / "avatars"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    filename = f"user_{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    target_path = uploads_dir / filename
    target_path.write_bytes(content)

    user.avatar_url = f"/uploads/avatars/{filename}"
    db.commit()
    db.refresh(user)
    return user



@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Solicitar restablecimiento de contraseña",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active:
        # Mensaje idéntico para mitigar enumeración de correos
        return ForgotPasswordResponse(
            message="Si el correo está registrado, se han generado instrucciones para restablecer la contraseña"
        )

    # Huella basada en la terminación del hash actual (si cambia la contraseña, el token expira automáticamente)
    pwd_fingerprint = user.hashed_password[-10:]
    token = create_reset_password_token(user.id, pwd_fingerprint)
    return ForgotPasswordResponse(
        message="Instrucciones generadas correctamente",
        reset_token=token,
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Restablecer contraseña usando token temporal",
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        claims = decode_token(payload.token, expected_type=RESET_PASSWORD_TOKEN_TYPE)
    except AuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, exc.detail) from exc

    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Usuario no válido")

    if user.hashed_password[-10:] != claims.get("pfp"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Este token de restablecimiento ya ha sido utilizado o ha expirado",
        )

    user.hashed_password = hash_password(payload.new_password)
    # Revocar todas las sesiones previas (Refresh Tokens) por seguridad
    now = utcnow()
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()

    return MessageResponse(
        message="Contraseña restablecida con éxito. Inicia sesión con tus nuevas credenciales."
    )

