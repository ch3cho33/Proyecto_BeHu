# Changelog

Todos los cambios relevantes del backend BeHu se registran aquí.

## [2.0.0] — 2026-11-19 — Neobanco familiar

### Added

- Invitación familiar con consentimiento: `FamilyInvitation` queda `PENDING` hasta que el Junior acepta. Un Senior no se vincula. Un Junior con núcleo activo responde 409. Si el correo no existe, `create-junior` crea la cuenta y la mesada en el ledger.
- Gastos e ingresos con método de pago, nota, recurrencia y bucket 50/30/20. El nudge `GASTO_IMPULSIVO` marca `is_impulsive` y baja el Score. El Senior puede bloquear la tarjeta Junior.
- BeHu Mini detecta gastos hormiga (3 compras pequeñas de comida u ocio en 48 h), publica alertas parentales y responde con saldo líquido, saldo congelado y la regla 50/30/20.
- PWA en dark mode (Linear / Vercel): sidebar, barra inferior, dashboard, nudge, familia, academia y chat.
- `pytest` cubre consentimiento, saldo congelado, hormiga y la respuesta contextual.

## [1.0.4] — 2026-11-19 — SQLite en /tmp

### Fixed

- Sin `DATABASE_URL`, y con `VERCEL=1`, el fallback deja de ser `./behu_sandbox.db` (solo lectura en `/var/task`) y pasa a `sqlite+aiosqlite:////tmp/behu_sandbox.db`.
- `GET /api/health` y `GET /health` incluyen `dialect`, `vercel` y `auto_seed` para ver qué base recibió el servicio `app`.
- `docs/deployment.md` fija Root Directory en `.` y las variables en **All Services**. `next.config.ts` no reescribe `/api`.

## [1.0.3] — 2026-11-19 — Runtime Python en Vercel

### Fixed

- La URL de Neon ya no lleva `sslmode`, `channel_binding` ni `ssl` en el query. `asyncpg` recibe `ssl` por `connect_args` solo si el host no es local, así no aparece `unexpected keyword argument 'sslmode'`.
- `bcrypt` queda fijado en `4.0.1`. El hash sigue en `app/core/security.py` con la librería directa, sin `passlib`.
- `GET /health` y `GET /api/health` responden `200` sin abrir la base. `GET /api/v1/health/db` devuelve el error exacto de Neon en JSON. El lifespan ya no tumba la función si la base falla.
- `vercel.json` sigue enviando la ruta completa a `app.main:app`.

## [1.0.2] — 2026-11-19 — Arranque en Vercel

### Fixed

- `AUTO_SEED_SANDBOX=true` fuerza `AUTO_CREATE_TABLES` también en `ENVIRONMENT=production`, para que Neon no quede sin tablas.
- La primera petición a `/api` (incluido `/api/v1/auth/login`) ejecuta `create_all` y el seed una sola vez por instancia, aunque Vercel no dispare el lifespan.
- El login muestra `HTTP <código>` y el `detail` del servidor cuando la respuesta no es el JSON esperado.
- Las rutas de FastAPI siguen siendo `/api/v1/...`. Vercel entrega esa ruta completa; no se recorta `/api`.

## [1.0.1] — 2026-11-19 — Vercel Services

### Changed

- `vercel.json` en la raíz: servicios `app` (FastAPI) y `frontend` (Next.js) bajo el mismo dominio. `/api`, Swagger y `/health` van al API; el resto va a la PWA.
- El cliente de producción llama a `/api/v1` si `NEXT_PUBLIC_API_URL` está vacía. En local sigue usando `http://127.0.0.1:8000/api/v1`.
- Las URIs de Neon/Supabase convierten `sslmode` a `ssl` para asyncpg. El seed avisa si corre sobre SQLite en un entorno efímero.

## [1.0.0] — 2026-11-19 — Release MVP

### Added

- Arranque con `AUTO_SEED_SANDBOX=true`: crea el esquema, los usuarios de prueba, el catálogo y las tres cápsulas sin duplicar filas si el proceso reinicia.
- Suite `tests/test_e2e_mvp.py` (pytest + httpx) del ciclo HU-01 a HU-09.
- Guía de variables para Render, MongoDB Atlas y Vercel en `docs/deployment.md`.

## [0.4.0] — 2026-11-19 — Sprint 3

### Added

- Score BeHu `GET /api/v1/scoring/me`: puntaje 0-100, nivel, factores y consejos a partir del ledger, metas, compras forzadas y academia.
- Academia BeHu: `modulo_educativo`, `progreso_educativo`, tres cápsulas con quiz, insignia y puntos de score.
- Compras con `forzada=true` quedan marcadas para el score.
- PWA: manifiesto, iconos, service worker y Score/Academia en el dashboard.
- `FRONTEND_URL` se suma a CORS. `render.yaml` y `docs/deployment.md` para Render, Postgres y MongoDB Atlas.
- `app/core/storage.py`: KYC en S3 con boto3 o en `data/kyc/` si no hay credenciales.

### Notes

- Recrea `behu_sandbox.db` para la columna `forzada` y las tablas educativas.
- En producción `AUTO_CREATE_TABLES` queda en false; el esquema se crea con el comando de `docs/deployment.md`.

## [0.3.0] — 2026-11-19 — Sprint 2

### Added

- Compra simulada `POST /api/v1/transactions/spend` con catálogo `categoria_gasto` y alerta anti-impulsos (`409 GASTO_IMPULSIVO`) si se supera el límite diario/semanal o el 40% del saldo.
- Metas de ahorro (`meta_ahorro`): crear, listar progreso y abonar. El abono congela saldo con partida doble hacia `SANDBOX_META`.
- BeHu Mini: `POST /api/v1/ai/consult` y `GET /api/v1/ai/history`. MongoDB con fallback JSON local.
- Cuentas internas `SANDBOX_MERCHANT` y `SANDBOX_META`.
- `Dockerfile` y `docker-compose.yml` (API + Mongo).
- Frontend Next.js en `frontend/` (login, dashboard Senior/Junior, presupuesto, gasto y BeHu Mini).

### Notes

- El asistente es un motor de reglas contextualizado para el sandbox, no un LLM de terceros.
- Si la base SQLite es de Sprint 1, hay que recrearla (`rm behu_sandbox.db && python scripts/seed_sandbox.py`) para las columnas nuevas.

## [0.2.0] — 2026-11-15 — Sprint 1 / Fase 2

### Added

- Excepciones de dominio y mapeo HTTP (`app/services/exceptions.py`).
- Servicios: autenticación (registro + cuenta + JWT), supervisión parental, ledger de partida doble atómico, consulta de saldo derivado.
- API REST v1: `/auth/register`, `/auth/login`, `/accounts/me`, `/supervision/link`, `/supervision/juniors`, `/supervision/link/{id}`, `/transfers/budget`.
- Sandbox SQLite portable y script `scripts/seed_sandbox.py` (`senior@behu.test` / `junior@behu.test`).
- Cuentas puente `SANDBOX_FLOAT` y `SANDBOX_EQUITY` para funding inicial sin `UPDATE` suelto de saldo.
- CORS, `create_all` en desarrollo y handlers JSON `{ "detail": "..." }`.

### Notes

- MVP académico: no hay ACH, redes de tarjetas ni KMS/S3 cableados.
- Perfil Junior no ve movimientos con `es_transferencia_global = true`.

## [0.1.0] — 2026-10-13 — Sprint 1 / Fase 1

### Added

- Documentación de arquitectura (`docs/architecture.md`): capas FastAPI, contrato REST stateless para móvil/PWA, POO `CuentaSenior` / `CuentaJunior`, ledger de partida doble y despliegue Railway / Vercel / AWS.
- Esquema de datos (`docs/database_schema.md`): tablas PostgreSQL ACID, ledger inmutable y colecciones MongoDB `user_habits` / `ai_recommendations`.
- Núcleo de configuración y seguridad: Pydantic Settings, bcrypt, JWT con claims `sub`, `rol` (`SENIOR` \| `JUNIOR`) y `exp`.
- Conexiones políglotas: SQLAlchemy 2 (async PostgreSQL) y cliente Motor (MongoDB).
- Dependencias FastAPI: `get_db`, `get_current_user`, `require_role`.
- Modelos SQLAlchemy: `Usuario`, `Cuenta` / `CuentaSenior` / `CuentaJunior`, `SupervisionCuenta`, `Transaccion`, `LedgerContable`.
- Schemas Pydantic de contrato JSON para clientes móviles.
- `GET /health` y CORS configurable para desarrollo móvil/PWA.

### Notes

- Integración AWS S3 / KMS documentada, no cableada.
