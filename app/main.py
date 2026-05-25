from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, auth, documents, blogs, chat, sources, websocket_chat
from app.core.config import settings
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.services.storage_service import ensure_bucket_exists
from app.services.user_seed_service import seed_default_users
from app.repositories.blog_source_repository import create_blog_source_indexes
from app.repositories.chat_session_repository import create_chat_session_indexes
from app.repositories.document_repository import create_document_indexes
from app.repositories.vector_repository import  ensure_vector_collection_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await seed_default_users()
    await ensure_vector_collection_exists()
    await create_document_indexes()
    await create_blog_source_indexes()
    await create_chat_session_indexes()
    ensure_bucket_exists()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)

app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"]
)


app.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"]
)

app.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"]
)

app.include_router(
    blogs.router,
    prefix="/blogs",
    tags=["Blogs"]
)

app.include_router(
    sources.router,
    prefix="/sources",
    tags=["Sources"]
)

app.include_router(
    websocket_chat.router,
    tags=["WebSocket"]
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
