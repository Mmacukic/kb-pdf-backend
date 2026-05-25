from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams
)

from app.core.config import settings


qdrant_client = AsyncQdrantClient(
    url=settings.qdrant_url
)


async def ensure_vector_collection_exists() -> None:
    collection_exists = await qdrant_client.collection_exists(
        collection_name=settings.qdrant_collection_name
    )

    if collection_exists:
        return

    await qdrant_client.create_collection(
        collection_name=settings.qdrant_collection_name,
        vectors_config=VectorParams(
            size=settings.qdrant_vector_size,
            distance=Distance.COSINE
        )
    )


def build_source_filter(
    source_type: str,
    source_id: str | None = None,
    version: int | None = None
) -> Filter:
    conditions = [
        FieldCondition(
            key="source_type",
            match=MatchValue(value=source_type)
        )
    ]

    if source_id is not None:
        conditions.append(
            FieldCondition(
                key="source_id",
                match=MatchValue(value=source_id)
            )
        )

    if version is not None:
        conditions.append(
            FieldCondition(
                key="version",
                match=MatchValue(value=version)
            )
        )

    return Filter(
        must=conditions
    )


def build_source_types_filter(
    source_types: list[str] | None
) -> Filter | None:
    if not source_types:
        return None

    should_conditions = [
        FieldCondition(
            key="source_type",
            match=MatchValue(value=source_type)
        )
        for source_type in source_types
    ]

    return Filter(
        should=should_conditions
    )


async def upsert_chunks_to_vector_db(
    chunks: list[dict]
) -> None:
    if not chunks:
        return

    points = []

    for chunk in chunks:
        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=chunk["embedding"],
                payload={
                    "source_type": chunk["source_type"],
                    "source_id": chunk["source_id"],
                    "title": chunk.get("title"),
                    "url": chunk.get("url"),
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "approved": chunk.get("approved", True),
                    "version": chunk.get("version"),
                    "metadata": chunk.get("metadata", {})
                }
            )
        )

    await qdrant_client.upsert(
        collection_name=settings.qdrant_collection_name,
        points=points
    )


async def delete_chunks_by_source(
    source_type: str,
    source_id: str,
    version: int | None = None
) -> None:
    await qdrant_client.delete(
        collection_name=settings.qdrant_collection_name,
        points_selector=FilterSelector(
            filter=build_source_filter(
                source_type=source_type,
                source_id=source_id,
                version=version
            )
        )
    )


async def search_relevant_chunks(
    query_embedding: list[float],
    source_types: list[str] | None = None,
    limit: int = 5
) -> list[dict]:
    query_filter = build_source_types_filter(source_types)

    search_result = await qdrant_client.query_points(
        collection_name=settings.qdrant_collection_name,
        query=query_embedding,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False
    )

    chunks = []

    for point in search_result.points:
        payload = point.payload or {}

        chunks.append({
            "source_type": payload.get("source_type"),
            "source_id": payload.get("source_id"),
            "title": payload.get("title"),
            "url": payload.get("url"),
            "chunk_index": payload.get("chunk_index"),
            "text": payload.get("text"),
            "approved": payload.get("approved", True),
            "version": payload.get("version"),
            "metadata": payload.get("metadata", {}),
            "score": point.score
        })

    return chunks


async def count_chunks_by_source(
    source_type: str,
    source_id: str
) -> int:
    result = await qdrant_client.count(
        collection_name=settings.qdrant_collection_name,
        count_filter=build_source_filter(
            source_type=source_type,
            source_id=source_id
        ),
        exact=True
    )

    return result.count
