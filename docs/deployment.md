# Despliegue BeHu — Vercel, Render, Neon/Render Postgres y MongoDB Atlas

El MVP no usa Railway. El API corre en **Render** (imagen Docker) y la PWA en **Vercel**.

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

En producción `AUTO_CREATE_TABLES=false`. Antes del primer tráfico, crea el esquema (job o shell de Render):

```bash
python -c "import asyncio; from app.core.database import create_schema; asyncio.run(create_schema())"
python scripts/seed_sandbox.py
```

El seed es de sandbox académico. En un entorno real no uses las contraseñas de prueba.

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
