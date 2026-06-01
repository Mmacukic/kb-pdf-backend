from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        message = value.strip()

        if not message:
            raise ValueError("Message is required")

        return message


class ChatSource(BaseModel):
    source_type: str | None = None
    source_id: str | None = None
    title: str | None = None
    url: str | None = None
    chunk_index: int | None = None
    version: int | None = None
    score: float | None = None


class ChatTraceStep(BaseModel):
    tool_name: str
    status: str
    message: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
    trace: list[ChatTraceStep]
    session_id: str | None = None
