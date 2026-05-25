from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import get_current_user, require_admin
from app.schemas.auth import CurrentUser
from app.schemas.blog import (
    BlogScrapeRequest,
    BlogSourceResponse,
    DeleteBlogSourceResponse
)
from app.services.blog_service import (
    delete_blog_source,
    list_blog_sources,
    scrape_and_index_blog
)

router = APIRouter()


@router.post(
    "/scrape",
    response_model=BlogSourceResponse
)
async def scrape_blog(
    request: BlogScrapeRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_admin)
):
    return await scrape_and_index_blog(
        url=request.url,
        current_user=current_user,
        background_tasks=background_tasks
    )


@router.get(
    "",
    response_model=list[BlogSourceResponse]
)
async def get_blog_sources(
    current_user: CurrentUser = Depends(get_current_user)
):
    return await list_blog_sources(
        current_user=current_user
    )


@router.delete(
    "/{blog_source_id}",
    response_model=DeleteBlogSourceResponse
)
async def delete_blog(
    blog_source_id: str,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_admin)
):
    return await delete_blog_source(
        blog_source_id=blog_source_id,
        current_user=current_user,
        background_tasks=background_tasks
    )
