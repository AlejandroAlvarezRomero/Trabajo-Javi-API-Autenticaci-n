"""Smoke test: sistema de autenticación dual (JWT + cookie) y ELO puro.

Ejecutar desde `backend/`:
    .venv\\Scripts\\python.exe tests\\smoke_auth.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# BD SQLite limpia para que el test sea determinista (hay que ejecutarlo desde backend/)
from app.core.config import settings  # noqa: E402

if settings.DATABASE_URL.startswith("sqlite:///"):
    db_file = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    if not db_file.is_absolute():
        db_file = ROOT / db_file.name
    db_file.unlink(missing_ok=True)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import elo_service  # noqa: E402

results = []


def check(name, condition, extra=""):
    results.append((name, bool(condition), extra))
    print(("OK  " if condition else "FAIL") + f" {name} {extra}")


with TestClient(app) as client:

    # 1. Registro
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "ana@test.com", "username": "ana", "password": "secreta123"},
    )
    check("register 201", r.status_code == 201, str(r.status_code))
    body = r.json()
    check("register role=PLAYER", body.get("role", {}).get("name") == "PLAYER")

    # 2. Registro duplicado
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "ana@test.com", "username": "otro", "password": "secreta123"},
    )
    check("register duplicado 409", r.status_code == 409, str(r.status_code))

    # 3. Login con contraseña incorrecta
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "ana@test.com", "password": "mala1234"},
    )
    check("login malo 401", r.status_code == 401, str(r.status_code))

    # 4. Login correcto
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "ana@test.com", "password": "secreta123"},
    )
    check("login 200", r.status_code == 200, str(r.status_code))
    token1 = r.json().get("access_token")
    check("access_token emitido", bool(token1))
    set_cookie = r.headers.get("set-cookie", "")
    check("cookie HttpOnly", "httponly" in set_cookie.lower(), set_cookie[:80])

    # 5. /me con Bearer
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    check("me 200", r.status_code == 200 and r.json()["username"] == "ana")

    # 6. /me sin token
    r = client.get("/api/v1/auth/me")
    check("me sin token 401", r.status_code == 401, str(r.status_code))

    # 7. Refresh con cookie (rotación)
    cookie1 = client.cookies.get("refresh_token")
    r = client.post("/api/v1/auth/refresh")
    check("refresh 200", r.status_code == 200, str(r.status_code))
    token2 = r.json().get("access_token")
    check("nuevo access token distinto", token2 and token2 != token1)
    cookie2 = client.cookies.get("refresh_token")

    # 7b. Detección de reuso de refresh token viejo (ataque de replay)
    client.cookies.set("refresh_token", cookie1)
    r_reuse = client.post("/api/v1/auth/refresh")
    check("reuso de refresh token detectado 401", r_reuse.status_code == 401 and "reuso" in r_reuse.text.lower())

    # La familia completa de tokens quedó revocada
    client.cookies.set("refresh_token", cookie2)
    r_family = client.post("/api/v1/auth/refresh")
    check("familia revocada tras reuso 401", r_family.status_code == 401)

    # 8. Re-login para probar logout normal
    r = client.post("/api/v1/auth/login", json={"email": "ana@test.com", "password": "secreta123"})
    token3 = r.json().get("access_token")
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token3}"})
    check("token nuevo válido en /me", r.status_code == 200)

    # 9. Actualización de perfil y avatar (PATCH /me)
    r_patch = client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token3}"},
        json={"display_name": "Ana Jugadora", "avatar_url": "https://example.com/avatar.png"},
    )
    check("patch me 200", r_patch.status_code == 200, str(r_patch.status_code))
    check("display_name y avatar actualizados", r_patch.json().get("display_name") == "Ana Jugadora" and r_patch.json().get("avatar_url") == "https://example.com/avatar.png")

    # 10. Logout
    r = client.post("/api/v1/auth/logout")
    check("logout 204", r.status_code == 204, str(r.status_code))
    r = client.post("/api/v1/auth/refresh")
    check("refresh tras logout 401", r.status_code == 401, str(r.status_code))

    # 11. Recuperación de contraseña (forgot-password + reset-password)
    r_forgot = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "ana@test.com"},
    )
    check("forgot password 200", r_forgot.status_code == 200)
    reset_tok = r_forgot.json().get("reset_token")
    check("reset_token generado", bool(reset_tok))

    # Reset de contraseña
    r_reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_tok, "new_password": "nuevaPassword123"},
    )
    check("reset password 200", r_reset.status_code == 200)

    # Reuso del mismo token debe fallar
    r_reuse_reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_tok, "new_password": "otraPassword123"},
    )
    check("token reset no reusable 400", r_reuse_reset.status_code == 400)

    # Login con nueva contraseña
    r_new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "ana@test.com", "password": "nuevaPassword123"},
    )
    check("login con nueva contraseña 200", r_new_login.status_code == 200)

    # 12. Rate limiting en /auth/login (5 intentos fallidos -> 429)
    # Creamos un usuario de prueba para no bloquear a ana
    client.post("/api/v1/auth/register", json={"email": "brute@test.com", "username": "brute", "password": "password123"})
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": "brute@test.com", "password": "incorrecta"})
    r_blocked = client.post("/api/v1/auth/login", json={"email": "brute@test.com", "password": "incorrecta"})
    check("rate limiting login 429 tras 5 fallos", r_blocked.status_code == 429, str(r_blocked.status_code))


# --- ELO (funciones puras) ---
deltas = elo_service.compute_updates({1: 1200, 2: 1400}, winner_id=1)
check("ELO: ganar contra +200 da ~+24", deltas[1] > 0 and deltas[1] + deltas[2] == 0, str(deltas))
check("ELO: rango Bronce 1200", elo_service.rank_for(1200).value == "BRONCE")
check("ELO: rango Diamante 2000", elo_service.rank_for(2000).value == "DIAMANTE")
check("ELO: soft reset 1600->1400", elo_service.soft_reset(1600) == 1400)

failed = [n for n, ok, _ in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} comprobaciones OK")
sys.exit(1 if failed else 0)
