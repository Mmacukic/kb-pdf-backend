from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.mongo import get_database
from app.repositories.vector_repository import qdrant_client
from app.services.storage_service import minio_client

router = APIRouter()


@router.get("")
async def health_check():
    return {
        "status": "ok"
    }


@router.get("/ready")
async def readiness_check():
    checks = {
        "mongo": "ok",
        "minio": "ok",
        "qdrant": "ok"
    }

    db = get_database()

    try:
        await db.command("ping")
    except Exception:
        checks["mongo"] = "error"

    try:
        await run_in_threadpool(
            minio_client.bucket_exists,
            settings.minio_bucket_name
        )
    except Exception:
        checks["minio"] = "error"

    try:
        await qdrant_client.collection_exists(
            collection_name=settings.qdrant_collection_name
        )
    except Exception:
        checks["qdrant"] = "error"

    status = "ok" if all(
        check == "ok"
        for check in checks.values()
    ) else "degraded"

    return JSONResponse(
        status_code=200 if status == "ok" else 503,
        content={
            "status": status,
            "checks": checks
        }
    )
