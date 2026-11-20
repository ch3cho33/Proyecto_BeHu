"""v4.0: perfil, categorías, notificaciones y BeHu Mini contextual."""

from decimal import Decimal

import httpx
import pytest

from scripts.seed_sandbox import seed


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
async def test_profile_categories_notifications_and_intent(client: httpx.AsyncClient):
    alta = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sara.v4@behu.test",
            "password": "BeHuSenior4!",
            "nombres": "Sara",
            "apellidos": "V4",
            "rol": "SENIOR",
            "moneda": "MXN",
            "ingreso_mensual_estimado": "25000",
        },
    )
    assert alta.status_code == 201, alta.text
    assert alta.json()["user"]["moneda_preferida"] == "MXN"
    senior = {"Authorization": f"Bearer {alta.json()['access_token']}"}
    perfil = await client.patch(
        "/api/v1/users/me",
        headers=senior,
        json={"nombres": "Sara", "apellidos": "Neobank", "moneda": "COP", "ingreso_mensual_estimado": "4000000"},
    )
    assert perfil.status_code == 200, perfil.text
    assert perfil.json()["moneda_preferida"] == "COP"
    assert Decimal(perfil.json()["ingreso_mensual_estimado"]) == Decimal("4000000")

    creada = await client.post("/api/v1/categories", headers=senior, json={"nombre": "Mascotas"})
    assert creada.status_code == 201, creada.text
    assert creada.json()["codigo"] == "MASCOTAS"
    catalogo = await client.get("/api/v1/categories", headers=senior)
    assert catalogo.status_code == 200
    codigos = {item["codigo"] for item in catalogo.json()}
    assert len([item for item in catalogo.json() if item["origen"] == "sistema"]) == 18
    assert "MASCOTAS" in codigos

    fondeo = await client.post("/api/v1/transactions/income", headers=senior, json={"monto": "500000", "descripcion": "Nomina"})
    assert fondeo.status_code == 201, fondeo.text
    junior = await client.post(
        "/api/v1/supervision/create-junior",
        headers=senior,
        json={
            "email": "leo.v4@behu.test",
            "password": "BeHuJunior4!",
            "nombres": "Leo",
            "apellidos": "V4",
            "initial_budget": "90000",
            "daily_limit": "200000",
            "weekly_limit": "400000",
            "monthly_limit": "800000",
        },
    )
    assert junior.status_code == 201, junior.text
    hijo = await _login(client, "leo.v4@behu.test", "BeHuJunior4!")
    compra = await client.post(
        "/api/v1/transactions",
        headers=hijo,
        json={"tipo": "GASTO", "monto": "4100", "categoria": "OCIO", "notas": "recarga juego", "bucket": "DESEOS"},
    )
    assert compra.status_code == 201, compra.text

    campana = await client.get("/api/v1/notifications", headers=senior)
    assert campana.status_code == 200, campana.text
    aviso = next(item for item in campana.json() if item["tipo"] == "GASTO_NO_PERTINENTE")
    assert aviso["leida"] is False
    assert aviso["severity"] == "high"
    leida = await client.patch(f"/api/v1/notifications/{aviso['id']}/read", headers=senior)
    assert leida.status_code == 200
    assert leida.json()["leida"] is True

    gasto = await client.post("/api/v1/ai/consult", headers=hijo, json={"pregunta": "¿Cuánto puedo gastar hoy?"})
    texto_gasto = " ".join(gasto.json()["recomendaciones"])
    assert "capacidad diaria" in texto_gasto
    assert "COP" in texto_gasto
    assert gasto.json()["recomendaciones"][0].startswith("Hola. Tu saldo disponible es")

    inversion = await client.post("/api/v1/ai/consult", headers=senior, json={"pregunta": "¿Puedo invertir en un CDT?"})
    texto_inv = " ".join(inversion.json()["recomendaciones"]).lower()
    assert "puedes invertir" in texto_inv
    assert "fondo de emergencia" in texto_inv
    assert "12" in texto_inv

    abierto = await client.post("/api/v1/ai/consult", headers=senior, json={"pregunta": "como va mi plata"})
    texto_abierto = " ".join(abierto.json()["recomendaciones"]).lower()
    assert "diagnóstico ejecutivo" in texto_abierto
    assert "cop" in texto_abierto
