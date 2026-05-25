from fastapi import APIRouter

from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import login_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    return await login_user(login_data)