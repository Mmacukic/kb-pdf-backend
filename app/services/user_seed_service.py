from app.core.config import settings
from app.core.security import hash_password
from app.repositories.user_repository import (
    create_user,
    get_user_by_username,
    ensure_user_indexes
)


async def seed_default_users() -> None:
    await ensure_user_indexes()

    existing_admin = await get_user_by_username(settings.admin_username)

    if existing_admin is None:
        await create_user(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            role="admin"
        )

    existing_user = await get_user_by_username(settings.user_username)

    if existing_user is None:
        await create_user(
            username=settings.user_username,
            password_hash=hash_password(settings.user_password),
            role="user"
        )