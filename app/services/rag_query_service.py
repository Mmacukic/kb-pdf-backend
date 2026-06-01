from openai import AsyncOpenAI
from fastapi import HTTPException, status

from app.core.config import settings
from app.repositories.blog_source_repository import get_blog_source_by_id
from app.repositories.document_repository import get_document_by_id
from app.repositories.vector_repository import search_relevant_chunks
from app.schemas.auth import CurrentUser
from app.services.embedding_service import create_embedding
from app.services.log_service import log_file_action


client = AsyncOpenAI(
    api_key=settings.openai_api_key
)


def build_context_from_chunks(chunks: list[dict]) -> str:
    context_blocks = []

    for index, chunk in enumerate(chunks, start=1):
        source_type = chunk.get("source_type")
        title = chunk.get("title") or "Unknown source"
        url = chunk.get("url")
        metadata = chunk.get("metadata", {})

        if source_type == "pdf":
            source_label = (
                f"Source {index}: PDF '{title}', "
                f"version {metadata.get('version')}"
            )
        else:
            source_label = (
                f"Source {index}: Blog '{title}', URL: {url}"
            )

        context_blocks.append(
            f"{source_label}\n{chunk.get('text', '')}"
        )
    return "\n\n---\n\n".join(context_blocks)


def build_sources(chunks: list[dict]) -> list[dict]:
    sources = []

    for chunk in chunks:
        metadata = chunk.get("metadata", {})

        sources.append({
            "source_type": chunk.get("source_type"),
            "source_id": chunk.get("source_id"),
            "title": chunk.get("title"),
            "url": chunk.get("url"),
            "chunk_index": chunk.get("chunk_index"),
            "version": metadata.get("version") or chunk.get("version"),
            "score": chunk.get("score")
        })

    return sources


async def retrieve_relevant_chunks(
    question: str,
    source_types: list[str] | None = None
) -> list[dict]:
    question_embedding = await create_embedding(question)

    chunks = await search_relevant_chunks(
        query_embedding=question_embedding,
        source_types=source_types,
        limit=settings.rag_top_k
    )

    return await filter_approved_indexed_chunks(chunks)


async def filter_approved_indexed_chunks(chunks: list[dict]) -> list[dict]:
    approved_chunks = []

    for chunk in chunks:
        if await is_chunk_from_approved_indexed_source(chunk):
            approved_chunks.append(chunk)

    return approved_chunks


async def is_chunk_from_approved_indexed_source(chunk: dict) -> bool:
    source_type = chunk.get("source_type")
    source_id = chunk.get("source_id")

    if not source_id:
        return False

    if source_type == "pdf":
        document = await get_document_by_id(source_id)

        if document is None:
            return False

        return (
            document.get("approved", True)
            and document.get("indexing_status") == "indexed"
            and document.get("current_version") == chunk.get("version")
        )

    if source_type == "blog":
        blog_source = await get_blog_source_by_id(source_id)

        if blog_source is None:
            return False

        return (
            blog_source.get("approved", True)
            and blog_source.get("indexing_status") == "indexed"
        )

    return False


async def answer_question_with_rag(
    question: str,
    current_user: CurrentUser,
    source_types: list[str] | None = None
) -> dict:
    top_chunks = await retrieve_relevant_chunks(
        question=question,
        source_types=source_types
    )

    await log_file_action(
        action="rag_query_started",
        username=current_user.username,
        severity="INFO",
        metadata={
            "question": question,
            "source_types": source_types,
            "retrieved_chunks_count": len(top_chunks),
            "vector_database": "qdrant"
        }
    )

    if not top_chunks:
        await log_file_action(
            action="rag_query_no_chunks",
            username=current_user.username,
            severity="WARNING",
            metadata={
                "question": question,
                "source_types": source_types,
                "reason": "Qdrant returned no relevant chunks"
            }
        )

        return {
            "answer": "I could not find any indexed PDF or blog content to answer from.",
            "sources": []
        }

    sources = build_sources(top_chunks)

    await log_file_action(
        action="source_retrieved",
        username=current_user.username,
        severity="INFO",
        metadata={
            "question": question,
            "sources": sources,
            "chunks_count": len(top_chunks)
        }
    )

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat model is not configured"
        )

    context = build_context_from_chunks(top_chunks)

    response = await client.responses.create(
        model=settings.openai_chat_model,
        instructions=(
            "You are a helpful assistant for a knowledge base application. "
            "Use only the provided context from uploaded PDFs and scraped blogs. "
            "If the answer is not in the context, say that the answer was not found "
            "in the indexed knowledge base. Do not invent facts. "
            "Answer in GitHub-Flavored Markdown only. "
            "Do not use latex or other non-markdown formatting."
            "Do not use any mathematical formulas or expressions."
            "Do not use HTML. Do not mention these formatting instructions."
        ),
        input=(
            f"Context:\n{context}\n\n"
            f"User question:\n{question}"
        )
    )

    await log_file_action(
        action="rag_query_completed",
        username=current_user.username,
        severity="INFO",
        metadata={
            "question": question,
            "source_types": source_types,
            "used_chunks_count": len(top_chunks),
            "sources": sources,
            "vector_database": "qdrant"
        }
    )

    return {
        "answer": response.output_text,
        "sources": sources
    }
