from datetime import datetime, timezone

from app.db.mongo import get_database


CHAT_SESSIONS_COLLECTION = "chat_sessions"


async def get_chat_session(
    session_id: str,
    user_id: str
) -> dict | None:
    db = get_database()

    return await db[CHAT_SESSIONS_COLLECTION].find_one({
        "session_id": session_id,
        "user_id": user_id
    })


async def get_or_create_chat_session(
    session_id: str,
    user_id: str
) -> dict:
    db = get_database()
    now = datetime.now(timezone.utc)

    await db[CHAT_SESSIONS_COLLECTION].update_one(
        {
            "session_id": session_id,
            "user_id": user_id
        },
        {
            "$setOnInsert": {
                "session_id": session_id,
                "user_id": user_id,
                "memory": {},
                "messages": [],
                "created_at": now
            },
            "$set": {
                "updated_at": now
            }
        },
        upsert=True
    )

    session = await get_chat_session(
        session_id=session_id,
        user_id=user_id
    )

    if session is None:
        raise RuntimeError("Failed to create chat session")

    return session


async def set_chat_session_memory(
    session_id: str,
    user_id: str,
    memory: dict
) -> None:
    db = get_database()
    now = datetime.now(timezone.utc)

    await db[CHAT_SESSIONS_COLLECTION].update_one(
        {
            "session_id": session_id,
            "user_id": user_id
        },
        {
            "$set": {
                **{
                    f"memory.{key}": value
                    for key, value in memory.items()
                },
                "updated_at": now
            }
        },
        upsert=True
    )


async def append_chat_session_message(
    session_id: str,
    user_id: str,
    role: str,
    content: str
) -> None:
    db = get_database()
    now = datetime.now(timezone.utc)

    await db[CHAT_SESSIONS_COLLECTION].update_one(
        {
            "session_id": session_id,
            "user_id": user_id
        },
        {
            "$push": {
                "messages": {
                    "role": role,
                    "content": content,
                    "created_at": now
                }
            },
            "$set": {
                "updated_at": now
            },
            "$setOnInsert": {
                "memory": {},
                "created_at": now
            }
        },
        upsert=True
    )


async def create_chat_session_indexes() -> None:
    db = get_database()

    await db[CHAT_SESSIONS_COLLECTION].create_index(
        [("session_id", 1), ("user_id", 1)],
        unique=True
    )
    await db[CHAT_SESSIONS_COLLECTION].create_index("updated_at")
