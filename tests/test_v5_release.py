"""v5.0: contrato de BeHu Mini, pausa de patrón, cifrado y backup híbrido."""

from decimal import Decimal

import httpx
import pytest

from app.core.crypto import cifrar, descifrar
from scripts.seed_sandbox import seed


@pytest.fixture
async def client():
    await seed()
    transport = httpx.ASGITransport(app=__import__("app.main", fromlist=["app"]).app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


@pytest.mark.asyncio
async def test_mini_reply_pattern_and_backup(client: httpx.AsyncClient):
    token = cifrar(b"documento-kyc")
    assert descifrar(token) == b"documento-kyc"

    alta = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "junior.v5@behu.test",
            "password": "BeHuJunior5!",
            "nombres": "Nia",
            "apellidos": "Cinco",
            "rol": "JUNIOR",
            "moneda": "COP",
        },
    )
    assert alta.status_code == 201, alta.text
    headers = {"Authorization": f"Bearer {alta.json()['access_token']}"}
    fondeo = await client.post("/api/v1/transactions/income", headers=headers, json={"monto": "200000", "descripcion": "Mesada"})
    assert fondeo.status_code == 201, fondeo.text

    mini = await client.post("/api/v1/ai/consult", headers=headers, json={"message": "¿Cómo evito gastos innecesarios?"})
    assert mini.status_code == 200, mini.text
    cuerpo = mini.json()
    assert cuerpo["reply"] == cuerpo["response"]
    assert cuerpo["reply"]
    assert cuerpo["insights"]
    assert "COP" in cuerpo["reply"]

    for monto in ("3000", "3000"):
        compra = await client.post(
            "/api/v1/transactions",
            headers=headers,
            json={"tipo": "GASTO", "monto": monto, "categoria": "COMIDA", "notas": "Snack", "bucket": "DESEOS"},
        )
        assert compra.status_code == 201, compra.text
    pausa = await client.post(
        "/api/v1/transactions",
        headers=headers,
        json={"tipo": "GASTO", "monto": "3000", "categoria": "COMIDA", "notas": "Otro snack", "bucket": "DESEOS"},
    )
    assert pausa.status_code == 409, pausa.text
    assert pausa.json()["detail"]["code"] == "PATRON_ANOMALO"
    avisos = await client.get("/api/v1/notifications", headers=headers)
    assert any(item["tipo"] == "PATRON_ANOMALO" for item in avisos.json())

    sigue = await client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "tipo": "GASTO",
            "monto": "3000",
            "categoria": "COMIDA",
            "notas": "Sigue",
            "bucket": "DESEOS",
            "forzar_confirmacion": True,
        },
    )
    assert sigue.status_code == 201, sigue.text
    recibo = await client.get(f"/api/v1/transactions/{sigue.json()['id']}/receipt", headers=headers)
    assert recibo.status_code == 200
    assert all(linea["sello_hmac"] for linea in recibo.json()["asientos"])

    copia = await client.post("/api/v1/system/backup", headers=headers)
    assert copia.status_code == 200, copia.text
    assert len(copia.json()["sha256"]) == 64
    assert copia.json()["cifrado"] == "AES-256-GCM"
    assert Decimal(copia.json()["snapshot"]["cuenta"]["saldo"]) > 0
