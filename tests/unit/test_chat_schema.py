import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest


def test_chat_request_rejects_blank_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="   ")


def test_chat_request_strips_message():
    request = ChatRequest(message="  hello  ")

    assert request.message == "hello"
