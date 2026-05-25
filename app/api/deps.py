from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.repositories.user_repository import get_user_by_username
from app.schemas.auth import CurrentUser
from app.services.log_service import log_file_action

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    return await get_current_user_from_token(credentials.credentials)


async def get_current_user_from_token(token: str) -> CurrentUser:
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    username = payload.get("sub")

    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = await get_user_by_username(username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists"
        )

    if not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    if user.get("role") not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user role"
        )


    return CurrentUser(
        username=user["username"],
        role=user["role"]
    )


async def require_admin(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    if current_user.role != "admin":
        await log_file_action(
            action="admin_access_denied",
            username=current_user.username,
            severity="WARNING",
            metadata={
                "reason": "Admin access required",
                "user_role": current_user.role,
                "path": request.url.path,
                "method": request.method
            }
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user
