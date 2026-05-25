from datetime import datetime

from pydantic import BaseModel, Field


class BlogScrapeRequest(BaseModel):
    url: str = Field(..., min_length=5)


class BlogSourceResponse(BaseModel):
    id: str
    url: str
    title: str
    scraped_by: str
    scraper: str
    chunks_count: int
    indexing_status: str = "indexed"
    indexing_error: str | None = None
    indexed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DeleteBlogSourceResponse(BaseModel):
    message: str
    blog_source_id: str
