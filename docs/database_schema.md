# Esquema de datos BeHu — Sprint 1

Persistencia políglota: PostgreSQL (ACID) para el núcleo transaccional e identidad; MongoDB para hábitos y contexto de IA.

Tipos monetarios: `NUMERIC(18, 2)`, moneda por defecto `COP`.
Identificadores: `UUID` (`gen_random_uuid()`).
Timestamps: `TIMESTAMPTZ` (`created_at`, `updated_at` donde aplique).

---

## 1. PostgreSQL / SQLAlchemy

### 1.1 `usuario`

Identidad de login y perfil. Un usuario tiene exactamente una cuenta transaccional de su rol.

| Columna | Tipo | Restricciones |
| --- | --- | --- |
| `id` | UUID | PK |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL |
| `password_hash` | VARCHAR(255) | NOT NULL |
| `nombres` | VARCHAR(120) | NOT NULL |
| `apellidos` | VARCHAR(120) | NOT NULL |
| `rol` | VARCHAR(20) | NOT NULL, `SENIOR` \| `JUNIOR` |
| `telefono` | VARCHAR(32) | NULL |
| `is_active` | BOOLEAN | NOT NULL, default true |
| `kyc_status` | VARCHAR(32) | default `PENDING` |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

Índices: `uq_usuario_email`, `ix_usuario_rol`.

### 1.2 `cuenta`

Herencia de tabla única (`polymorphic_on = tipo`). `SENIOR` y `JUNIOR` comparten columnas; las de límite aplican a junior.

| Columna | Tipo | Restricciones |
| --- | --- | --- |
| `id` | UUID | PK |
| `usuario_id` | UUID | FK `usuario.id`, UNIQUE, NOT NULL |
| `tipo` | VARCHAR(20) | NOT NULL, `SENIOR` \| `JUNIOR` (discriminador) |
| `saldo` | NUMERIC(18, 2) | NOT NULL, default 0, CHECK `>= 0` |
| `moneda` | CHAR(3) | NOT NULL, default `COP` |
| `estado` | VARCHAR(20) | NOT NULL, `ACTIVA` \| `BLOQUEADA` \| `CERRADA` |
| `limite_gasto_diario` | NUMERIC(18, 2) | NULL (junior) |
| `limite_gasto_mensual` | NUMERIC(18, 2) | NULL (junior) |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

Índices: `uq_cuenta_usuario_id`, `ix_cuenta_tipo`.

Mapeo POO:

- `Cuenta` → filas de `cuenta`
- `CuentaSenior` → `tipo = SENIOR`
- `CuentaJunior` → `tipo = JUNIOR`

### 1.3 `supervision_cuenta`

Vínculo parental (RF-03, RF-05). El presupuesto asignado al junior vive aquí, no en un campo suelto de usuario.

| Columna | Tipo | Restricciones |
| --- | --- | --- |
| `id` | UUID | PK |
| `cuenta_senior_id` | UUID | FK `cuenta.id`, NOT NULL |
| `cuenta_junior_id` | UUID | FK `cuenta.id`, NOT NULL |
| `presupuesto_periodico` | NUMERIC(18, 2) | NOT NULL, default 0, CHECK `>= 0` |
| `periodicidad` | VARCHAR(20) | NOT NULL, `SEMANAL` \| `MENSUAL` |
| `estado` | VARCHAR(20) | NOT NULL, `ACTIVA` \| `PENDIENTE_DESVINCULO` \| `DESVINCULADA` |
| `alerta_desvinculo` | BOOLEAN | NOT NULL, default false |
| `confirmado_desvinculo_en` | TIMESTAMPTZ | NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

Índices: `uq_supervision_par` UNIQUE (`cuenta_senior_id`, `cuenta_junior_id`), `ix_supervision_estado`.
CHECK: `cuenta_senior_id <> cuenta_junior_id`.

### 1.4 `transaccion`

Cabecera de negocio de un movimiento. No sustituye al ledger.

| Columna | Tipo | Restricciones |
| --- | --- | --- |
| `id` | UUID | PK |
| `tipo` | VARCHAR(32) | NOT NULL (`TRANSFERENCIA_INTERNA`, `ASIGNACION_PRESUPUESTO`, `REVERSO`) |
| `estado` | VARCHAR(20) | NOT NULL, `PENDIENTE` \| `COMPLETADA` \| `RECHAZADA` |
| `monto` | NUMERIC(18, 2) | NOT NULL, CHECK `> 0` |
| `moneda` | CHAR(3) | NOT NULL, default `COP` |
| `descripcion` | VARCHAR(280) | NULL |
| `iniciada_por_usuario_id` | UUID | FK `usuario.id`, NOT NULL |
| `es_transferencia_global` | BOOLEAN | NOT NULL, default false (oculta a perfiles Junior) |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

### 1.5 `ledger_contable`

Libro mayor **inmutable** (sin `updated_at`, sin UPDATE/DELETE de aplicación).

| Columna | Tipo | Restricciones |
| --- | --- | --- |
| `id` | UUID | PK |
| `transaccion_id` | UUID | FK `transaccion.id`, NOT NULL |
| `cuenta_id` | UUID | FK `cuenta.id`, NOT NULL |
| `naturaleza` | VARCHAR(10) | NOT NULL, `DEBITO` \| `CREDITO` |
| `monto` | NUMERIC(18, 2) | NOT NULL, CHECK `> 0` |
| `created_at` | TIMESTAMPTZ | NOT NULL |

Índices: `ix_ledger_transaccion_id`, `ix_ledger_cuenta_id`.

**Invariante de partida doble:** para cada `transaccion_id` deben existir al menos dos asientos y `SUM(monto) FILTER (DEBITO) = SUM(monto) FILTER (CREDITO)`.

Flujo atómico (una transacción SQL):

1. Insertar `transaccion`.
2. Insertar asiento `DEBITO` en cuenta origen (disminuye saldo).
3. Insertar asiento `CREDITO` en cuenta destino (aumenta saldo).
4. Actualizar `cuenta.saldo` de origen y destino con `SELECT … FOR UPDATE`.

### 1.6 Esquema reservado (sin endpoints en Fase 1)

**`tarjeta`**

| Columna | Tipo |
| --- | --- |
| `id` | UUID PK |
| `cuenta_id` | UUID FK |
| `pan_token` | VARCHAR (tokenizado; nunca PAN en claro) |
| `ultimos_4` | CHAR(4) |
| `estado` | VARCHAR |
| `created_at` / `updated_at` | TIMESTAMPTZ |

**`presupuesto_ia`**

| Columna | Tipo |
| --- | --- |
| `id` | UUID PK |
| `cuenta_id` | UUID FK |
| `categoria` | VARCHAR |
| `monto_sugerido` | NUMERIC(18, 2) |
| `periodo` | VARCHAR |
| `origen_modelo` | VARCHAR |
| `created_at` / `updated_at` | TIMESTAMPTZ |

---

## 2. MongoDB

Base: `behu` (configurable). El núcleo transaccional **no** escribe aquí.

### 2.1 Colección `user_habits`

Historial no estructurado de hábitos financieros (BeHu Mini).

```json
{
  "_id": "ObjectId",
  "usuario_id": "uuid-string",
  "cuenta_id": "uuid-string",
  "evento": "ahorro | gasto | meta | racha",
  "payload": {},
  "ocurrio_en": "ISO-8601",
  "created_at": "ISO-8601"
}
```

Índices: `{ usuario_id: 1, ocurrio_en: -1 }`.

### 2.2 Colección `ai_recommendations`

Logs y contexto de recomendaciones.

```json
{
  "_id": "ObjectId",
  "usuario_id": "uuid-string",
  "cuenta_id": "uuid-string",
  "modelo": "behu-mini",
  "prompt_contexto": {},
  "recomendacion": {},
  "aceptada": null,
  "created_at": "ISO-8601"
}
```

Índices: `{ usuario_id: 1, created_at: -1 }`.

---

## 3. Reglas de visibilidad (RF-06)

- Perfil `JUNIOR`: consulta saldo y límites de **su** cuenta; no lista `transaccion.es_transferencia_global = true`.
- Perfil `SENIOR`: saldo propio, cuentas junior vinculadas vía `supervision_cuenta.estado = ACTIVA`, y movimientos de supervisión/presupuesto.
