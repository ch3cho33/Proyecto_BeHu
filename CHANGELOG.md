# Changelog

Todos los cambios relevantes del backend BeHu se registran aquí.

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
