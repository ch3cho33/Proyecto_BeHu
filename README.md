# BeHu

Plataforma Fintech de cuentas transaccionales, control parental e IA predictiva (BeHu Mini) para el mercado colombiano — Jäger Group (Pontificia Universidad Javeriana).

El backend es un API REST **stateless** (FastAPI) pensado para **app móvil iOS/Android y PWA Next.js**. Las sesiones de dispositivo se resuelven con JWT (`sub`, `rol`, `exp`). El Sprint 1 es un **MVP sandbox**: ledger de partida doble, roles Senior/Junior y sin ACH ni redes de tarjetas reales.

## Stack (Sprint 1)

- Python 3.11+
- FastAPI + Pydantic v2
- SQLite (sandbox local) o PostgreSQL (SQLAlchemy 2 async)
- MongoDB (Motor) — hábitos y recomendaciones de IA (contrato)
- JWT + bcrypt

Documentación:

- [Arquitectura](docs/architecture.md)
- [Esquema de datos](docs/database_schema.md)
- [Changelog](CHANGELOG.md)

## Requisitos

- Python 3.11 o superior
- SQLite (incluido) para el sandbox local; PostgreSQL 15+ es opcional
- MongoDB 6+ opcional; el healthcheck no lo exige

## Configuración del entorno

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env.example` apunta a `sqlite+aiosqlite:///./behu_sandbox.db`. No commitees `.env`.

## Arranque local y seed

```bash
source .venv/bin/activate
python scripts/seed_sandbox.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Usuarios del sandbox:

| Rol | Email | Password | Saldo |
| --- | --- | --- | --- |
| SENIOR | `senior@behu.test` | `BeHuSenior1!` | 1.000.000 COP |
| JUNIOR | `junior@behu.test` | `BeHuJunior1!` | 0 COP (vinculado) |

En `/docs`: `POST /api/v1/auth/login` → copiar `access_token` → botón **Authorize** → `Bearer <token>`.

Prueba sugerida: con el token Senior, `GET /api/v1/accounts/me`, `GET /api/v1/supervision/juniors` y `POST /api/v1/transfers/budget`. Con el token Junior, `GET /api/v1/accounts/me` (sin transferencias globales).

## Sprint 2 (hábitos, metas, Docker, frontend)

Backend local (recrea la base si vienes del Sprint 1):

```bash
rm -f behu_sandbox.db
python scripts/seed_sandbox.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Abre [http://127.0.0.1:3000](http://127.0.0.1:3000). Docker:

```bash
docker compose up --build
docker compose exec backend python scripts/seed_sandbox.py
```

## Rama de trabajo

Sprint 3: `feature/sprint-3-scoring-educacion-pwa` → integrar en `develop`.

Despliegue: [docs/deployment.md](docs/deployment.md). Score: `GET /api/v1/scoring/me`. Academia: `GET /api/v1/education/modules`. Si cambió el esquema, borra `behu_sandbox.db` y vuelve a correr el seed.

## Despliegue objetivo

| Pieza | Destino |
| --- | --- |
| API FastAPI | Railway |
| PWA Next.js | Vercel |
| KYC | AWS S3 |
| Llaves | AWS KMS |
