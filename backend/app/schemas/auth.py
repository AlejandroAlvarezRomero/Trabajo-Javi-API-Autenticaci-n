"""Esquemas Pydantic (v2) de autenticación y usuarios."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ------------------------------------------------------------------
# Requests
# ------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_.]+$",
        description="Solo letras, números, punto y guion bajo",
    )
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None  # Token de recuperación para entornos de desarrollo/test


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)


class MessageResponse(BaseModel):
    message: str



# ------------------------------------------------------------------
# Responses
# ------------------------------------------------------------------
class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    is_active: bool
    role: RoleOut
    created_at: datetime


class TokenResponse(BaseModel):
    """Access Token para la cabecera `Authorization: Bearer <token>`.
    El Refresh Token NO aparece aquí: viaja en cookie HttpOnly."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos hasta la expiración del access token
