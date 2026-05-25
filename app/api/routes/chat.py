from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import get_current_user
from app.schemas.auth import CurrentUser
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent_service import chat_with_agent

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user)
):
    return await chat_with_agent(
        message=request.message,
        session_id=request.session_id,
        current_user=current_user,
        background_tasks=background_tasks
    )
