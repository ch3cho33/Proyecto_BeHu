# BeHu

Plataforma Fintech de cuentas transaccionales, control parental e IA predictiva (BeHu Mini) para el mercado colombiano — Jäger Group (Pontificia Universidad Javeriana).

El backend es un API REST **stateless** (FastAPI) pensado para **app móvil iOS/Android y PWA Next.js**. Las sesiones de dispositivo se resuelven con JWT (`sub`, `rol`, `exp`).

## Stack (Sprint 1)

- Python 3.11+
- FastAPI + Pydantic v2
- PostgreSQL (SQLAlchemy 2 async) — núcleo ACID
- MongoDB (Motor) — hábitos y recomendaciones de IA
- JWT + bcrypt

Documentación:

- [Arquitectura](docs/architecture.md)
- [Esquema de datos](docs/database_schema.md)
- [Changelog](CHANGELOG.md)

## Requisitos

- Python 3.11 o superior
- PostgreSQL 15+ (local o Railway)
- MongoDB 6+ (opcional en Fase 1; el healthcheck no lo exige)

## Configuración del entorno

```bash
cd Proyecto_BeHu
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` con `DATABASE_URL`, `MONGODB_URI` y un `JWT_SECRET` de al menos 32 caracteres. No commitees `.env`.

## Arranque local

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

CORS en desarrollo acepta orígenes de PWA/Expo definidos en `CORS_ORIGINS`.

## Rama de trabajo

Sprint 1 / HU-01: `feature/HU-01-autenticacion-y-roles` → integrar en `develop`.

## Despliegue objetivo

| Pieza | Destino |
| --- | --- |
| API FastAPI | Railway |
| PWA Next.js | Vercel |
| KYC | AWS S3 |
| Llaves | AWS KMS |
