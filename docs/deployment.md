# Despliegue BeHu v1.0.0 — Vercel, Render y MongoDB Atlas

BeHu v1.0.0 es el sandbox académico completo: cuentas Senior/Junior, ledger de partida doble, presupuesto, compras con alerta, metas, BeHu Mini, Score y Academia. El API corre en **Render** (imagen Docker) y la PWA en **Vercel**.

## 0. Pruebas antes de desplegar

```bash
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

`tests/test_e2e_mvp.py` usa una SQLite propia (`test_mvp.db`) y no toca `behu_sandbox.db`. Cubre registro y JWT, presupuesto con partida doble, gasto impulsivo, meta que congela saldo, BeHu Mini por rol, score y quiz.

## 1. Frontend en Vercel

1. Importa el repo y define el directorio raíz `frontend`.
2. Variable de entorno: `NEXT_PUBLIC_API_URL=https://<servicio-render>.onrender.com/api/v1`.
3. El manifiesto en `frontend/public/manifest.json` y los iconos permiten instalar la PWA desde el navegador del teléfono (HTTPS de Vercel).

## 2. Backend en Render

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

En Vercel, directorio `frontend`, una sola variable: `NEXT_PUBLIC_API_URL=https://<servicio>.onrender.com/api/v1`.

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
