"""v2.0: consentimiento familiar, saldo congelado, hormiga y BeHu Mini."""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from scripts.seed_sandbox import SENIOR_EMAIL, SENIOR_PASSWORD, seed


@pytest.fixture
async def client():
    await seed()
    transport = httpx.ASGITransport(app=__import__("app.main", fromlist=["app"]).app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _login(client: httpx.AsyncClient, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.asyncio
async def test_invitation_consent_freeze_and_mini(client: httpx.AsyncClient):
    senior = await _login(client, SENIOR_EMAIL, SENIOR_PASSWORD)
    otro = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "otro.senior@behu.test",
            "password": "BeHuSenior2!",
            "nombres": "Otro",
            "apellidos": "Senior",
            "rol": "SENIOR",
        },
    )
    assert otro.status_code == 201, otro.text
    huerfano = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "huerfano@behu.test",
            "password": "BeHuJunior2!",
            "nombres": "Hua",
            "apellidos": "Orfano",
            "rol": "JUNIOR",
            "moneda": "COP",
        },
    )
    assert huerfano.status_code == 201, huerfano.text

    senior_ajeno = await client.post(
        "/api/v1/supervision/invite",
        headers=senior,
        json={
            "email": "otro.senior@behu.test",
            "initial_budget": "10000",
            "daily_limit": "50000",
            "weekly_limit": "200000",
            "monthly_limit": "500000",
        },
    )
    assert senior_ajeno.status_code == 400, senior_ajeno.text
    assert "Senior independiente" in senior_ajeno.json()["detail"]

    ya_vinculado = await client.post(
        "/api/v1/supervision/invite",
        headers=senior,
        json={
            "email": "junior@behu.test",
            "initial_budget": "1000",
            "daily_limit": "1000",
            "weekly_limit": "1000",
            "monthly_limit": "1000",
        },
    )
    assert ya_vinculado.status_code == 409, ya_vinculado.text
    assert ya_vinculado.json()["detail"] == "Esta cuenta ya pertenece a otro núcleo familiar"

    invitacion = await client.post(
        "/api/v1/supervision/invite",
        headers=senior,
        json={
            "email": "huerfano@behu.test",
            "initial_budget": "20000",
            "daily_limit": "50000",
            "weekly_limit": "200000",
            "monthly_limit": "500000",
        },
    )
    assert invitacion.status_code == 201, invitacion.text
    assert invitacion.json()["estado"] == "PENDING"
    invitation_id = invitacion.json()["id"]

    junior = await _login(client, "huerfano@behu.test", "BeHuJunior2!")
    pendientes = await client.get("/api/v1/supervision/invitations", headers=junior)
    assert pendientes.status_code == 200
    assert pendientes.json()[0]["id"] == invitation_id
    assert Decimal((await client.get("/api/v1/accounts/me", headers=junior)).json()["account"]["saldo"]) == 0

    aceptada = await client.post(
        f"/api/v1/supervision/invitations/{invitation_id}/respond",
        headers=junior,
        json={"accept": True},
    )
    assert aceptada.status_code == 200, aceptada.text
    assert aceptada.json()["estado"] == "ACCEPTED"
    assert Decimal((await client.get("/api/v1/accounts/me", headers=junior)).json()["account"]["saldo"]) == Decimal(
        "20000.00"
    )

    otro_headers = {"Authorization": f"Bearer {otro.json()['access_token']}"}
    conflicto = await client.post(
        "/api/v1/supervision/invite",
        headers=otro_headers,
        json={
            "email": "huerfano@behu.test",
            "initial_budget": "1000",
            "daily_limit": "1000",
            "weekly_limit": "1000",
            "monthly_limit": "1000",
        },
    )
    assert conflicto.status_code == 409

    meta = await client.post(
        "/api/v1/goals",
        headers=junior,
        json={
            "nombre": "Viaje",
            "monto_objetivo": "15000",
            "fecha_limite": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert meta.status_code == 201, meta.text
    abono = await client.post(
        f"/api/v1/goals/{meta.json()['id']}/deposit",
        headers=junior,
        json={"monto": "4000"},
    )
    assert abono.status_code == 200, abono.text
    cuenta = (await client.get("/api/v1/accounts/me", headers=junior)).json()["account"]
    assert Decimal(cuenta["saldo_congelado"]) == Decimal("4000.00")
    assert Decimal(cuenta["saldo"]) == Decimal("16000.00")

    for _ in range(3):
        compra = await client.post(
            "/api/v1/transactions/spend",
            headers=junior,
            json={"monto": "1500", "categoria": "COMIDA", "comercio": "Snack"},
        )
        assert compra.status_code == 201, compra.text

    alertas = await client.get("/api/v1/ai/parental-alerts", headers=senior)
    assert alertas.status_code == 200, alertas.text
    assert any(item["tipo"] == "GASTO_HORMIGA" and "Hua" in item["junior_nombre"] for item in alertas.json())

    mini_senior = await client.post(
        "/api/v1/ai/consult",
        headers=senior,
        json={"pregunta": "fondo de emergencia"},
    )
    texto_senior = " ".join(mini_senior.json()["recomendaciones"]).lower()
    assert mini_senior.status_code == 200
    assert "emergencia" in texto_senior
    assert "50/30/20" in texto_senior

    mini_junior = await client.post(
        "/api/v1/ai/consult",
        headers=junior,
        json={"pregunta": "como subo el score"},
    )
    texto_junior = " ".join(mini_junior.json()["recomendaciones"]).lower()
    assert "meta" in texto_junior
    assert "hormiga" in texto_junior

    ingreso = await client.post(
        "/api/v1/transactions/income",
        headers=senior,
        json={"monto": "300000", "descripcion": "Nomina sandbox"},
    )
    assert ingreso.status_code == 201, ingreso.text
    regla = await client.get("/api/v1/budgets/50-30-20", headers=senior)
    assert regla.status_code == 200, regla.text
    assert Decimal(regla.json()["ingresos"]) >= Decimal("300000")

    enviadas = await client.get("/api/v1/supervision/invitations/sent", headers=senior)
    assert enviadas.status_code == 200

    cuenta_junior = next(
        item["cuenta_junior_id"]
        for item in (await client.get("/api/v1/supervision/juniors", headers=senior)).json()
        if item["email"] == "huerfano@behu.test"
    )
    limites = await client.patch(
        f"/api/v1/supervision/juniors/{cuenta_junior}/limits",
        headers=senior,
        json={"daily_limit": "12000", "weekly_limit": "40000", "monthly_limit": "90000"},
    )
    assert limites.status_code == 200, limites.text
    propio = (await client.get("/api/v1/accounts/me", headers=junior)).json()["account"]
    assert Decimal(propio["limite_gasto_diario"]) == Decimal("12000")
