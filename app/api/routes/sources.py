from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.deps import get_current_user, require_admin
from app.schemas.auth import CurrentUser
from app.schemas.blog import DeleteBlogSourceResponse
from app.schemas.source import (
    BlogKnowledgeSourceResponse,
    BlogSourceCreateRequest,
    KnowledgeSourceResponse
)
from app.services.source_service import (
    add_blog_source,
    list_knowledge_sources,
    remove_blog_source
)

router = APIRouter()


@router.get("", response_model=list[KnowledgeSourceResponse])
async def get_sources(
    current_user: CurrentUser = Depends(get_current_user)
):
    return await list_knowledge_sources(current_user=current_user)


@router.post(
    "/blog",
    response_model=BlogKnowledgeSourceResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_blog_source(
    request: BlogSourceCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_admin)
):
    return await add_blog_source(
        url=request.url,
        current_user=current_user,
        background_tasks=background_tasks
    )


@router.delete(
    "/blog/{source_id}",
    response_model=DeleteBlogSourceResponse
)
async def delete_blog_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_admin)
):
    return await remove_blog_source(
        source_id=source_id,
        current_user=current_user,
        background_tasks=background_tasks
    )
