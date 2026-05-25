from datetime import datetime

from pydantic import BaseModel

class DocumentVersionResponse(BaseModel):
    version: int
    filename: str
    storage_key: str
    size: int
    content_type: str
    uploaded_by: str
    uploaded_at: datetime
    indexing_status: str = "indexed"
    indexing_error: str | None = None
    indexed_at: datetime | None = None
    chunks_count: int = 0


class DocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    storage_key: str
    current_version: int
    uploaded_by: str
    created_at: datetime
    updated_at: datetime
    indexing_status: str = "indexed"
    indexing_error: str | None = None
    indexed_at: datetime | None = None
    chunks_count: int = 0


class DeleteDocumentResponse(BaseModel):
    message: str
    document_id: str
