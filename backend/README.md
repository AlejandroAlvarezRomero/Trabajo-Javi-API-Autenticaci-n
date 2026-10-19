# Board Game Tracker API

Backend distribuido para registrar y gestionar partidas de juegos de mesa:
grupos privados, catálogo integrado con BoardGameGeek, verificación de resultados,
ELO con rangos, temporadas de 3 meses, logros y panel de administración.

**Estado**: funcional y cubierto por tests de integración (51 comprobaciones end-to-end).

## 1. Estructura de carpetas (Backend FastAPI)

```
backend/
├── .env.example                  # Variables de entorno (copiar a .env)
├── requirements.txt
├── README.md
├── alembic.ini                   # Config de Alembic (la URL la inyecta alembic/env.py)
├── alembic/
│   ├── env.py                    # settings.DATABASE_URL + Base.metadata (autogenerate)
│   └── versions/                 # Revisiones (eb665009a651 = esquema inicial)
└── app/
    ├── main.py                   # Factoría FastAPI, CORS, lifespan (migraciones + seed), routers
    ├── core/                     # Núcleo transversal
    │   ├── config.py             # Settings vía pydantic-settings (lee .env)
    │   ├── security.py           # hash passlib/bcrypt + JWT dual (access/refresh)
    │   ├── deps.py               # get_current_user + RBAC (admin global, roles de grupo)
    │   └── timeutils.py          # utcnow() común
    ├── db/
    │   ├── base.py               # DeclarativeBase de SQLAlchemy 2.0
    │   ├── session.py            # engine, SessionLocal, get_db()
    │   ├── migrate.py            # run_migrations(): `alembic upgrade head` al arrancar
    │   └── seed.py               # Siembra de roles (ADMIN/PLAYER) y logros
    ├── models/                   # ESQUEMAS DE BASE DE DATOS (SQLAlchemy 2.0)
    │   ├── enums.py              # GlobalRole, GroupRole, MatchStatus, Rank...
    │   ├── user.py               # Role, User, RefreshToken (revocable)
    │   ├── group.py              # Group, GroupMembership (MANAGER/MEMBER)
    │   ├── game.py               # Game (catálogo por grupo, metadatos BGG)
    │   ├── season.py             # Season, SeasonRating (ELO, win rate, rango)
    │   ├── match.py              # Match, MatchParticipant, MatchConfirmation
    │   ├── achievement.py        # Achievement, UserAchievement
    │   └── notification.py       # Notification
    ├── schemas/                  # DTOs Pydantic v2
    │   ├── auth.py  group.py  game.py  match.py  notification.py  stats.py
    ├── api/v1/                   # ENDPOINTS
    │   ├── auth.py               # registro/login/refresh/logout/me
    │   ├── groups.py             # crear, unirse, miembros, roles, borrar
    │   ├── games.py              # catálogo + búsqueda BGG + alta con metadatos
    │   ├── matches.py            # registro PENDING, confirm/reject/cancel
    │   ├── seasons.py            # histórico y rollover manual
    │   ├── stats.py              # leaderboard, stats/me, stats de usuarios
    │   ├── notifications.py      # bandeja de notificaciones
    │   ├── achievements.py       # catálogo de logros y mis insignias
    │   └── admin.py              # métricas globales y moderación de usuarios
    └── services/
        ├── elo_service.py        # ELO FIDE multijugador, rangos, soft reset
        ├── bgg_service.py        # cliente xmlapi2 (search/thing) con reintentos
        ├── season_service.py     # temporada activa, rollover, ratings
        ├── match_service.py      # registro, verificación y aplicación de ELO
        └── achievement_service.py# evaluación de insignias tras confirmar
```

## 2. Puesta en marcha

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # define un JWT_SECRET_KEY fuerte
uvicorn app.main:app --reload --port 8000
```

- Swagger: http://localhost:8000/docs  (34 rutas)
- Health:  `GET /health`

### Migraciones (Alembic)

El esquema vive en `alembic/versions/` y se aplica solo al arrancar la app
(el `lifespan` ejecuta `alembic upgrade head`). Comandos útiles desde `backend/`:

```powershell
.venv\Scripts\alembic.exe revision --autogenerate -m "descripcion"  # nueva revisión
.venv\Scripts\alembic.exe upgrade head                              # aplicar
.venv\Scripts\alembic.exe downgrade -1                              # revertir
.venv\Scripts\alembic.exe current                                   # versión actual
```

> Tras cambiar un modelo: genera la revisión con `--autogenerate`, **revisa el
> archivo generado** (nullable, server_default, batch de SQLite) y lanza
> `tests/migrations_test.py` para comprobar que no hay *drift*.

## 3. API (prefijo `/api/v1`)

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| POST | `/auth/register` | público | Alta (rol PLAYER) → 201 |
| POST | `/auth/login` | público | `{email, password}` → access token + cookie HttpOnly (rate limited: 5 intentos/min) |
| POST | `/auth/refresh` | cookie | Rotación del refresh → nuevo access token (con detección de reuso) |
| POST | `/auth/logout` | cookie | Revoca jti y borra cookie → 204 |
| GET | `/auth/me` | Bearer | Usuario autenticado |
| PATCH | `/auth/me` | Bearer | Actualizar perfil (`display_name`, `avatar_url`) |
| POST | `/auth/forgot-password` | público | Solicitar token para recuperación de contraseña |
| POST | `/auth/reset-password` | público | Restablecer contraseña y revocar sesiones previas |
| POST | `/groups` | Bearer | Crear grupo (`seed_popular: true` opcional para precargar catálogo) |
| GET | `/groups` | Bearer | Mis grupos |
| POST | `/groups/join` | Bearer | Unirse por código de invitación |
| GET | `/groups/{id}` | miembro | Detalle (miembros, juegos) |
| POST | `/groups/{id}/transfer-ownership` | dueño/ADMIN | Transferir propiedad del grupo |
| GET | `/groups/{id}/members` | miembro | Lista de miembros y roles |
| PATCH/DELETE | `/groups/{id}/members/{uid}` | **MANAGER** | Rol / expulsión |
| POST | `/groups/{id}/leave` | miembro | Salir del grupo |
| DELETE | `/groups/{id}` | propietario/ADMIN | Borra en cascada |
| GET | `/groups/{id}/games` | miembro | Catálogo del grupo |
| GET | `/groups/{id}/games/search?q=` | miembro | Búsqueda en BGG |
| POST | `/groups/{id}/games` | **MANAGER** | Añadir por `bgg_id` (metadatos automáticos) |
| POST | `/groups/{id}/games/seed-popular` | **MANAGER** | Precargar catálogo con juegos populares (Catan, Carcassonne...) |
| DELETE | `/groups/{id}/games/{gid}` | **MANAGER** | Quitar (409 si tiene partidas) |
| GET/POST | `/groups/{id}/matches` | miembro | Listar (con paginación `limit`/`offset`) / registrar (PENDING) |
| GET | `/groups/{id}/matches/{mid}` | miembro | Detalle + confirmaciones |
| POST | `.../matches/{mid}/confirm` | participante | Confirmar → al 100% aplica ELO |
| POST | `.../matches/{mid}/reject` | participante | Rechazar → REJECTED (sin efecto) |
| POST | `.../matches/{mid}/cancel` | **MANAGER** | Anular pendiente |
| GET | `/groups/{id}/seasons` | miembro | Histórico de temporadas |
| POST | `/groups/{id}/seasons/rollover` | **MANAGER** | Siguiente temporada (soft reset) |
| GET | `/groups/{id}/leaderboard` | miembro | Clasificación ELO + rangos (paginado) |
| GET | `/groups/{id}/stats/me` | miembro | Win rate, ELO, minutos jugados |
| GET | `/groups/{id}/stats/users/{uid}` | miembro | Stats de otro miembro |
| GET | `/notifications` (+`/read`, `/read-all`) | Bearer | Bandeja de notificaciones (paginada) |
| GET | `/notifications/stream` | Bearer | Stream en tiempo real (Server-Sent Events - SSE) |
| GET | `/achievements` | Bearer | Catálogo de insignias |
| GET | `/users/me/achievements` | Bearer | Mis insignias desbloqueadas |
| GET | `/admin/overview`, `/admin/users` | **ADMIN** | Métricas y moderación (paginado) |
| PATCH | `/admin/users/{uid}` | **ADMIN** | Activar/desactivar (revoca tokens) o cambiar rol |

## 4. Seguridad implementada

| Mecanismo | Detalle |
|---|---|
| Contraseñas | `passlib` + **bcrypt** (hash con salt automático) |
| Access Token | JWT de **15 min**, cabecera `Authorization: Bearer` |
| Refresh Token | JWT de **14 días** en **cookie HttpOnly** (`SameSite=Lax`, `Secure` en prod), ruta restringida a `/api/v1/auth` |
| Rotación y Reuso | Cada `/refresh` rota el `jti`. Si se detecta un intento de reutilizar un token antiguo, se revoca de inmediato **toda la familia de tokens** del usuario (mitigación de robo de cookie) |
| Rate Limiting | Ventana deslizante en memoria en `/auth/login` (máximo 5 intentos fallidos por IP/email en 60 segundos; responde HTTP 429 con `Retry-After`) |
| Recuperación de Contraseña | Token JWT temporal de un solo uso con firma invalidada tras el cambio de hash |
| Login | Mensaje genérico (evita *user enumeration*); registro duplicado → 409 |
| CORS | Orígenes configurables con `allow_credentials=True` |
| RBAC | `require_global_admin` (ADMIN) y `require_group_role(MANAGER/MEMBER)` por grupo |


## 5. Lógica de negocio

- **Registro de partidas**: el participante que la registra la deja `PENDING`;
  el resto recibe `MATCH_CONFIRMATION` y debe `confirm` o `reject`.
  El registrador se da por confirmado. Solo al 100 % de confirmaciones → `CONFIRMED`.
- **ELO** (k=32, reparto entre rivales): ganar a un rival +200 ELO ≈ **+24 puntos**.
  Rangos: Hierro <1200 ≤ Bronce <1400 ≤ Plata <1600 ≤ Oro <1800 ≤ Platino <2000 ≤ Diamante.
  Las variaciones se guardan en `match_participants.elo_delta` al verificar.
- **Estadísticas**: win rate, victorias/derrotas, minutos jugados y ELO por
  usuario en la temporada vigente del grupo (`season_ratings`).
- **Temporadas** (92 días): al expirar (o con `rollover`) se cierra la temporada,
  se crea la siguiente con **soft reset** (50 % de regresión a la media) y el
  histórico anterior queda intacto.
- **Logros**: `FIRST_BLOOD`, `WIN_STREAK_5`, `GAMES_10`, `GAMES_50` se evalúan
  al confirmar cada partida y generan notificación de insignia.
- **BGG**: `GET /thing?id=X&stats=1` rellena portada, descripción, jugadores,
  duración, año, rank y rating; reintentos ante el 202 de BGG; sin red → 502.

## 6. Tests

La suite completa incluye tanto scripts de integración directa como tests estructurados con `pytest` (**97 comprobaciones en total**):

- `tests/smoke_auth.py` (**28 checks**): auth dual, cookies, rotación, detección de reuso y revocación de familia, actualización de perfil/avatar, recuperación de contraseña, rate limiting y fórmulas puras de ELO.
- `tests/integration_test.py` (**56 checks**): flujo completo multiusuario (grupos, precarga de catálogo, BGG, partidas PENDING/CONFIRMED/REJECTED, leaderboard, logros, rollover, RBAC, transferencia de propiedad y borrado en cascada).
- `tests/migrations_test.py` (**6 checks**): Alembic sobre BD temporal aislada — `upgrade head` crea las 15 tablas, sin *drift* modelos/migraciones, `downgrade base` limpia y re-`upgrade` reconstruye.
- `pytest` (**7 tests en `tests/test_api.py`**): ejecución unitaria y de integración automatizable en CI (`.github/workflows/ci.yml`).

Todos borran su BD al empezar (deterministas) y salen con código 1 si algo falla.

## 7. Frontend Flutter (`frontend/`)

El frontend multiplataforma en Flutter está completamente desarrollado en `frontend/` y compilado para Web:
- **Riverpod 3** para gestión reactiva de estado sin generadores de código.
- **GoRouter** para navegación y control de acceso.
- **Dio** con interceptor de rotación silenciosa de tokens (`AuthInterceptor`) ante respuestas HTTP 401.
- Pantallas: Autenticación (Login/Registro), Mis Grupos, Detalle de Grupo con 4 pestañas (Partidas, Leaderboard con soft reset, Catálogo con thumbnails y precarga, Miembros con roles), Búsqueda e importación BGG, Registro y Detalle de Partidas con confirmación colectiva, Bandeja de Notificaciones en vivo y Vitrina de Logros.

