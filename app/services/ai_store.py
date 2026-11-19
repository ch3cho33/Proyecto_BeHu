"""Persistencia de hábitos y recomendaciones. MongoDB con fallback JSON local."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

STORE_PATH = Path("data/behu_ai_store.json")
_mongo_ok: bool | None = None
_client: AsyncIOMotorClient | None = None


async def _mongo_available() -> bool:
    global _mongo_ok, _client
    if _mongo_ok is not None:
        return _mongo_ok
    try:
        _client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=400)
        await _client.admin.command("ping")
        _mongo_ok = True
    except Exception:
        _mongo_ok = False
        if _client is not None:
            _client.close()
            _client = None
    return _mongo_ok


def _read_json() -> dict:
    if not STORE_PATH.exists():
        return {"user_habits": [], "ai_recommendations": []}
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def _write_json(payload: dict) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def guardar_habito(documento: dict) -> str:
    documento = {**documento, "created_at": datetime.now(timezone.utc).isoformat()}
    if await _mongo_available() and _client is not None:
        result = await _client[settings.mongodb_db]["user_habits"].insert_one(documento)
        return "mongodb"
    data = _read_json()
    data["user_habits"].append({**documento, "_id": uuid4().hex})
    _write_json(data)
    return "json"


async def guardar_recomendacion(documento: dict) -> tuple[dict, str]:
    documento = {**documento, "created_at": datetime.now(timezone.utc).isoformat(), "_id": uuid4().hex}
    if await _mongo_available() and _client is not None:
        await _client[settings.mongodb_db]["ai_recommendations"].insert_one(documento)
        return documento, "mongodb"
    data = _read_json()
    data["ai_recommendations"].append(documento)
    _write_json(data)
    return documento, "json"


async def historial(usuario_id: str, limite: int = 20) -> tuple[list[dict], str]:
    if await _mongo_available() and _client is not None:
        cursor = (
            _client[settings.mongodb_db]["ai_recommendations"]
            .find({"usuario_id": usuario_id})
            .sort("created_at", -1)
            .limit(limite)
        )
        docs = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            docs.append(doc)
        return docs, "mongodb"
    data = _read_json()
    propios = [item for item in data["ai_recommendations"] if item.get("usuario_id") == usuario_id]
    propios.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return propios[:limite], "json"
