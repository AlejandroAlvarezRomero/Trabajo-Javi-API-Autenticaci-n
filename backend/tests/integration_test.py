"""Test de integración end-to-end del backend.

Cubre: auth + RBAC, grupos, catálogo BGG, partidas con verificación,
ELO, estadísticas, logros, temporadas, notificaciones y admin.

Ejecutar desde `backend/`:
    .venv\\Scripts\\python.exe tests\\integration_test.py

Si BGG no está accesible (sin red), simula la API para no depender de internet.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# BD SQLite limpia para que el test sea determinista
from app.core.config import settings  # noqa: E402

if settings.DATABASE_URL.startswith("sqlite:///"):
    db_file = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    if not db_file.is_absolute():
        db_file = ROOT / db_file.name
    db_file.unlink(missing_ok=True)

from fastapi.testclient import TestClient  # noqa: E402

import app.services.bgg_service as bgg_service  # noqa: E402
from app.main import app  # noqa: E402

results = []


def check(name, condition, extra=""):
    results.append(bool(condition))
    print(("OK  " if condition else "FAIL") + f" {name}" + (f" | {extra}" if extra else ""))


# ------------------------------------------------------------------
# BGG: se usa la API real; si no hay red, se simula
# ------------------------------------------------------------------
try:
    meta = bgg_service.fetch_game(13)  # Catan
    LIVE_BGG = bool(meta.name)
except Exception:
    LIVE_BGG = False

if not LIVE_BGG:
    from app.services.bgg_service import BGGGameMetadata, BGGNotFoundError, BGGSearchItem

    def _fake_fetch(bgg_id):
        if bgg_id == 999999:
            raise BGGNotFoundError("no existe")
        return BGGGameMetadata(
            bgg_id=bgg_id,
            name=f"Juego {bgg_id}",
            description="Descripción de prueba",
            image_url="https://cf.geekdo-images.com/example.jpg",
            min_players=2,
            max_players=4,
            avg_playtime_minutes=60,
            year_published=2000,
            bgg_ranking=100,
            bgg_rating=7.2,
        )

    def _fake_search(query, limit=10):
        return [BGGSearchItem(bgg_id=13, name="Catan", year_published=1995)]

    bgg_service.fetch_game = _fake_fetch
    bgg_service.search_games = _fake_search
print(f"(BGG en vivo: {LIVE_BGG})\n")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


with TestClient(app) as client:
    # ---------------- Registro y login de 3 usuarios ----------------
    users = {}
    for name in ("ana", "bruno", "carlos"):
        r = client.post(
            "/api/v1/auth/register",
            json={"email": f"{name}@test.com", "username": name, "password": "secreta123"},
        )
        check(f"registro {name} 201", r.status_code == 201, str(r.status_code))
        users[name] = r.json()["id"]

    tokens = {}
    for name in ("ana", "bruno", "carlos"):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": f"{name}@test.com", "password": "secreta123"},
        )
        check(f"login {name} 200", r.status_code == 200)
        tokens[name] = r.json()["access_token"]

    # ---------------- Grupos ----------------
    r = client.post(
        "/api/v1/groups",
        json={"name": "Los Dados", "description": "Grupo de pruebas"},
        headers=auth(tokens["ana"]),
    )
    check("crear grupo 201", r.status_code == 201, str(r.status_code))
    group = r.json()
    gid = group["id"]
    check("creador es MANAGER", group["my_role"] == "MANAGER")
    check("grupo tiene código de invitación", len(group["invite_code"]) == 6, group["invite_code"])
    check("grupo arranca con 1 miembro y 0 juegos", group["member_count"] == 1 and group["game_count"] == 0)

    r = client.post(
        "/api/v1/groups/join",
        json={"invite_code": group["invite_code"]},
        headers=auth(tokens["bruno"]),
    )
    check("bruno se une 200", r.status_code == 200 and r.json()["my_role"] == "MEMBER")

    r = client.post(
        "/api/v1/groups/join",
        json={"invite_code": group["invite_code"]},
        headers=auth(tokens["bruno"]),
    )
    check("doble unión 409", r.status_code == 409, str(r.status_code))

    r = client.post(
        "/api/v1/groups/join",
        json={"invite_code": "XXXXXX"},
        headers=auth(tokens["carlos"]),
    )
    check("código inválido 404", r.status_code == 404, str(r.status_code))

    r = client.get(f"/api/v1/groups/{gid}/members", headers=auth(tokens["ana"]))
    check("lista de miembros = 2", r.status_code == 200 and len(r.json()) == 2, str(r.status_code))

    # RBAC: bruno (MEMBER) no puede añadir juegos
    r = client.post(
        f"/api/v1/groups/{gid}/games",
        json={"bgg_id": 13},
        headers=auth(tokens["bruno"]),
    )
    check("member añade juego 403", r.status_code == 403, str(r.status_code))

    # ---------------- Catálogo BGG ----------------
    r = client.get(
        f"/api/v1/groups/{gid}/games/search",
        params={"query": "catan"},
        headers=auth(tokens["ana"]),
    )
    check("búsqueda BGG 200", r.status_code == 200 and len(r.json()) >= 1, str(r.status_code))

    r = client.post(
        f"/api/v1/groups/{gid}/games",
        json={"bgg_id": 13},
        headers=auth(tokens["ana"]),
    )
    check("añadir juego 201", r.status_code == 201, str(r.status_code))
    game = r.json()
    check(
        "metadatos BGG rellenados",
        bool(game["name"]) and (game["min_players"] in (None, 2)) and game["year_published"] in (None, 1995, 2000),
        f"name={game['name']} jugadores={game['min_players']}-{game['max_players']} duración={game['avg_playtime_minutes']}",
    )

    r = client.post(
        f"/api/v1/groups/{gid}/games",
        json={"bgg_id": 13},
        headers=auth(tokens["ana"]),
    )
    check("juego duplicado 409", r.status_code == 409, str(r.status_code))

    r = client.post(
        f"/api/v1/groups/{gid}/games",
        json={"bgg_id": 999999},
        headers=auth(tokens["ana"]),
    )
    check("juego inexistente en BGG 404", r.status_code == 404, str(r.status_code))

    # ---------------- Registro de partida (PENDING) ----------------
    r = client.post(
        f"/api/v1/groups/{gid}/matches",
        json={
            "game_id": game["id"],
            "winner_id": users["ana"],
            "participant_ids": [users["ana"], users["bruno"]],
            "duration_minutes": 45,
        },
        headers=auth(tokens["ana"]),
    )
    check("registrar partida 201 PENDING", r.status_code == 201 and r.json()["status"] == "PENDING", str(r.status_code))
    match = r.json()
    mid = match["id"]
    check(
        "2 participantes y 1 confirmación pendiente",
        len(match["participants"]) == 2 and match["confirmations"][0]["confirmed"] is None,
    )

    r = client.get("/api/v1/notifications", headers=auth(tokens["bruno"]))
    notifs = r.json()
    check(
        "bruno recibe notificación de confirmación",
        any(n["type"] == "MATCH_CONFIRMATION" for n in notifs),
        str(len(notifs)),
    )

    # El registrador no confirma su propia partida
    r = client.post(f"/api/v1/groups/{gid}/matches/{mid}/confirm", headers=auth(tokens["ana"]))
    check("registrador confirma 409", r.status_code == 409, str(r.status_code))

    # ---------------- Confirmación -> CONFIRMED + ELO ----------------
    r = client.post(f"/api/v1/groups/{gid}/matches/{mid}/confirm", headers=auth(tokens["bruno"]))
    check("bruno confirma -> CONFIRMED", r.status_code == 200 and r.json()["status"] == "CONFIRMED", str(r.status_code))
    deltas = {p["user_id"]: p["elo_delta"] for p in r.json()["participants"]}
    check("variaciones ELO aplicadas", deltas[users["ana"]] > 0 > deltas[users["bruno"]], str(deltas))

    r = client.post(f"/api/v1/groups/{gid}/matches/{mid}/confirm", headers=auth(tokens["bruno"]))
    check("doble confirmación 409", r.status_code == 409, str(r.status_code))

    r = client.get(f"/api/v1/groups/{gid}/stats/me", headers=auth(tokens["ana"]))
    stats_ana = r.json()
    check(
        "stats ana: 1 victoria, 100% winrate, ELO > 1200",
        stats_ana["wins"] == 1 and stats_ana["win_rate"] == 100.0 and stats_ana["elo"] > 1200,
        str(stats_ana),
    )

    r = client.get(f"/api/v1/groups/{gid}/leaderboard", headers=auth(tokens["bruno"]))
    lb = r.json()
    check(
        "leaderboard con 2 entradas y ana líder",
        len(lb["entries"]) == 2 and lb["entries"][0]["username"] == "ana",
        str([(e["username"], e["elo"], e["rank"]) for e in lb["entries"]]),
    )

    # ---------------- Racha de 5 victorias -> logro ----------------
    for i in range(4):
        r = client.post(
            f"/api/v1/groups/{gid}/matches",
            json={
                "game_id": game["id"],
                "winner_id": users["ana"],
                "participant_ids": [users["ana"], users["bruno"]],
                "duration_minutes": 30,
            },
            headers=auth(tokens["ana"]),
        )
        assert r.status_code == 201, r.text
        m = r.json()
        r = client.post(
            f"/api/v1/groups/{gid}/matches/{m['id']}/confirm",
            headers=auth(tokens["bruno"]),
        )
        assert r.status_code == 200 and r.json()["status"] == "CONFIRMED", r.text

    r = client.get("/api/v1/users/me/achievements", headers=auth(tokens["ana"]))
    codes = sorted(a["achievement"]["code"] for a in r.json())
    check("ana desbloquea FIRST_BLOOD y WIN_STREAK_5", codes == ["FIRST_BLOOD", "WIN_STREAK_5"], str(codes))

    r = client.get("/api/v1/users/me/achievements", headers=auth(tokens["bruno"]))
    check("bruno sin logros (5 partidas < 10)", r.json() == [], str(r.json()))

    r = client.get(f"/api/v1/groups/{gid}/stats/me", headers=auth(tokens["bruno"]))
    check("bruno: 5 partidas jugadas", r.json()["games_played"] == 5, str(r.json()))

    # ---------------- Rechazo de resultado ----------------
    r = client.post(
        f"/api/v1/groups/{gid}/matches",
        json={
            "game_id": game["id"],
            "winner_id": users["bruno"],
            "participant_ids": [users["ana"], users["bruno"], users["carlos"]],
        },
        headers=auth(tokens["bruno"]),
    )
    # carlos aún no está en el grupo -> 400
    check("participante ajeno al grupo 400", r.status_code == 400, str(r.status_code))

    r = client.post(
        "/api/v1/groups/join",
        json={"invite_code": group["invite_code"]},
        headers=auth(tokens["carlos"]),
    )
    check("carlos se une 200", r.status_code == 200)

    r = client.post(
        f"/api/v1/groups/{gid}/matches",
        json={
            "game_id": game["id"],
            "winner_id": users["bruno"],
            "participant_ids": [users["ana"], users["bruno"], users["carlos"]],
            "duration_minutes": 60,
        },
        headers=auth(tokens["bruno"]),
    )
    check("partida 3 jugadores 201", r.status_code == 201 and r.json()["status"] == "PENDING")
    mid3 = r.json()["id"]

    r = client.post(f"/api/v1/groups/{gid}/matches/{mid3}/reject", headers=auth(tokens["carlos"]))
    check("carlos rechaza -> REJECTED", r.status_code == 200 and r.json()["status"] == "REJECTED", str(r.status_code))

    r = client.get(f"/api/v1/groups/{gid}/stats/me", headers=auth(tokens["ana"]))
    check("partida rechazada NO afecta a stats", r.json()["games_played"] == 5, str(r.json()))

    # ---------------- Temporadas ----------------
    r = client.post(f"/api/v1/groups/{gid}/seasons/rollover", headers=auth(tokens["bruno"]))
    check("rollover por MEMBER 403", r.status_code == 403, str(r.status_code))

    r = client.get(f"/api/v1/groups/{gid}/leaderboard", headers=auth(tokens["ana"]))
    elo_s1 = {e["username"]: e["elo"] for e in r.json()["entries"]}
    r = client.post(f"/api/v1/groups/{gid}/seasons/rollover", headers=auth(tokens["ana"]))
    check("rollover por MANAGER 201", r.status_code == 201, str(r.status_code))
    check("nueva temporada número 2", r.json()["number"] == 2 and r.json()["is_active"])

    r = client.get(f"/api/v1/groups/{gid}/seasons", headers=auth(tokens["ana"]))
    check("histórico de 2 temporadas", r.status_code == 200 and len(r.json()) == 2, str(r.status_code))

    r = client.get(f"/api/v1/groups/{gid}/leaderboard", headers=auth(tokens["ana"]))
    entries = {e["username"]: e["elo"] for e in r.json()["entries"]}
    expected_ana = round(1200 + (elo_s1["ana"] - 1200) * 0.5)
    check("soft reset: ELO regresa a la media", entries["ana"] == expected_ana, f"{elo_s1} -> {entries}")
    check(
        "temporada 2 empieza con stats a cero",
        next(e for e in r.json()["entries"] if e["username"] == "ana")["games_played"] == 0,
    )

    # ---------------- RBAC global (Administrador) ----------------
    r = client.get("/api/v1/admin/overview", headers=auth(tokens["ana"]))
    check("player no es admin 403", r.status_code == 403, str(r.status_code))

    from app.db.session import SessionLocal
    from app.models import Role, User

    db = SessionLocal()
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    db.query(User).filter(User.username == "ana").update({"role_id": admin_role.id})
    db.commit()
    db.close()

    r = client.get("/api/v1/admin/overview", headers=auth(tokens["ana"]))
    check("admin overview 200", r.status_code == 200 and r.json()["users"] == 3, str(r.json()))

    r = client.patch(
        "/api/v1/admin/users/%d" % users["carlos"],
        json={"is_active": False},
        headers=auth(tokens["ana"]),
    )
    check("admin desactiva usuario 200", r.status_code == 200 and r.json()["is_active"] is False)

    r = client.get("/api/v1/auth/me", headers=auth(tokens["carlos"]))
    check("usuario desactivado 403", r.status_code == 403, str(r.status_code))

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "carlos@test.com", "password": "secreta123"},
    )
    check("login de cuenta desactivada 403", r.status_code == 403, str(r.status_code))

    # ---------------- Transferencia de propiedad ----------------
    r = client.post(
        f"/api/v1/groups/{gid}/transfer-ownership",
        json={"new_owner_id": users["carlos"]},
        headers=auth(tokens["bruno"]),
    )
    check("no owner no transfiere grupo 403", r.status_code == 403, str(r.status_code))

    r = client.post(
        f"/api/v1/groups/{gid}/transfer-ownership",
        json={"new_owner_id": users["bruno"]},
        headers=auth(tokens["ana"]),
    )
    check("propietario transfiere grupo 200", r.status_code == 200 and r.json()["owner_id"] == users["bruno"], str(r.status_code))

    # ---------------- Borrado del grupo (cascada) ----------------
    # ana ya no es dueña, bruno es el dueño
    r = client.delete(f"/api/v1/groups/{gid}", headers=auth(tokens["bruno"]))
    check("nuevo propietario borra grupo 204", r.status_code == 204, str(r.status_code))

    r = client.get(f"/api/v1/groups/{gid}", headers=auth(tokens["bruno"]))
    check("grupo ya no existe 403/404", r.status_code in (403, 404), str(r.status_code))

    # ---------------- Precarga de juegos populares ----------------
    r_seed_grp = client.post(
        "/api/v1/groups",
        json={"name": "Grupo Con Juegos", "description": "Con catálogo precargado", "seed_popular": True},
        headers=auth(tokens["ana"]),
    )
    check("crear grupo con seed_popular 201", r_seed_grp.status_code == 201)
    gid2 = r_seed_grp.json()["id"]
    check("grupo creado tiene juegos precargados", r_seed_grp.json()["game_count"] >= 7, str(r_seed_grp.json()["game_count"]))

    # Listar catálogo del grupo precargado
    r_cat = client.get(f"/api/v1/groups/{gid2}/games", headers=auth(tokens["ana"]))
    check("catálogo contiene Catan y Carcassonne", any(g["name"] == "Catan" for g in r_cat.json()) and any(g["name"] == "Carcassonne" for g in r_cat.json()))

    # Precarga idempotente vía endpoint dedicado
    r_endpoint_seed = client.post(f"/api/v1/groups/{gid2}/games/seed-popular", headers=auth(tokens["ana"]))
    check("endpoint seed-popular 201 idempotente", r_endpoint_seed.status_code == 201)


failed = results.count(False)
print(f"\n{len(results) - failed}/{len(results)} comprobaciones OK")
sys.exit(1 if failed else 0)
