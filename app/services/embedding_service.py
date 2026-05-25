from openai import AsyncOpenAI

from app.core.config import settings


client = AsyncOpenAI(
    api_key=settings.openai_api_key
)


async def create_embedding(text: str) -> list[float]:
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text
    )

    return response.data[0].embedding


async def create_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts
    )

    return [
        item.embedding
        for item in response.data
    ]