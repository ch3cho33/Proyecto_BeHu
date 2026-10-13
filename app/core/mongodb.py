"""Cliente Motor para colecciones de hábitos e IA."""

from collections.abc import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


def get_mongo_db() -> AsyncIOMotorDatabase:
    return get_mongo_client()[settings.mongodb_db]


async def get_mongo() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    yield get_mongo_db()


async def close_mongo_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
