from datetime import datetime

from pydantic import BaseModel, Field


class BlogSourceCreateRequest(BaseModel):
    url: str = Field(..., min_length=5)


class KnowledgeSourceResponse(BaseModel):
    id: str
    type: str
    title: str
    created_at: datetime
    status: str | None = None
    filename: str | None = None
    url: str | None = None
    chunks_count: int = 0


class BlogKnowledgeSourceResponse(BaseModel):
    id: str
    type: str = "blog"
    title: str
    url: str
    status: str
    created_at: datetime
    chunks_count: int = 0
