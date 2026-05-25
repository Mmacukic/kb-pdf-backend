from fastapi import HTTPException, status

from app.core.security import create_access_token, verify_password
from app.repositories.user_repository import get_user_by_username
from app.schemas.auth import LoginRequest, TokenResponse


async def login_user(login_data: LoginRequest) -> TokenResponse:
    user = await get_user_by_username(login_data.username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    password_is_valid = verify_password(
        plain_password=login_data.password,
        password_hash=user["password_hash"]
    )

    if not password_is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        data={
            "sub": user["username"],
            "role": user["role"]
        }
    )

    return TokenResponse(
        access_token=access_token
    )