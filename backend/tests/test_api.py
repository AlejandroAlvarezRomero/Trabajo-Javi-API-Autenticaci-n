"""Tests unitarios y de integración para pytest."""
from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import verify_password
from app.main import app
from app.services import elo_service


@pytest.fixture(scope="session", autouse=True)
def clean_db():
    if settings.DATABASE_URL.startswith("sqlite:///"):
        db_file = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
        if not db_file.is_absolute():
            root = Path(__file__).resolve().parents[1]
            db_file = root / db_file.name
        db_file.unlink(missing_ok=True)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_elo_service_pure():
    """Comprueba las fórmulas puras de ELO y rangos."""
    deltas = elo_service.compute_updates({1: 1200, 2: 1400}, winner_id=1)
    assert deltas[1] > 0
    assert deltas[1] + deltas[2] == 0
    assert elo_service.rank_for(1200).value == "BRONCE"
    assert elo_service.rank_for(2000).value == "DIAMANTE"
    assert elo_service.soft_reset(1600) == 1400


def test_register_and_login_flow(client: TestClient):
    """Prueba registro, login, emisión de cookie HttpOnly y perfil."""
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "pytest_user@test.com", "username": "pytest_user", "password": "password123"},
    )
    assert r.status_code == 201
    user_data = r.json()
    assert user_data["username"] == "pytest_user"
    assert user_data["role"]["name"] == "PLAYER"

    # Login
    r_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pytest_user@test.com", "password": "password123"},
    )
    assert r_login.status_code == 200
    token = r_login.json()["access_token"]
    assert bool(token)
    assert "httponly" in r_login.headers.get("set-cookie", "").lower()

    # /me
    r_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r_me.status_code == 200
    assert r_me.json()["email"] == "pytest_user@test.com"


def test_profile_update(client: TestClient):
    """Actualización de display_name y avatar_url."""
    # Login
    r_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pytest_user@test.com", "password": "password123"},
    )
    token = r_login.json()["access_token"]

    r_patch = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"display_name": "Pytest Master", "avatar_url": "https://example.com/pytest.png"},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["display_name"] == "Pytest Master"
    assert r_patch.json()["avatar_url"] == "https://example.com/pytest.png"


def test_avatar_upload(client: TestClient):
    """Subida de archivo binario de imagen como avatar."""
    r_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pytest_user@test.com", "password": "password123"},
    )
    token = r_login.json()["access_token"]

    # Falso archivo PNG (cabecera básica)
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    r_upload = client.post(
        "/api/v1/auth/avatar",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("profile.png", fake_png, "image/png")},
    )
    assert r_upload.status_code == 200
    avatar_url = r_upload.json()["avatar_url"]
    assert avatar_url.startswith("/uploads/avatars/")

    # Comprobar que el archivo se sirve estáticamente
    r_static = client.get(avatar_url)
    assert r_static.status_code == 200
    assert r_static.content == fake_png



def test_password_recovery(client: TestClient):
    """Solicitud de forgot-password y restablecimiento con nuevo hash."""
    r_forgot = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "pytest_user@test.com"},
    )
    assert r_forgot.status_code == 200
    reset_token = r_forgot.json().get("reset_token")
    assert reset_token is not None

    r_reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "new_secret_pwd_123"},
    )
    assert r_reset.status_code == 200

    # No se puede reusar el mismo token de reset
    r_reuse = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "another_pwd_123"},
    )
    assert r_reuse.status_code == 400

    # Login con nueva contraseña
    r_new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pytest_user@test.com", "password": "new_secret_pwd_123"},
    )
    assert r_new_login.status_code == 200


def test_token_reuse_detection(client: TestClient):
    """Detección de replay attack y revocación de la familia de refresh tokens."""
    r_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pytest_user@test.com", "password": "new_secret_pwd_123"},
    )
    cookie1 = client.cookies.get("refresh_token")

    # Refresh legítimo
    r_ref = client.post("/api/v1/auth/refresh")
    assert r_ref.status_code == 200
    cookie2 = client.cookies.get("refresh_token")
    assert cookie2 != cookie1

    # Reuso del token anterior (replay attack)
    client.cookies.set("refresh_token", cookie1)
    r_replay = client.post("/api/v1/auth/refresh")
    assert r_replay.status_code == 401
    assert "reuso" in r_replay.text.lower()

    # La familia completa quedó revocada
    client.cookies.set("refresh_token", cookie2)
    r_blocked = client.post("/api/v1/auth/refresh")
    assert r_blocked.status_code == 401


def test_rate_limiting_login(client: TestClient):
    """Verifica que tras 5 intentos fallidos consecutivos se bloquea con 429."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "ratelimit@test.com", "username": "ratelimit", "password": "password123"},
    )
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": "ratelimit@test.com", "password": "wrong"})

    r_429 = client.post("/api/v1/auth/login", json={"email": "ratelimit@test.com", "password": "wrong"})
    assert r_429.status_code == 429
    assert "Retry-After" in r_429.headers


def test_groups_and_popular_games_seed(client: TestClient):
    """Creación de grupo con catálogo precargado y transferencia de propiedad."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "owner@test.com", "username": "owner", "password": "password123"},
    )
    r_log_owner = client.post("/api/v1/auth/login", json={"email": "owner@test.com", "password": "password123"})
    token_owner = r_log_owner.json()["access_token"]

    client.post(
        "/api/v1/auth/register",
        json={"email": "member2@test.com", "username": "member2", "password": "password123"},
    )
    r_log_m2 = client.post("/api/v1/auth/login", json={"email": "member2@test.com", "password": "password123"})
    token_m2 = r_log_m2.json()["access_token"]
    user_m2_id = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_m2}"}).json()["id"]

    # Crear grupo con seed_popular = True
    r_grp = client.post(
        "/api/v1/groups",
        json={"name": "Club de Mesa Pytest", "description": "Grupo de prueba", "seed_popular": True},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_grp.status_code == 201
    grp_data = r_grp.json()
    gid = grp_data["id"]
    assert grp_data["game_count"] >= 7

    # El otro usuario se une
    r_join = client.post(
        "/api/v1/groups/join",
        json={"invite_code": grp_data["invite_code"]},
        headers={"Authorization": f"Bearer {token_m2}"},
    )
    assert r_join.status_code == 200

    # Transferir propiedad
    r_transfer = client.post(
        f"/api/v1/groups/{gid}/transfer-ownership",
        json={"new_owner_id": user_m2_id},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_transfer.status_code == 200
    assert r_transfer.json()["owner_id"] == user_m2_id

    # El nuevo propietario borra el grupo
    r_del = client.delete(f"/api/v1/groups/{gid}", headers={"Authorization": f"Bearer {token_m2}"})
    assert r_del.status_code == 204
