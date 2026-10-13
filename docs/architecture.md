# Arquitectura BeHu — Sprint 1

BeHu es un banco Fintech para el mercado colombiano (Jäger Group / Pontificia Universidad Javeriana). El canal principal de consumo es **aplicación móvil (iOS / Android) y PWA Next.js**. El backend FastAPI es un API REST **stateless**: cada petición se autentica con JWT; no hay sesiones de servidor ni cookies de autenticación.

## 1. Componentes

| Capa | Tecnología | Responsabilidad |
| --- | --- | --- |
| Clientes | iOS / Android / PWA (Next.js en Vercel) | UI, almacenamiento seguro del JWT, claims `rol` |
| API | FastAPI (Python 3.11+), Railway | Autenticación, cuentas, supervisión parental, ledger |
| Relacional | PostgreSQL | Entidades ACID: usuario, cuenta, supervisión, transacción, ledger |
| Documental | MongoDB | Hábitos no estructurados e historial de recomendaciones de IA |
| Objetos | AWS S3 | Documentos KYC (contrato; no implementado en Fase 1) |
| Llaves | AWS KMS | Cifrado de secretos y PII (contrato; no implementado en Fase 1) |

Separación de capas del backend:

```
app/
  core/       # config, seguridad JWT, conexiones DB
  models/     # SQLAlchemy (persistencia)
  schemas/    # Pydantic (contrato JSON móvil)
  services/   # reglas de negocio (Fase 2)
  api/        # routers HTTP (Fase 2)
```

El contrato público **nunca** expone modelos ORM. Toda respuesta es un schema Pydantic serializado a JSON liviano (`snake_case`), sin hashes, sin asientos internos innecesarios y sin transferencias globales en perfiles `JUNIOR`.

## 2. Contrato API REST (móvil / PWA)

Principios:

- **Stateless.** Autenticación únicamente por `Authorization: Bearer <access_token>`.
- **JWT con expiración.** Claims obligatorios: `sub` (id de usuario), `rol` (`SENIOR` \| `JUNIOR`), `exp`, `iat`.
- **Respuestas pequeñas.** Un objeto (o lista acotada) por recurso; paginación futura por cursor.
- **Errores predecibles.** HTTP status estándar + cuerpo `{ "detail": "..." }` (FastAPI).
- **CORS.** Orígenes configurables para PWA y desarrollo Expo/metro (`localhost`, emuladores).

Healthcheck (Fase 1): `GET /health` → `{ "status": "ok", "service": "behu-api", "version": "0.1.0" }`.

Routers de negocio (Fase 2, misma arquitectura):

| Recurso | Uso móvil |
| --- | --- |
| `POST /api/v1/auth/register` | Alta; hashing bcrypt; no devuelve password |
| `POST /api/v1/auth/login` | Emite JWT + `expires_in` + `rol` |
| `GET /api/v1/accounts/me` | Saldo y límites; Junior no ve red global |
| `POST /api/v1/supervision` | Vínculo Senior→Junior y presupuesto |
| `POST /api/v1/transfers` | Movimiento con partida doble |
| `DELETE /api/v1/supervision/{id}` | Desvinculación con confirmación |

## 3. Autenticación y roles (RF-01, RF-02)

1. Registro: email único, contraseña hasheada con bcrypt, rol explícito `SENIOR` o `JUNIOR`.
2. Login: verificación de hash; emisión de access token.
3. Dependencias FastAPI:
   - `get_current_user`: valida firma, expiración y usuario activo.
   - `require_role("SENIOR")` / `require_role("JUNIOR")`: aislamiento de perfil.

El cliente móvil persiste el token (Keychain / Keystore / almacenamiento PWA) y lo envía en cada request. El servidor no guarda el token.

## 4. Diseño POO de cuentas

```
Cuenta (clase base, mapeo polimórfico SQLAlchemy)
 ├── CuentaSenior   # puede patrocinar N cuentas junior
 └── CuentaJunior   # techos de gasto; visibilidad restringida
```

- `Cuenta` define saldo, moneda `COP`, estado y dueño (`usuario_id`).
- `CuentaSenior` especializa operaciones de supervisión y transferencias de red.
- `CuentaJunior` especializa `limite_gasto_diario` / `limite_gasto_mensual` y oculta transferencias globales (RF-06).
- La relación parental no vive en la cuenta: vive en `SupervisionCuenta` (RF-03, RF-05) para permitir historial de vínculo, presupuesto asignado y desvinculación con alerta/confirmación.

## 5. Ledger de partida doble (RF-04)

Ningún movimiento actualiza un saldo de forma aislada. El servicio de ledger (Fase 2) en una sola transacción SQL:

1. Crea `Transaccion` (cabecera de negocio).
2. Inserta **dos** asientos inmutables en `LedgerContable`: débito en origen y crédito en destino, mismo `monto`.
3. Actualiza saldos de `Cuenta` de forma atómica, o los deriva de la suma de asientos.

Invariante: para cada `transaccion_id`, `SUM(debito) = SUM(credito)`. Los asientos no se actualizan ni se borran.

## 6. Persistencia políglota

- **PostgreSQL:** verdad transaccional y de identidad (ACID).
- **MongoDB:** `user_habits` (eventos de hábito) y `ai_recommendations` (contexto de BeHu Mini). El cliente Motor queda cableado en Fase 1; las colecciones no son RF de autenticación.

## 7. Despliegue

| Componente | Destino |
| --- | --- |
| Backend FastAPI | Railway (`behu-api`) |
| Frontend / PWA | Vercel (Next.js) |
| KYC (objetos) | AWS S3 |
| Cifrado de llaves | AWS KMS |

Variables de entorno (12-factor) vía `app/core/config.py`. Secretos de JWT y cadenas de conexión **nunca** se commitean. Fase 1 deja el contrato KMS/S3 documentado; la integración cloud se implementa en sprints posteriores.

## 8. Seguridad (línea base Fase 1)

- Hashing de contraseñas: bcrypt.
- JWT firmado (HS256 en desarrollo; rotación/KMS en producción).
- CORS restrictivo por lista de orígenes.
- Schemas públicos sin `password_hash` ni PII innecesaria.
- Aislamiento de roles en dependencia, no solo en el cliente.
