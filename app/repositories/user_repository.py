from datetime import datetime, timezone

from app.db.mongo import get_database


USERS_COLLECTION = "users"


async def create_user(
    username: str,
    password_hash: str,
    role: str
) -> dict:
    db = get_database()

    user = {
        "username": username,
        "password_hash": password_hash,
        "role": role,
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }

    result = await db[USERS_COLLECTION].insert_one(user)

    user["_id"] = str(result.inserted_id)

    return user


async def get_user_by_username(username: str) -> dict | None:
    db = get_database()

    user = await db[USERS_COLLECTION].find_one({
        "username": username
    })

    return user


async def ensure_user_indexes() -> None:
    db = get_database()

    await db[USERS_COLLECTION].create_index(
        "username",
        unique=True
    )