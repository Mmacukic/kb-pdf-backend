from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


class MongoDB:
    client: AsyncIOMotorClient | None = None
    database = None


mongo = MongoDB()


async def connect_to_mongo():
    mongo.client = AsyncIOMotorClient(settings.mongo_uri)
    mongo.database = mongo.client[settings.mongo_db]

    # Test connection
    await mongo.client.admin.command("ping")


async def close_mongo_connection():
    if mongo.client:
        mongo.client.close()


def get_database():
    if mongo.database is None:
        raise RuntimeError("Database is not initialized")
    return mongo.database