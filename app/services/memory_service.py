from uuid import uuid4

from app.repositories.chat_session_repository import (
    append_chat_session_message,
    get_or_create_chat_session,
    set_chat_session_memory,
)


def resolve_session_id(session_id: str | None) -> str:
    if session_id and session_id.strip():
        return session_id.strip()

    return str(uuid4())


async def get_session_memory(
    session_id: str,
    user_id: str
) -> dict:
    session = await get_or_create_chat_session(
        session_id=session_id,
        user_id=user_id
    )

    return session.get("memory") or {}


async def save_user_name(
    session_id: str,
    user_id: str,
    user_name: str
) -> None:
    await set_chat_session_memory(
        session_id=session_id,
        user_id=user_id,
        memory={
            "user_name": user_name
        }
    )


async def save_chat_exchange(
    session_id: str,
    user_id: str,
    user_message: str,
    assistant_message: str
) -> None:
    await append_chat_session_message(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=user_message
    )
    await append_chat_session_message(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=assistant_message
    )
