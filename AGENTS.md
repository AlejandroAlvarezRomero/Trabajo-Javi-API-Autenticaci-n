# CONTEXTO DEL PROYECTO — Documento de traspaso a otro agente

> Lee este documento completo antes de tocar nada. Es la fuente de verdad del
> estado del proyecto, las decisiones ya tomadas y lo que queda por hacer.

## 1. Misión del proyecto

Aplicación distribuida para **registrar y gestionar partidas de juegos de mesa**:
grupos privados, catálogo con metadatos de BoardGameGeek, verificación de
resultados por confirmación entre jugadores, sistema ELO con rangos, temporadas
de 3 meses, logros y roles (RBAC). Objetivo final: desplegar en **Web** y luego
en **Android e iOS**.

## 2. Ubicación, entorno y cómo ejecutar

- **Raíz del workspace**: `C:\Users\AlejandroAlvarez\Desktop\Trabajo Autenticacion`
- **Backend**: subcarpeta `backend/` (aquí vive TODO el código actual).
- **SO**: Windows · **Python**: 3.13.15 · **No es un repo git** (recomendado `git init` al continuar).
- **Virtualenv ya creado e instalado**: `backend/.venv` con todas las dependencias de `requirements.txt`.

```powershell
cd "C:\Users\AlejandroAlvarez\Desktop\Trabajo Autenticacion\backend"
.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000   # Swagger en http://localhost:8000/docs
```

- **Tests (obligatorios tras cualquier cambio)**, se ejecutan desde `backend/`:
  ```powershell
  .venv\Scripts\python.exe tests\smoke_auth.py         # 18 comprobaciones (auth + ELO puro)
  .venv\Scripts\python.exe tests\integration_test.py   # 51 comprobaciones (flujo completo)
  .venv\Scripts\python.exe tests\migrations_test.py    # 6 comprobaciones (Alembic: up/down/sin drift)
  ```
  Los tres borran y recrean su BD automáticamente (son scripts con `check()` y
  `sys.exit(1)` si algo falla, pensados para CI). El esquema de `boardgames.db`
  ahora lo crea **Alembic** (ya no hay `create_all`).
  **Estado actual: 18/18, 51/51 y 6/6 OK. Cualquier cambio debe mantenerlo así.**
  El test de integración usa la API real de BGG y, si no hay red, la simula
  (imprime `(BGG en vivo: True/False)`).

## 3. Stack y decisiones ya tomadas (NO cambiar a la ligera)

| Área | Decisión |
|---|---|
| Backend | Python + **FastAPI** (endpoints síncronos `def`, se ejecutan en threadpool) + Swagger autogenerado |
| ORM | **SQLAlchemy 2.0** estilo `Mapped`/`mapped_column` (NO SQLModel) |
| Migraciones | **Alembic integrado** (Tarea A hecha): `alembic/` + `alembic.ini` en `backend/`; el `lifespan` de `app/main.py` llama a `run_migrations()` (`app/db/migrate.py`), que es `alembic upgrade head`, y después siembra roles y logros. `create_all` **ya no se usa**. En SQLite (`render_as_batch=True`) Alembic emula los ALTER recreando la tabla |
| DB | SQLite en dev (`DATABASE_URL` en `.env`), preparado para PostgreSQL |
| Contraseñas | `passlib` con **bcrypt** (salt automático). `bcrypt` está **pineado a 4.0.1** en requirements por incompatibilidad con passlib 1.7.4 |
| Tokens | JWT dual: **Access 15 min** en cabecera `Authorization: Bearer` + **Refresh 14 días en cookie HttpOnly** (`path=/api/v1/auth`, `SameSite=Lax`, `Secure` vía env). Cada refresh **rota el jti** (un solo uso, revocable en tabla `refresh_tokens`) |
| Sesión BD | `SessionLocal` con **`autoflush=False`** y **`expire_on_commit=False`** → hay que hacer `db.flush()` explícito antes de SELECTs que deban ver inserts pendientes (ya causó un bug, ver §6) |
| RBAC | Rol global en `users.role_id` (`ADMIN`/`PLAYER`) + rol por grupo en `group_memberships.role` (`MANAGER`/`MEMBER`). Dependencias: `require_global_admin` y `require_group_role(min_role)` en `app/core/deps.py` (leen `group_id` del path) |
| Frontend | Aún no existe. El previsto es **Flutter** (multiplataforma Web/Android/iOS) con interceptor de refresh silencioso |
| Idioma | Comentarios, mensajes HTTP y nombres de usuario/descripción en **español**; código y claves en inglés |

## 4. Estado actual — qué está HECHO y VERIFICADO

### Estructura

```
backend/
├── .env.example  requirements.txt  README.md  .gitignore
├── alembic.ini  alembic/  (env.py + versions/)  # ← migraciones (Tarea A hecha)
├── app/
│   ├── main.py                # lifespan (run_migrations()+seeds), CORS, 9 routers, /health
│   ├── core/    config.py  security.py  deps.py  timeutils.py
│   ├── db/      base.py  session.py  migrate.py  seed.py (roles ADMIN/PLAYER + 4 logros)
│   ├── models/  enums.py  user.py  group.py  game.py  season.py  match.py
│   │            achievement.py  notification.py  __init__.py (re-exporta todo)
│   ├── schemas/ auth.py  group.py  game.py  match.py  notification.py  stats.py
│   ├── api/v1/  auth.py  groups.py  games.py  matches.py  seasons.py
│   │            stats.py  notifications.py  achievements.py  admin.py
│   └── services/ elo_service.py  bgg_service.py  season_service.py
│                 match_service.py  achievement_service.py
└── tests/       smoke_auth.py  integration_test.py  migrations_test.py  # ← tras cada cambio
```

### 34 rutas operativas (prefijo `/api/v1`)

- **auth**: register, login (cookie), refresh (rotación), logout (revoca), me
- **groups**: crear (genera código de invitación + Temporada 1), listar mis grupos,
  `POST /groups/join` por código, detalle, miembros, cambiar rol/expulsar (MANAGER),
  salir, borrar en cascada (propietario o ADMIN)
- **games**: catálogo por grupo, búsqueda en BGG, alta por `bgg_id` rellenando
  metadatos desde `xmlapi2/thing` (MANAGER), baja (409 si tiene partidas)
- **matches**: registrar (queda `PENDING` + notificaciones a los demás),
  detalle con confirmaciones, `confirm` / `reject` (solo participantes),
  `cancel` (MANAGER). **Al 100 % de confirmaciones → `CONFIRMED` y ahí se
  aplican ELO + stats + logros**; un rechazo → `REJECTED` sin efectos
- **seasons**: histórico + `rollover` manual (MANAGER)
- **stats**: `leaderboard` (ELO+rank), `stats/me`, `stats/users/{uid}`
- **notifications**: bandeja, marcar leída, marcar todas
- **achievements**: catálogo + mis insignias
- **admin** (solo ADMIN): overview, listar/buscar usuarios, activar-desactivar
  (al desactivar se revocan sus refresh tokens) y cambiar rol

### Reglas de negocio invariantes (no romper)

1. **ELO** (`elo_service`): k=32, expectativa FIDE repartida entre rivales
   (ganar a rival +200 ≈ +24 puntos), ELO base 1200. Las variaciones se
   guardan en `match_participants.elo_delta` **solo al confirmar**.
2. **Rangos**: Hierro <1200 ≤ Bronce <1400 ≤ Plata <1600 ≤ Oro <1800 ≤
   Platino <2000 ≤ Diamante (constante `RANK_THRESHOLDS`).
3. **Temporadas**: 92 días por grupo; al finalizar → soft reset = regresión
   50 % a la media (`elo_service.soft_reset`); el histórico de la temporada
   anterior **nunca se toca** (`season_ratings` por `season_id`).
4. **Partida**: solo `CONFIRMED` afecta a estadísticas/ELO; el registrador se
   da por confirmado y no puede confirmar la suya; nadie puede responder dos veces.
5. **RBAC**: `ADMIN` global → todo; `MANAGER` → solo modera **su grupo**
   (miembros, catálogo, cancelar partidas, rollover); `MEMBER` → jugar/ver.
6. Un usuario solo puede jugar partidas si **todos** los participantes son
   miembros del grupo y el juego pertenece al catálogo del grupo.

## 5. Convenciones del proyecto (seguirlas para mantener coherencia)

- Router: `APIRouter(prefix=..., tags=...)` y se registra en `app/main.py` con
  `app.include_router(x.router, prefix=settings.API_V1_PREFIX)`.
- Respuestas: **siempre** `response_model` Pydantic (v2, `ConfigDict(from_attributes=True)` para ORM); para objetos compuestos se construye una función helper (`match_to_out`, `_group_out`).
- Errores: `HTTPException(status.HTTP_XXX, "mensaje en español")`. Usar 401/403/404/409/422 con criterio (409 para conflictos de estado/unicidad).
- Acceso a BD: `db: Session = Depends(get_db)`; `db.commit()` explícito; recuerda `flush()` tras `add()` en bloque si un SELECT posterior debe verlos.
- Fechas: siempre `utcnow()` de `app/core/timeutils.py` (naive UTC, compatible SQLite+Postgres).
- Enums `str, Enum` en `models/enums.py`; en BD se guarda el `.value`.
- Cada endpoint de grupo repite `_member/_manager: GroupMembership = Depends(require_group_role(...))` para autorización y ya no hace falta comprobar pertenencia a mano.
- **Migraciones**: tras tocar cualquier modelo → `alembic revision --autogenerate -m "..."` desde `backend/`, revisar el archivo generado y lanzar `tests/migrations_test.py`. El esquema se aplica SIEMPRE vía `run_migrations()` en el `lifespan`; nunca volver a `create_all`.

## 6. Bugs ya encontrados (aprendizajes — no repetirlos)

1. **FK ambigua**: `GroupMembership` tiene DOS FK hacia `users` (`user_id` y `joined_by_id`) → hay que pasar `foreign_keys=` en las relationships.
2. **`Response` inyectado en FastAPI**: su `status_code` es `None` si no lo asignas; en endpoints `status_code=204` hay que hacer `response.status_code = ...` y devolver `None` (no devolver el objeto `response` tal cual).
3. **`Element` de XML es falsy sin hijos**: nunca `elem or default` → usar `is None` (rompió `min_players` de BGG).
4. **`autoflush=False`**: en el rollover se duplicaban `season_ratings` porque el SELECT no veía los INSERT pendientes → `db.flush()` obligatorio.
5. `passlib` + `bcrypt>=4.1` revienta → por eso `bcrypt==4.0.1` en requirements.
6. **`fileConfig` de Alembic** apaga los loggers existentes (`disable_existing_loggers`) → al migrar desde la app (`app/db/migrate.py`) se pasa `cfg.attributes["skip_logging_config"] = True` y `env.py` respeta ese flag; si no, uvicorn se queda sin logs al arrancar.
7. **Autogenerate necesita la BD vacía/limpia**: si la BD ya tiene tablas creadas fuera de Alembic no detecta nada → borrar el `.db` antes de generar la primera revisión (ya está reflejado en la revisión inicial).

## 7. BACKLOG — lo que hay que hacer ahora (por este orden)

### Tarea A ✅ (HECHA el 2026-10-15): Migraciones con Alembic
- `alembic/` + `alembic.ini` en `backend/`; `alembic/env.py` usa
  `settings.DATABASE_URL` y `Base.metadata` (importa `app.models`).
- Revisión inicial `eb665009a651_esquema_inicial.py` (14 tablas) generada con
  `--autogenerate` y verificada: 0 drift, upgrade/downgrade OK.
- `lifespan` de `app/main.py`: `run_migrations()` (`app/db/migrate.py`) sustituye a
  `create_all`; después seeds. Cubierto por `tests/migrations_test.py` (6 checks).
- Flujo documentado en `backend/README.md` §2.

### Tarea B ✅ (HECHA el 2026-10-19): Frontend Flutter (`frontend/` en la raíz)
- Instalación de Flutter SDK 3.47.7 en `C:\flutter`.
- Estructura limpia y desacoplada con Riverpod + GoRouter + Dio.
- Core: cliente HTTP Dio con `baseUrl`, `withCredentials` y `AuthInterceptor` para refresco automático ante 401; almacenamiento seguro de tokens con `flutter_secure_storage`.
- Modelos DTO completos (User, Group, Member, Game, Match, Confirmation, Stats, Leaderboard, Notification, Achievement).
- Pantallas implementadas:
  - Auth: Login y Registro con validaciones según reglas del backend.
  - Grupos: Lista de grupos, creación y unión por código; Detalle de grupo con 4 pestañas (Partidas, Clasificación/Leaderboard por temporada con soft reset, Catálogo con thumbnails, Miembros con roles).
  - Juegos: Buscador interactivo de BoardGameGeek (`BggSearchDialog`) para que el MANAGER agregue juegos al catálogo.
  - Partidas: Formulario completo de registro (`RegisterMatchScreen`) con selección de juego, multi-selección de jugadores y ganador; Pantalla de detalle (`MatchDetailScreen`) con estado de confirmaciones y acciones para Confirmar, Rechazar o Cancelar.
  - Notificaciones: Bandeja de avisos con marcado individual y masivo.
  - Logros: Catálogo de insignias y visualización de logros desbloqueados con fechas.
  - Perfil: Resumen de usuario, rol global y logout.
  - Widgets compartidos: `EloBadge` con colores personalizados por rango (Hierro, Bronce, Plata, Oro, Platino, Diamante).
- Compilación web exitosa: `build/web` generado sin errores.

### Tarea C ✅ (HECHA el 2026-10-19): Mejoras backend avanzadas, Seguridad y Catálogo
- **Transferencia de propiedad de grupo**: `POST /api/v1/groups/{group_id}/transfer-ownership` (solo propietario o ADMIN global; promueve al nuevo dueño a MANAGER).
- **Paginación real**: query params `limit` y `offset` añadidos en `matches`, `leaderboard`, `notifications` y `admin/users`.
- **Detección de reuso de refresh token**: revoca inmediatamente toda la familia de tokens del usuario si se intenta reutilizar un token ya consumido o rotado (prevención de ataques de replay/robo de cookie).
- **Notificaciones en tiempo real**: Server-Sent Events (SSE) vía `GET /api/v1/notifications/stream` con bus pub/sub asíncrono (`event_service.py`) transmitiendo eventos en vivo de confirmación de partida, rechazo y logros.
- **Rate limiting en login**: limitador de ventana deslizante en memoria (`rate_limit.py`) bloqueando fuerza bruta tras 5 intentos fallidos (devuelve HTTP 429 con cabecera `Retry-After`).
- **Gestión de avatar y perfil**: `PATCH /api/v1/auth/me` para actualizar `display_name` y `avatar_url`.
- **Recuperación de contraseña**: `POST /api/v1/auth/forgot-password` y `POST /api/v1/auth/reset-password` mediante token temporal firmado invalidable automáticamente tras el cambio y revocación de sesiones previas.
- **Base de datos de juegos y precarga**:
  - Los juegos viven en la tabla relacional `group_games` con metadatos completos BGG.
  - Añadido catálogo precargado `POPULAR_GAMES` en `app/db/seed.py` (Catan, Carcassonne, Pandemic, Ticket to Ride, Azul, Terraforming Mars, 7 Wonders).
  - Parámetro opcional `seed_popular: bool = True` en `POST /groups` para inicializar grupos con catálogo listo sin conexión externa.
  - Endpoint `POST /api/v1/groups/{group_id}/games/seed-popular` (MANAGER) para poblar juegos populares de forma idempotente.
- **Suite de pruebas y CI**:
  - `pytest` integrado: `pytest.ini` configurado y suite completa en `tests/test_api.py` (7 tests unitarios y de integración).
  - Workflow de integración continua en GitHub Actions: `.github/workflows/ci.yml`.
  - Mantenimiento y ampliación de tests independientes: `smoke_auth.py` ampliado a **28/28 OK**, `integration_test.py` ampliado a **56/56 OK**, `migrations_test.py` en **6/6 OK**.

### Tarea D ✅ (HECHA el 2026-10-19): Integración Frontend, Avatares Globales, Docker y Git
- **Sistema de Avatares y Fotos de Perfil**:
  - Backend: endpoint `POST /api/v1/auth/avatar` para subir fotos (.jpg/.png/.webp/.gif <= 5MB), guardadas en `backend/uploads/avatars/`. Directorio `/uploads/` montado como estático en FastAPI.
  - Esquemas y visibilidad global: `avatar_url` propagado a `MemberOut`, `GroupStatsOut`, `ParticipantOut` y `ConfirmationOut`. Todos los usuarios ven la foto de los demás en la lista de miembros, leaderboard de temporada y confirmaciones de partidas.
  - Frontend: componente reutilizable `UserAvatar` con carga remota de red, resolución automática de URLs estáticas (`resolveUrl`), fallback con iniciales deterministas y paleta de colores coherente.
  - Editor interactivo en `ProfileScreen`: selección de avatares temáticos predefinidos (guerrero, mago, rey, pícaro, bardo, bot), campo de URL personalizada y previsualización en vivo.
- **Conexión de Nuevas Funciones en Frontend**:
  - Transferencia de propiedad de grupo conectada en el menú contextual de miembros de `GroupDetailScreen` (`transferOwnership`).
  - Precarga de juegos populares conectada con botón de acción directa en la pestaña de catálogo (`seedPopularGames`).
  - Flujo interactivo de recuperación de contraseña ("¿Olvidaste tu contraseña?") implementado en `LoginScreen` con soporte para validación y reseteo por token.
- **Dockerización Completa**:
  - `backend/Dockerfile`: contenedor Python 3.12-slim con soporte para SQLite/PostgreSQL y volumen persistente de uploads.
  - `frontend/Dockerfile` + `frontend/nginx.conf`: contenedor multi-etapa con Flutter SDK y Nginx sirviendo la SPA con proxy reverso a `/api/`, `/uploads/` y `/docs`.
  - `docker-compose.yml`: orquestación de PostgreSQL 16, backend FastAPI y frontend web Nginx con healthchecks y volúmenes de datos.
- **Git y Preparación Móvil**:
  - Repositorio Git inicializado en la raíz con `.gitignore` exhaustivo (omitiendo `.venv`, `.dart_tool`, `build`, `.db`).
  - Primer commit limpio realizado.
  - `AndroidManifest.xml` actualizado con permisos `INTERNET`, `ACCESS_NETWORK_STATE`, `usesCleartextTraffic="true"` y label "Board Game Tracker".
- **Estado de Pruebas**:
  - `smoke_auth.py`: **28/28 OK**.
  - `integration_test.py`: **56/56 OK**.
  - `migrations_test.py`: **6/6 OK**.
  - `pytest`: **8/8 PASSED** (incluyendo `test_avatar_upload`).
  - `flutter build web`: compilado exitosamente en `frontend/build/web`.

## 8. Restricciones

- **No romper lo verificado**: al terminar, `tests/smoke_auth.py` = 28/28,
  `tests/integration_test.py` = 56/56, `tests/migrations_test.py` = 6/6 y
  `pytest` = 8/8 deben seguir en verde (o ampliar los tests si añades funcionalidad nueva).
- No cambiar el esquema de tokens/cookies sin actualizar `deps.py`, `security.py`
  y los tests a la vez.
- Mantener el Swagger limpio: `summary`/`description` en los endpoints.
- Si creas tablas nuevas, acuérdate de las relationships con `back_populates`
  y de los `flush()` con `autoflush=False`.

*(Documento actualizado el 2026-10-19: Tareas A (Alembic), B (Frontend Flutter Web), C (Mejoras Backend Avanzadas) y D (Conexión de Funciones, Fotos de Perfil Globales, Docker, Git y Móvil)
completadas al 100 % — Backend 28/28, 56/56, 6/6 y pytest 8/8 en verde; Frontend Flutter compilado exitosamente en Web; Docker Compose configurado; Git inicializado.
`backend/README.md` documenta la API completa en formato tabla; este AGENTS.md manda sobre el README.)*

