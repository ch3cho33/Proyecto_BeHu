"""Ciclo MVP BeHu v1.0.0 contra la app ASGI (sin red externa)."""

from decimal import Decimal

import httpx
import pytest

from app.core.security import decode_access_token
from scripts.seed_sandbox import JUNIOR_EMAIL, JUNIOR_PASSWORD, SENIOR_EMAIL, SENIOR_PASSWORD, seed


@pytest.fixture
async def client():
    await seed()
    await seed()
    transport = httpx.ASGITransport(app=__import__("app.main", fromlist=["app"]).app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _login(client: httpx.AsyncClient, email: str, password: str) -> dict:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_seed_is_idempotent():
    await seed()
    await seed()
    from sqlalchemy import func, select

    from app.core.database import AsyncSessionLocal
    from app.models.education import ModuloEducativo
    from app.models.user import Usuario

    async with AsyncSessionLocal() as db:
        seniors = await db.scalar(
            select(func.count()).select_from(Usuario).where(Usuario.email == SENIOR_EMAIL)
        )
        modulos = await db.scalar(select(func.count()).select_from(ModuloEducativo))
    assert seniors == 1
    assert modulos == 5


@pytest.mark.asyncio
async def test_mvp_cycle(client: httpx.AsyncClient):
    # HU-01 registro y JWT
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "nuevo@behu.test",
            "password": "BeHuNuevo1!",
            "nombres": "Nueva",
            "apellidos": "Cuenta",
            "rol": "SENIOR",
        },
    )
    assert registered.status_code == 201, registered.text
    body = registered.json()
    claims = decode_access_token(body["access_token"])
    assert claims["rol"] == "SENIOR"
    assert claims["sub"] == str(body["user"]["id"])
    assert body["token_type"] == "bearer"

    senior = await _login(client, SENIOR_EMAIL, SENIOR_PASSWORD)
    junior = await _login(client, JUNIOR_EMAIL, JUNIOR_PASSWORD)
    assert decode_access_token(junior["access_token"])["rol"] == "JUNIOR"
    hs = _auth(senior["access_token"])
    hj = _auth(junior["access_token"])

    # HU-02 / HU-04 presupuesto y partida doble
    juniors = await client.get("/api/v1/supervision/juniors", headers=hs)
    assert juniors.status_code == 200, juniors.text
    junior_id = juniors.json()[0]["cuenta_junior_id"]
    antes_senior = Decimal((await client.get("/api/v1/accounts/me", headers=hs)).json()["account"]["saldo"])
    antes_junior = Decimal((await client.get("/api/v1/accounts/me", headers=hj)).json()["account"]["saldo"])
    monto = Decimal("100000.00")
    budget = await client.post(
        "/api/v1/transfers/budget",
        headers=hs,
        json={"cuenta_junior_id": junior_id, "monto": str(monto), "descripcion": "Mes escolar"},
    )
    assert budget.status_code == 201, budget.text
    assert budget.json()["tipo"] == "ASIGNACION_PRESUPUESTO"
    despues_senior = Decimal((await client.get("/api/v1/accounts/me", headers=hs)).json()["account"]["saldo"])
    despues_junior = Decimal((await client.get("/api/v1/accounts/me", headers=hj)).json()["account"]["saldo"])
    assert antes_senior - despues_senior == monto
    assert despues_junior - antes_junior == monto
    historial_junior = (await client.get("/api/v1/accounts/me", headers=hj)).json()["movimientos"]
    assert any(item["tipo"] == "ASIGNACION_PRESUPUESTO" for item in historial_junior)
    assert all(item["es_transferencia_global"] is False for item in historial_junior)

    # HU-07 gasto impulsivo
    blocked = await client.post(
        "/api/v1/transactions/spend",
        headers=hj,
        json={"monto": "45000", "categoria": "COMIDA", "comercio": "Tienda"},
    )
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "GASTO_IMPULSIVO"
    forced = await client.post(
        "/api/v1/transactions/spend",
        headers=hj,
        json={
            "monto": "45000",
            "categoria": "COMIDA",
            "comercio": "Tienda",
            "forzar_confirmacion": True,
        },
    )
    assert forced.status_code == 201, forced.text
    saldo_tras_compra = Decimal((await client.get("/api/v1/accounts/me", headers=hj)).json()["account"]["saldo"])

    # HU-06 meta que congela saldo
    from datetime import date, timedelta

    goal = await client.post(
        "/api/v1/goals",
        headers=hj,
        json={
            "nombre": "Bici",
            "monto_objetivo": "80000",
            "fecha_limite": (date.today() + timedelta(days=40)).isoformat(),
        },
    )
    assert goal.status_code == 201, goal.text
    deposit = await client.post(
        f"/api/v1/goals/{goal.json()['id']}/deposit",
        headers=hj,
        json={"monto": "10000"},
    )
    assert deposit.status_code == 200, deposit.text
    assert Decimal(deposit.json()["monto_actual"]) == Decimal("10000.00")
    saldo_tras_meta = Decimal((await client.get("/api/v1/accounts/me", headers=hj)).json()["account"]["saldo"])
    assert saldo_tras_compra - saldo_tras_meta == Decimal("10000.00")

    # HU-05 BeHu Mini por rol
    mini_junior = await client.post("/api/v1/ai/consult", headers=hj, json={"pregunta": "hormiga"})
    mini_senior = await client.post("/api/v1/ai/consult", headers=hs, json={"pregunta": "excedente"})
    assert mini_junior.status_code == 200, mini_junior.text
    assert mini_senior.status_code == 200, mini_senior.text
    assert mini_junior.json()["rol"] == "JUNIOR"
    assert mini_senior.json()["rol"] == "SENIOR"
    assert "CDT" in " ".join(mini_senior.json()["recomendaciones"])
    history = await client.get("/api/v1/ai/history", headers=hj)
    assert history.status_code == 200 and history.json()

    # HU-08 / HU-09 score y quiz
    antes = (await client.get("/api/v1/scoring/me", headers=hj)).json()
    modules = await client.get("/api/v1/education/modules", headers=hj)
    assert modules.status_code == 200 and len(modules.json()) == 5
    modulo = modules.json()[0]
    malo = await client.post(
        f"/api/v1/education/modules/{modulo['id']}/complete",
        headers=hj,
        json={"respuesta": "0"},
    )
    assert malo.status_code == 400
    bueno = await client.post(
        f"/api/v1/education/modules/{modulo['id']}/complete",
        headers=hj,
        json={"respuesta": "1"},
    )
    assert bueno.status_code == 200, bueno.text
    assert bueno.json()["modulo"]["completado"] is True
    despues = (await client.get("/api/v1/scoring/me", headers=hj)).json()
    assert despues["puntaje"] == antes["puntaje"] + 8
    assert 0 <= despues["puntaje"] <= 100
    assert despues["nivel"]
