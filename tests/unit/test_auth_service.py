import asyncio

import pytest
from fastapi import HTTPException

from app.schemas.auth import LoginRequest
from app.services import auth_service


def test_login_user_rejects_unknown_user(monkeypatch):
    async def fake_get_user_by_username(username: str):
        return None

    monkeypatch.setattr(auth_service, "get_user_by_username", fake_get_user_by_username)

    async def run_test():
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login_user(LoginRequest(username="missing", password="secret"))

        assert exc_info.value.status_code == 401

    asyncio.run(run_test())


def test_login_user_returns_token_for_valid_credentials(monkeypatch):
    async def fake_get_user_by_username(username: str):
        return {
            "username": username,
            "password_hash": "hash",
            "role": "admin",
            "is_active": True,
        }

    monkeypatch.setattr(auth_service, "get_user_by_username", fake_get_user_by_username)
    monkeypatch.setattr(auth_service, "verify_password", lambda **kwargs: True)
    monkeypatch.setattr(auth_service, "create_access_token", lambda data: "token")

    token_response = asyncio.run(
        auth_service.login_user(LoginRequest(username="admin", password="admin123"))
    )

    assert token_response.access_token == "token"
    assert token_response.token_type == "bearer"
