from app.schemas.auth import CurrentUser
from app.services.intent_service import (
    Intent,
    classify_message,
)
from app.services.log_service import log_file_action
from app.services.memory_service import (
    get_session_memory,
    resolve_session_id,
    save_chat_exchange,
    save_user_name,
)
from app.services.rag_query_service import answer_question_with_rag


async def chat_with_agent(
    message: str,
    session_id: str | None,
    current_user: CurrentUser
) -> dict:
    resolved_session_id = resolve_session_id(session_id)
    user_id = current_user.username

    await log_file_action(
        action="agent_chat_start",
        username=current_user.username,
        severity="INFO",
        metadata={
            "message": message,
            "session_id": resolved_session_id
        }
    )

    intent_result = classify_message(message)
    intent = intent_result.intent

    if intent == Intent.MEMORY_UPDATE:
        user_name = intent_result.user_name

        await save_user_name(
            session_id=resolved_session_id,
            user_id=user_id,
            user_name=user_name
        )
        answer = f"Bok {user_name}! Kako ti mogu pomoći?"
        trace_message = f"Saved user_name={user_name}"

        await save_chat_exchange(
            session_id=resolved_session_id,
            user_id=user_id,
            user_message=message,
            assistant_message=answer
        )
        await _log_agent_chat_complete(
            message=message,
            session_id=resolved_session_id,
            current_user=current_user,
            intent=intent,
            used_tools=[],
            sources_count=0
        )

        return build_non_rag_response(
            answer=answer,
            session_id=resolved_session_id,
            intent=intent,
            trace_message=trace_message
        )

    if intent == Intent.MEMORY_QUERY:
        memory = await get_session_memory(
            session_id=resolved_session_id,
            user_id=user_id
        )
        user_name = memory.get("user_name")
        answer = (
            f"Zoveš se {user_name}."
            if user_name
            else "Još mi nisi rekao kako se zoveš."
        )

        await save_chat_exchange(
            session_id=resolved_session_id,
            user_id=user_id,
            user_message=message,
            assistant_message=answer
        )
        await _log_agent_chat_complete(
            message=message,
            session_id=resolved_session_id,
            current_user=current_user,
            intent=intent,
            used_tools=[],
            sources_count=0
        )

        return build_non_rag_response(
            answer=answer,
            session_id=resolved_session_id,
            intent=intent,
            trace_message=(
                "Read user_name from session memory"
                if user_name
                else "No user_name in session memory"
            )
        )

    if intent == Intent.SMALL_TALK:
        answer = "Bok! Kako ti mogu pomoći?"

        await save_chat_exchange(
            session_id=resolved_session_id,
            user_id=user_id,
            user_message=message,
            assistant_message=answer
        )
        await _log_agent_chat_complete(
            message=message,
            session_id=resolved_session_id,
            current_user=current_user,
            intent=intent,
            used_tools=[],
            sources_count=0
        )

        return build_non_rag_response(
            answer=answer,
            session_id=resolved_session_id,
            intent=intent,
            trace_message="Simple greeting handled without RAG"
        )

    rag_response = await answer_question_with_rag(
        question=message,
        current_user=current_user
    )
    sources = rag_response["sources"]

    await _log_agent_chat_complete(
        message=message,
        session_id=resolved_session_id,
        current_user=current_user,
        intent=intent,
        used_tools=["retrieve_approved_indexed_sources"],
        sources_count=len(sources)
    )

    await save_chat_exchange(
        session_id=resolved_session_id,
        user_id=user_id,
        user_message=message,
        assistant_message=rag_response["answer"]
    )

    return {
        "answer": rag_response["answer"],
        "sources": sources,
        "trace": [
            {
                "tool_name": "intent_router",
                "status": "success",
                "message": f"Intent detected: {intent.value}"
            },
            {
                "tool_name": "retrieve_approved_indexed_sources",
                "status": "success" if sources else "empty",
                "message": None if sources else "No approved indexed sources found"
            }
        ],
        "session_id": resolved_session_id
    }


async def _log_agent_chat_complete(
    message: str,
    session_id: str,
    current_user: CurrentUser,
    intent: Intent,
    used_tools: list[str],
    sources_count: int
) -> None:
    await log_file_action(
        action="agent_chat_complete",
        username=current_user.username,
        severity="INFO",
        metadata={
            "message": message,
            "session_id": session_id,
            "intent": intent.value,
            "used_tools": used_tools,
            "sources_count": sources_count
        }
    )


def build_non_rag_response(
    answer: str,
    session_id: str,
    intent: Intent,
    trace_message: str
) -> dict:
    return {
        "answer": answer,
        "sources": [],
        "trace": [
            {
                "tool_name": "intent_router",
                "status": "success",
                "message": f"Intent detected: {intent.value}"
            },
            {
                "tool_name": "session_memory",
                "status": "success",
                "message": trace_message
            },
            {
                "tool_name": "retrieve_approved_indexed_sources",
                "status": "skipped",
                "message": "RAG skipped"
            }
        ],
        "session_id": session_id
    }
