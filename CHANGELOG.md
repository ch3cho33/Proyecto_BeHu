# Changelog

Todos los cambios relevantes del backend BeHu se registran aquí.

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

- Sin endpoints de negocio (auth, supervisión, transferencias): Fase 2.
- Integración AWS S3 / KMS documentada, no cableada.
