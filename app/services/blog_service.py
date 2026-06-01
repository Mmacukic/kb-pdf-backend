from fastapi import BackgroundTasks, HTTPException, status

from app.repositories.blog_source_repository import (
    create_blog_source,
    get_blog_source_by_id,
    list_active_blog_sources,
    mark_blog_source_as_deleted,
    update_blog_source_indexing_status,
    update_blog_source_scrape_result
)
from app.repositories.vector_repository import delete_chunks_by_source
from app.schemas.auth import CurrentUser
from app.services.blog_scraper_service import scrape_blog_page
from app.services.log_service import log_file_action
from app.services.rag_indexing_service import index_blog_for_rag


async def scrape_and_index_blog(
    url: str,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks
) -> dict:
    blog_source = await create_blog_source(
        url=url,
        title=url,
        scraped_by=current_user.username,
        scraper="httpx-html",
        chunks_count=0
    )

    background_tasks.add_task(
        _scrape_and_index_blog_background,
        blog_source_id=blog_source["id"],
        url=url,
        username=current_user.username
    )

    await log_file_action(
        action="blog_url_added",
        username=current_user.username,
        severity="INFO",
        metadata={
            "blog_source_id": blog_source["id"],
            "url": url,
            "scraper": "httpx-html"
        }
    )

    return blog_source


async def list_blog_sources() -> list[dict]:
    return await list_active_blog_sources()


async def delete_blog_source(
    blog_source_id: str,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks
) -> dict:
    blog_source = await get_blog_source_by_id(blog_source_id)

    if blog_source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog source not found"
        )

    deleted = await mark_blog_source_as_deleted(
        source_id=blog_source_id,
        deleted_by=current_user.username
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog source not found or already deleted"
        )

    background_tasks.add_task(
        _delete_blog_vectors_background,
        blog_source_id=blog_source_id,
        username=current_user.username
    )

    await log_file_action(
        action="blog_url_deleted",
        username=current_user.username,
        severity="INFO",
        metadata={
            "blog_source_id": blog_source_id,
            "url": blog_source["url"],
            "title": blog_source["title"]
        }
    )

    return {
        "message": "Blog source deleted successfully",
        "blog_source_id": blog_source_id
    }


async def _scrape_and_index_blog_background(
    blog_source_id: str,
    url: str,
    username: str
) -> None:
    await update_blog_source_indexing_status(
        source_id=blog_source_id,
        status="processing"
    )

    try:
        scraped = await scrape_blog_page(url)

        chunks_count = await index_blog_for_rag(
            blog_source_id=blog_source_id,
            url=scraped["url"],
            title=scraped["title"],
            text=scraped["text"],
            username=username,
            scraper=scraped["scraper"]
        )

        if chunks_count is None:
            return

        await update_blog_source_scrape_result(
            source_id=blog_source_id,
            url=scraped["url"],
            title=scraped["title"],
            scraper=scraped["scraper"],
            status="indexed",
            chunks_count=chunks_count,
            extracted_text=scraped["text"],
            source_metadata=scraped.get("metadata", {})
        )

        await log_file_action(
            action="blog_url_processed",
            username=username,
            severity="INFO",
            metadata={
                "blog_source_id": blog_source_id,
                "url": scraped["url"],
                "title": scraped["title"],
                "chunks_count": chunks_count,
                "scraper": scraped["scraper"],
                "metadata": scraped.get("metadata", {})
            }
        )

    except Exception as exception:
        error = str(exception)

        await update_blog_source_indexing_status(
            source_id=blog_source_id,
            status="failed",
            error=error
        )

        await log_file_action(
            action="blog_url_failed",
            username=username,
            severity="ERROR",
            metadata={
                "blog_source_id": blog_source_id,
                "url": url,
                "error": error
            }
        )


async def _delete_blog_vectors_background(
    blog_source_id: str,
    username: str
) -> None:
    try:
        await delete_chunks_by_source(
            source_type="blog",
            source_id=blog_source_id
        )
    except Exception as exception:
        await log_file_action(
            action="blog_delete_vectors_failed",
            username=username,
            severity="ERROR",
            metadata={
                "blog_source_id": blog_source_id,
                "error": str(exception)
            }
        )
