import json

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://0.0.0.0:5173",
    "http://[::1]:5173"
]
DEFAULT_CORS_ORIGIN_REGEX = (
    r"^https?://(localhost|127(?:\.\d{1,3}){3}|0\.0\.0\.0|\[::1\])(:\d+)?$"
)


class Settings(BaseSettings):
    app_name: str
    environment: str
    service_name: str = "kb-pdf-backend"
    cors_origins: str = ",".join(DEFAULT_CORS_ORIGINS)
    cors_origin_regex: str | None = DEFAULT_CORS_ORIGIN_REGEX

    mongo_uri: str
    mongo_db: str

    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int

    admin_username: str
    admin_password: str

    user_username: str
    user_password: str


    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket_name: str
    minio_secure: bool = False

    openai_api_key: str
    openai_chat_model: str = "gpt-5.2"
    openai_embedding_model: str = "text-embedding-3-small"

    rag_top_k: int = 5
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 200

    qdrant_url: str
    qdrant_collection_name: str = "knowledge_chunks"
    qdrant_vector_size: int = 1536

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def allowed_cors_origins(self) -> list[str]:
        value = self.cors_origins.strip()

        if value.startswith("["):
            try:
                origins = json.loads(value)
            except json.JSONDecodeError:
                origins = []

            if isinstance(origins, list):
                return [
                    str(origin).strip()
                    for origin in origins
                    if str(origin).strip()
                ]

        return [
            origin.strip()
            for origin in value.split(",")
            if origin.strip()
        ]


settings = Settings()
