from fastapi import BackgroundTasks

from app.schemas.auth import CurrentUser
from app.services.blog_service import (
    delete_blog_source,
    list_blog_sources,
    scrape_and_index_blog
)
from app.services.document_service import list_documents


def _document_to_source(document: dict) -> dict:
    return {
        "id": document["id"],
        "type": "pdf",
        "filename": document["filename"],
        "title": document["filename"],
        "url": None,
        "status": document.get("indexing_status"),
        "created_at": document["created_at"],
        "chunks_count": document.get("chunks_count", 0)
    }


def _blog_to_source(blog_source: dict) -> dict:
    return {
        "id": blog_source["id"],
        "type": "blog",
        "filename": None,
        "title": blog_source["title"],
        "url": blog_source["url"],
        "status": blog_source.get("indexing_status"),
        "created_at": blog_source["created_at"],
        "chunks_count": blog_source.get("chunks_count", 0)
    }


async def list_knowledge_sources() -> list[dict]:
    documents = await list_documents()
    blog_sources = await list_blog_sources()

    sources = [
        *[_document_to_source(document) for document in documents],
        *[_blog_to_source(blog_source) for blog_source in blog_sources]
    ]

    return sorted(
        sources,
        key=lambda source: source["created_at"],
        reverse=True
    )


async def add_blog_source(
    url: str,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks
) -> dict:
    blog_source = await scrape_and_index_blog(
        url=url,
        current_user=current_user,
        background_tasks=background_tasks
    )

    return {
        "id": blog_source["id"],
        "type": "blog",
        "title": blog_source["title"],
        "url": blog_source["url"],
        "status": blog_source.get("indexing_status"),
        "created_at": blog_source["created_at"],
        "chunks_count": blog_source.get("chunks_count", 0)
    }


async def remove_blog_source(
    source_id: str,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks
) -> dict:
    return await delete_blog_source(
        blog_source_id=source_id,
        current_user=current_user,
        background_tasks=background_tasks
    )
