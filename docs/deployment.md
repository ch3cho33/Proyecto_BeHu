# Despliegue BeHu v1.0.0 — Vercel Services, Postgres y MongoDB Atlas

BeHu v1.0.0 es el sandbox académico completo: cuentas Senior/Junior, ledger de partida doble, presupuesto, compras con alerta, metas, BeHu Mini, Score y Academia.

El proyecto se publica como **un solo proyecto de Vercel Services** (`vercel.json` en la raíz). El mismo dominio sirve la PWA y el API.

| Servicio | Raíz | Qué es |
| --- | --- | --- |
| `app` | `.` | FastAPI (`app.main:app`) |
| `frontend` | `frontend` | Next.js / PWA |

Rutas públicas, de la más específica a la general:

| Ruta | Servicio |
| --- | --- |
| `/api/...` | `app` |
| `/docs`, `/redoc`, `/openapi.json`, `/health` | `app` |
| el resto (`/`, estáticos, PWA) | `frontend` |

No hay binding interno. El navegador llama a `/api/v1` en el mismo origen. Un binding solo inyecta una URL en código de servidor, y esta PWA llama al API desde el cliente.

## Variables en Vercel

| Variable | Dónde | Valor |
| --- | --- | --- |
| `DATABASE_URL` | servicio `app` | URI de Neon o Supabase. `postgres://` se convierte a `postgresql+asyncpg://`. `sslmode=require` pasa a `ssl=require`. |
| `AUTO_SEED_SANDBOX` | `app` | `true` solo en este sandbox. El arranque crea tablas, `senior@behu.test`, `junior@behu.test` y las 3 cápsulas. Un reinicio no duplica filas. |
| `AUTO_CREATE_TABLES` | `app` | `false` si el seed ya crea el esquema |
| `JWT_SECRET` | `app` | 32 caracteres o más |
| `MONGODB_URI` | `app` | `mongodb+srv://...` de Atlas |
| `MONGODB_DB` | `app` | `behu` |
| `FRONTEND_URL` | `app` | URL pública de Vercel, por si un cliente externo llama al API |
| `NEXT_PUBLIC_API_URL` | `frontend` | Déjala **vacía** en Vercel. El build de producción usa `/api/v1`. En local el ejemplo apunta a `http://127.0.0.1:8000/api/v1`. |

No uses SQLite en Vercel: el disco de la función desaparece. Sin `DATABASE_URL` de Postgres el seed no sobrevive al siguiente arranque.

Usuarios del seed: `senior@behu.test` / `BeHuSenior1!` y `junior@behu.test` / `BeHuJunior1!`.

## 0. Pruebas antes de desplegar

```bash
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

`tests/test_e2e_mvp.py` usa una SQLite propia (`test_mvp.db`) y no toca `behu_sandbox.db`. Cubre registro y JWT, presupuesto con partida doble, gasto impulsivo, meta que congela saldo, BeHu Mini por rol, score y quiz.

## 1. Frontend en el mismo proyecto

El servicio `frontend` ya vive en este despliegue. No hace falta un segundo proyecto de Vercel ni un `NEXT_PUBLIC_API_URL` apuntando a otro host. El manifiesto en `frontend/public/manifest.json` sigue permitiendo instalar la PWA.

## 2. Alternativa: backend en Render

`render.yaml` describe el servicio web Docker y una base Postgres.

Variables que debes completar en el panel (marcadas `sync: false`):

| Variable | Valor |
| --- | --- |
| `MONGODB_URI` | Cadena de MongoDB Atlas (`mongodb+srv://...`) |
| `FRONTEND_URL` | Origen exacto de Vercel, por ejemplo `https://behu.vercel.app` |
| `AWS_S3_KYC_BUCKET` | Bucket de documentos KYC, si ya existe |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Llaves con permiso `s3:PutObject` |

`DATABASE_URL` sale de la base `behu-postgres`. El API convierte `postgres://` y `postgresql://` a `postgresql+asyncpg://`.

Con `AUTO_SEED_SANDBOX=true` el arranque crea las tablas si faltan y carga el sandbox una sola vez. Un reinicio vuelve a pasar por el seed y no duplica usuarios ni módulos. Déjalo en `false` fuera de este sandbox académico.

Variables exactas del servicio web:

| Variable | Valor en Render |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `AUTO_CREATE_TABLES` | `false` |
| `AUTO_SEED_SANDBOX` | `true` |
| `DATABASE_URL` | Connection string de la Postgres de Render (la inyecta `render.yaml`) |
| `MONGODB_URI` | URI de Atlas, `mongodb+srv://USER:PASSWORD@CLUSTER.mongodb.net` |
| `MONGODB_DB` | `behu` |
| `JWT_SECRET` | Secreto de al menos 32 caracteres (Render puede generarlo) |
| `FRONTEND_URL` | Origen de Vercel, por ejemplo `https://behu.vercel.app` |
| `CORS_ORIGINS` | Opcional. `FRONTEND_URL` ya se suma solo |
| `AWS_REGION` | `us-east-1` |
| `AWS_S3_KYC_BUCKET` | Vacío hasta tener bucket |
| `AWS_ACCESS_KEY_ID` | Vacío hasta tener llave |
| `AWS_SECRET_ACCESS_KEY` | Vacío hasta tener llave |

Si el API vive en Render y la PWA en otro host, `NEXT_PUBLIC_API_URL` debe ser `https://<servicio>.onrender.com/api/v1`. En el proyecto unificado de Vercel esa variable se deja vacía.

Usuarios que crea el seed: `senior@behu.test` / `BeHuSenior1!` y `junior@behu.test` / `BeHuJunior1!`.

## 3. MongoDB Atlas

1. Crea un cluster y un usuario de base `behu`.
2. Permite la salida de Render (o `0.0.0.0/0` solo mientras dure el sandbox).
3. Pega la URI en `MONGODB_URI`. Si Atlas no responde, BeHu Mini cae al archivo local `data/behu_ai_store.json`, que en Render no persiste entre deploys. En producción la URI debe estar bien.

## 4. KYC y S3

`app/core/storage.py`:

- Sin bucket o sin llaves: guarda el archivo en `data/kyc/` y responde `modo=local`.
- Con `AWS_S3_KYC_BUCKET`, `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`: sube el objeto con boto3 y responde `modo=s3`.

Prueba: `POST /api/v1/kyc/document` con el JWT y un archivo multipart `archivo`.

## 5. CORS

Los orígenes salen de `CORS_ORIGINS` más `FRONTEND_URL`. El dominio de Vercel tiene que coincidir carácter por carácter, incluido `https`.
