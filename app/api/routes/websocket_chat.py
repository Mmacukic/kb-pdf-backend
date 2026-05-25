from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.api.deps import get_current_user_from_token
from app.services.agent_service import chat_with_agent
from app.services.log_service import log_file_action

router = APIRouter()


def _format_ws_sources(sources: list[dict]) -> list[dict]:
    formatted_sources = []

    for source in sources:
        formatted_sources.append({
            "id": source.get("source_id"),
            "type": source.get("source_type"),
            "title": source.get("title"),
            "filename": source.get("title") if source.get("source_type") == "pdf" else None,
            "url": source.get("url")
        })

    return formatted_sources


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    try:
        current_user = await get_current_user_from_token(token)
    except HTTPException as exception:
        await websocket.close(code=1008, reason=str(exception.detail))
        return

    await websocket.accept()

    try:
        while True:
            payload = await websocket.receive_json()

            if payload.get("type") != "message":
                await websocket.send_json({
                    "type": "error",
                    "message": "Unsupported message type"
                })
                continue

            message = payload.get("message")
            session_id = payload.get("session_id")

            if not isinstance(message, str) or not message.strip():
                await websocket.send_json({
                    "type": "error",
                    "message": "Message is required"
                })
                continue

            await log_file_action(
                action="chat_message_sent",
                username=current_user.username,
                severity="INFO",
                metadata={
                    "session_id": session_id,
                    "message": message
                }
            )

            try:
                response = await chat_with_agent(
                    message=message,
                    session_id=session_id,
                    current_user=current_user,
                    background_tasks=BackgroundTasks()
                )
            except HTTPException as exception:
                await log_file_action(
                    action="chat_answer_failed",
                    username=current_user.username,
                    severity="ERROR",
                    metadata={
                        "session_id": session_id,
                        "error": exception.detail
                    }
                )
                await websocket.send_json({
                    "type": "error",
                    "message": str(exception.detail)
                })
                continue
            except Exception as exception:
                await log_file_action(
                    action="chat_answer_failed",
                    username=current_user.username,
                    severity="ERROR",
                    metadata={
                        "session_id": session_id,
                        "error": str(exception)
                    }
                )
                await websocket.send_json({
                    "type": "error",
                    "message": "Something went wrong"
                })
                continue

            sources = _format_ws_sources(response.get("sources", []))

            await log_file_action(
                action="chat_answer_generated",
                username=current_user.username,
                severity="INFO",
                metadata={
                    "session_id": response.get("session_id"),
                    "source_ids": [source["id"] for source in sources if source.get("id")]
                }
            )

            await websocket.send_json({
                "type": "answer",
                "message": response["answer"],
                "sources": sources,
                "session_id": response.get("session_id")
            })

    except WebSocketDisconnect:
        return
