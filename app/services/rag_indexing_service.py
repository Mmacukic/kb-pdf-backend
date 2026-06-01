from app.repositories.vector_repository import (
    delete_chunks_by_source,
    upsert_chunks_to_vector_db
)
from app.repositories.document_repository import get_document_by_id
from app.repositories.blog_source_repository import get_blog_source_by_id
from app.services.chunking_service import chunk_text
from app.services.embedding_service import create_embeddings
from app.services.log_service import log_file_action
from app.services.pdf_text_service import extract_text_from_pdf_bytes


async def index_pdf_for_rag(
    document_id: str,
    version: int,
    filename: str,
    file_bytes: bytes,
    username: str
) -> int | None:
    text = extract_text_from_pdf_bytes(file_bytes)

    chunks = chunk_text(text)

    embeddings = await create_embeddings(chunks)

    current_document = await get_document_by_id(document_id)

    if (
        current_document is None
        or current_document.get("current_version") != version
        or current_document.get("is_deleted")
    ):
        return None

    vector_chunks = []

    for index, chunk in enumerate(chunks):
        vector_chunks.append({
            "source_type": "pdf",
            "source_id": document_id,
            "title": filename,
            "url": None,
            "chunk_index": index,
            "text": chunk,
            "embedding": embeddings[index],
            "approved": True,
            "version": version,
            "metadata": {
                "document_id": document_id,
                "filename": filename,
                "version": version,
                "is_current_version": True
            }
        })

    await delete_chunks_by_source(
        source_type="pdf",
        source_id=document_id
    )

    await upsert_chunks_to_vector_db(vector_chunks)

    await log_file_action(
        action="rag_pdf_index",
        username=username,
        document_id=document_id,
        filename=filename,
        severity="INFO",
        metadata={
            "source_type": "pdf",
            "version": version,
            "chunks_count": len(vector_chunks),
            "vector_database": "qdrant"
        }
    )

    return len(vector_chunks)


async def index_blog_for_rag(
    blog_source_id: str,
    url: str,
    title: str,
    text: str,
    username: str,
    scraper: str
) -> int | None:
    chunks = chunk_text(text)

    embeddings = await create_embeddings(chunks)

    blog_source = await get_blog_source_by_id(blog_source_id)

    if blog_source is None:
        return None

    vector_chunks = []

    for index, chunk in enumerate(chunks):
        vector_chunks.append({
            "source_type": "blog",
            "source_id": blog_source_id,
            "title": title,
            "url": url,
            "chunk_index": index,
            "text": chunk,
            "embedding": embeddings[index],
            "approved": True,
            "version": None,
            "metadata": {
                "blog_source_id": blog_source_id,
                "scraper": scraper
            }
        })

    await delete_chunks_by_source(
        source_type="blog",
        source_id=blog_source_id
    )

    await upsert_chunks_to_vector_db(vector_chunks)

    await log_file_action(
        action="rag_blog_index",
        username=username,
        severity="INFO",
        metadata={
            "source_type": "blog",
            "blog_source_id": blog_source_id,
            "url": url,
            "title": title,
            "scraper": scraper,
            "chunks_count": len(vector_chunks),
            "vector_database": "qdrant"
        }
    )

    return len(vector_chunks)
