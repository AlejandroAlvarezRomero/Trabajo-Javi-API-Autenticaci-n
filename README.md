# Board Game Tracker 🎲🏆

Plataforma distribuida integral para el registro, verificación y análisis competitivo de partidas de juegos de mesa en grupos privados. Incluye catálogo conectado con metadatos de BoardGameGeek (BGG), sistema ELO FIDE con rangos y temporadas trimestrales con *soft reset*, verificación por consenso entre jugadores, sistema de logros (badges), roles granulares (RBAC), fotos de perfil globales y despliegue multiplataforma (Web, Android, iOS y Docker).

---

## 🌟 Características Principales

- **Autenticación Robusta y Segura**:
  - Tokens JWT duales (Access Token de 15 min + Refresh Token de 14 días en cookie `HttpOnly`, `SameSite=Lax`).
  - Rotación estricta de *jti* con revocación automática de sesiones ante intentos de reuso.
  - Rate limiting adaptativo en inicio de sesión (bloqueo tras 5 intentos fallidos con cabecera `Retry-After`).
  - Flujo de recuperación de contraseñas mediante tokens temporales firmados.
- **Perfiles y Avatares Globales**:
  - Subida de fotos de perfil (JPG, PNG, WebP, GIF) servidas estáticamente en el backend.
  - Selector de avatares temáticos predefinidos y soporte para URLs externas (DiceBear, etc.).
  - Visibilidad transversal: las fotos de perfil se muestran en listas de miembros, clasificaciones por temporada y confirmaciones de partidas.
- **Grupos y Roles (RBAC)**:
  - Grupos privados accesibles mediante códigos únicos de invitación alfanuméricos.
  - Roles globales (`ADMIN`, `PLAYER`) y roles contextuales por grupo (`MANAGER`, `MEMBER`).
  - Transferencia segura de propiedad de grupo y moderación de miembros.
- **Catálogo de Juegos y BoardGameGeek**:
  - Búsqueda en vivo contra la XML API 2 de BGG y precarga de metadatos (jugadores, duración, thumbnails).
  - Precarga offline instantánea de juegos populares (Catan, Carcassonne, Pandemic, Ticket to Ride, Azul, Terraforming Mars, 7 Wonders).
- **Partidas y Verificación ELO**:
  - Registro colaborativo en estado pendiente (`PENDING`) con notificaciones en vivo.
  - Verificación por consenso: requiere la confirmación del 100% de participantes rivales para consolidarse.
  - Sistema ELO tipo ajedrez con expectativa FIDE ponderada por rivales ($k=32$).
  - 6 rangos competitivos: **Hierro**, **Bronce**, **Plata**, **Oro**, **Platino** y **Diamante**.
  - Temporadas de 92 días con *soft reset* (regresión del 50% hacia la media 1200) preservando el histórico inmutable.
- **Sistema de Logros e Insignias**:
  - Reconocimiento automático al consolidar partidas (Primera Victoria, Racha de 5 victorias, Veterano, Centurión).
- **Notificaciones en Tiempo Real**:
  - Server-Sent Events (SSE) vía `/api/v1/notifications/stream` para eventos en directo.

---

## 🏗️ Arquitectura del Sistema

```
Trabajo Autenticacion/
├── backend/                  # API REST FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/v1/           # 9 routers: auth, groups, games, matches, seasons, stats, etc.
│   │   ├── core/             # Configuración, seguridad JWT, RBAC y utilidades de tiempo
│   │   ├── db/               # Sesión SQLAlchemy, migraciones automáticas y seeds
│   │   ├── models/           # 14 modelos relacionales mapeados con SQLAlchemy 2.0
│   │   ├── schemas/          # Modelos Pydantic v2 (DTOs de entrada y salida)
│   │   └── services/         # ELO FIDE, BGG API, eventos SSE, logros y temporadas
│   ├── alembic/              # Control de versiones de base de datos
│   ├── tests/                # 4 suites de prueba: smoke_auth, integration, migrations, pytest
│   ├── Dockerfile            # Imagen backend Python 3.12-slim
│   └── requirements.txt
├── frontend/                 # Aplicación Flutter (Web / Android / iOS)
│   ├── lib/
│   │   ├── core/             # Cliente HTTP Dio con interceptor de refresco silencioso y temas
│   │   ├── features/         # Módulos por pantalla: auth, groups, games, matches, stats, profile
│   │   └── shared/           # Modelos DTO y widgets compartidos (UserAvatar, EloBadge)
│   ├── android/              # Configuración Android con permisos de red e iconos
│   ├── web/                  # Shell web y manifiesto PWA
│   ├── nginx.conf            # Proxy inverso y enrutamiento SPA
│   └── Dockerfile            # Construcción multi-etapa Flutter Web + Nginx
├── docker-compose.yml        # Orquestación de BD PostgreSQL, Backend y Frontend Web
└── AGENTS.md                 # Documento de traspaso y especificación técnica
```

---

## 🚀 Despliegue Rápido con Docker Compose

La forma más sencilla de arrancar todo el ecosistema (PostgreSQL + FastAPI + Flutter Web Nginx):

```powershell
docker-compose up --build
```

Una vez levantado:
- **Frontend Web**: [http://localhost](http://localhost)
- **API Backend & Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Base de Datos PostgreSQL**: `localhost:5432` (`user: postgres`, `password: postgrespassword`, `db: boardgames`)

---

## 💻 Desarrollo Local

### 1. Backend (FastAPI + SQLite/Postgres)

```powershell
cd backend

# Activar entorno virtual existente
.venv\Scripts\activate

# Ejecutar el servidor con recarga en caliente
uvicorn app.main:app --reload --port 8000
```

#### Ejecutar Batería Completa de Pruebas:
```powershell
# 1. Autenticación, JWT dual, rotación, rate-limit y ELO puro (28 checks)
python tests/smoke_auth.py

# 2. Flujo E2E completo: grupos, BGG, partidas, confirmaciones, rollover (56 checks)
python tests/integration_test.py

# 3. Ciclo de migraciones Alembic (up/down/drift) (6 checks)
python tests/migrations_test.py

# 4. Suite Pytest con CI (8 tests)
pytest
```

*Estado actual: **28/28**, **56/56**, **6/6** y **8/8 PASSED**.*

---

### 2. Frontend (Flutter)

```powershell
cd frontend

# Obtener dependencias
flutter pub get

# Compilar para Web en modo release
flutter build web --no-tree-shake-icons

# Ejecutar en modo desarrollo
flutter run -d chrome
```

---

## 📱 Soporte Móvil

- **Android**: [`android/app/src/main/AndroidManifest.xml`](frontend/android/app/src/main/AndroidManifest.xml) incluye los permisos requeridos (`INTERNET`, `ACCESS_NETWORK_STATE`) y `usesCleartextTraffic="true"` para entornos locales de prueba.
- Para compilar APK de Android:
  ```powershell
  cd frontend
  flutter build apk --release
  ```

---

## 🛡️ Licencia y Mantenimiento

Proyecto desarrollado siguiendo la especificación y reglas de negocio documentadas en [AGENTS.md](AGENTS.md).
