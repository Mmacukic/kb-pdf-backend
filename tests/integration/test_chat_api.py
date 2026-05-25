from app.schemas.auth import CurrentUser
from starlette.websockets import WebSocketDisconnect


def test_http_chat_uses_authenticated_user_and_returns_sources(
    client,
    authenticate_as_user,
    monkeypatch,
):
    async def fake_chat_with_agent(message, session_id, current_user, background_tasks):
        assert current_user.username == "user"
        assert session_id is None
        return {
            "answer": f"answer to {message}",
            "sources": [
                {
                    "source_type": "pdf",
                    "source_id": "pdf-1",
                    "title": "handbook.pdf",
                    "url": None,
                    "chunk_index": 0,
                    "version": 1,
                    "score": 0.9,
                }
            ],
            "trace": [
                {
                    "tool_name": "retrieve_approved_indexed_sources",
                    "status": "success",
                    "message": None,
                }
            ],
            "session_id": "generated-session",
        }

    monkeypatch.setattr("app.api.routes.chat.chat_with_agent", fake_chat_with_agent)

    response = client.post("/chat", json={"message": "policy"})

    assert response.status_code == 200
    assert response.json()["answer"] == "answer to policy"
    assert response.json()["sources"][0]["source_id"] == "pdf-1"
    assert response.json()["session_id"] == "generated-session"


def test_websocket_chat_rejects_missing_token(client):
    try:
        with client.websocket_connect("/ws/chat"):
            raise AssertionError("connection should not be accepted")
    except WebSocketDisconnect as exception:
        assert exception.code == 1008


def test_websocket_chat_returns_answer_with_sources(client, monkeypatch):
    async def fake_get_current_user_from_token(token: str):
        assert token == "valid-token"
        return CurrentUser(username="user", role="user")

    async def fake_chat_with_agent(message, session_id, current_user, background_tasks):
        assert session_id == "session-1"
        return {
            "answer": f"grounded answer for {message}",
            "sources": [
                {
                    "source_type": "blog",
                    "source_id": "blog-1",
                    "title": "Article",
                    "url": "https://example.com/article",
                    "chunk_index": 0,
                    "version": None,
                    "score": 0.8,
                }
            ],
            "trace": [],
            "session_id": session_id,
        }

    async def noop_log_file_action(**kwargs):
        return None

    monkeypatch.setattr(
        "app.api.routes.websocket_chat.get_current_user_from_token",
        fake_get_current_user_from_token,
    )
    monkeypatch.setattr(
        "app.api.routes.websocket_chat.chat_with_agent",
        fake_chat_with_agent,
    )
    monkeypatch.setattr(
        "app.api.routes.websocket_chat.log_file_action",
        noop_log_file_action,
    )

    with client.websocket_connect("/ws/chat?token=valid-token") as websocket:
        websocket.send_json({
            "type": "message",
            "message": "what is indexed?",
            "session_id": "session-1",
        })
        response = websocket.receive_json()

    assert response == {
        "type": "answer",
        "message": "grounded answer for what is indexed?",
        "sources": [
            {
                "id": "blog-1",
                "type": "blog",
                "title": "Article",
                "filename": None,
                "url": "https://example.com/article",
            }
        ],
        "session_id": "session-1",
    }
