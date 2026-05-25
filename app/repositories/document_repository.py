from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongo import get_database


DOCUMENTS_COLLECTION = "documents"

def serialize_document(document: dict) -> dict:
    document["id"] = str(document["_id"])
    document.pop("_id", None)
    return document


def to_object_id(document_id: str) -> ObjectId | None:
    try:
        return ObjectId(document_id)
    except Exception:
        return None


async def create_document_metadata(
    filename: str,
    content_type: str,
    size: int,
    storage_key: str,
    uploaded_by: str
) -> dict:
    db = get_database()

    now = datetime.now(timezone.utc)

    document = {
        "filename": filename,
        "content_type": content_type,
        "size": size,
        "storage_key": storage_key,
        "current_version": 1,
        "uploaded_by": uploaded_by,
        "created_at": now,
        "updated_at": now,
        "indexing_status": "pending",
        "indexing_error": None,
        "indexed_at": None,
        "chunks_count": 0,
        "approved": True,
        "is_deleted": False,
        "versions": [
            {
                "version": 1,
                "filename": filename,
                "content_type": content_type,
                "size": size,
                "storage_key": storage_key,
                "uploaded_by": uploaded_by,
                "uploaded_at": now,
                "indexing_status": "pending",
                "indexing_error": None,
                "indexed_at": None,
                "chunks_count": 0
            }
        ]
    }

    result = await db[DOCUMENTS_COLLECTION].insert_one(document)

    document["id"] = str(result.inserted_id)

    return document

async def list_active_documents() -> list[dict]:
    db = get_database()

    cursor = db[DOCUMENTS_COLLECTION].find(
        {
            "is_deleted": False
        }
    ).sort("created_at", -1)

    documents = []

    async for document in cursor:
        documents.append(serialize_document(document))

    return documents


async def get_document_by_id(document_id: str) -> dict | None:
    db = get_database()

    object_id = to_object_id(document_id)

    if object_id is None:
        return None

    document = await db[DOCUMENTS_COLLECTION].find_one(
        {
            "_id": object_id,
            "is_deleted": False
        }
    )

    if document is None:
        return None

    return serialize_document(document)


async def mark_document_as_deleted(
    document_id: str,
    deleted_by: str
) -> bool:
    db = get_database()

    object_id = to_object_id(document_id)

    if object_id is None:
        return False

    result = await db[DOCUMENTS_COLLECTION].update_one(
        {
            "_id": object_id,
            "is_deleted": False
        },
        {
            "$set": {
                "is_deleted": True,
                "deleted_by": deleted_by,
                "deleted_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "indexing_status": "deleted"
            }
        }
    )
    return result.modified_count == 1

async def add_document_version(
    document_id: str,
    version_data: dict,
    expected_current_version: int
) -> dict | None:
    db = get_database()

    object_id = to_object_id(document_id)

    if object_id is None:
        return None

    now = datetime.now(timezone.utc)

    result = await db[DOCUMENTS_COLLECTION].update_one(
        {
            "_id": object_id,
            "is_deleted": False,
            "current_version": expected_current_version
        },
        {
            "$set": {
                "filename": version_data["filename"],
                "content_type": version_data["content_type"],
                "size": version_data["size"],
                "storage_key": version_data["storage_key"],
                "current_version": version_data["version"],
                "updated_at": now,
                "indexing_status": "pending",
                "indexing_error": None,
                "indexed_at": None,
                "chunks_count": 0
            },
            "$push": {
                "versions": version_data
            }
        }
    )

    if result.modified_count != 1:
        return None

    return await get_document_by_id(document_id)


async def update_document_indexing_status(
    document_id: str,
    version: int,
    status: str,
    chunks_count: int | None = None,
    error: str | None = None
) -> bool:
    db = get_database()

    object_id = to_object_id(document_id)

    if object_id is None:
        return False

    now = datetime.now(timezone.utc)

    document_fields = {
        "indexing_status": status,
        "indexing_error": error,
        "updated_at": now
    }
    version_fields = {
        "versions.$[version].indexing_status": status,
        "versions.$[version].indexing_error": error
    }

    if chunks_count is not None:
        document_fields["chunks_count"] = chunks_count
        version_fields["versions.$[version].chunks_count"] = chunks_count

    if status == "indexed":
        document_fields["indexed_at"] = now
        version_fields["versions.$[version].indexed_at"] = now

    result = await db[DOCUMENTS_COLLECTION].update_one(
        {
            "_id": object_id,
            "is_deleted": False,
            "current_version": version
        },
        {
            "$set": {
                **document_fields,
                **version_fields
            }
        },
        array_filters=[
            {
                "version.version": version
            }
        ]
    )

    return result.modified_count == 1


async def create_document_indexes() -> None:
    db = get_database()

    await db[DOCUMENTS_COLLECTION].create_index("created_at")
    await db[DOCUMENTS_COLLECTION].create_index("is_deleted")
    await db[DOCUMENTS_COLLECTION].create_index("indexing_status")


async def get_document_versions(
    document_id: str
) -> list[dict] | None:
    document = await get_document_by_id(document_id)

    if document is None:
        return None

    return document.get("versions", [])
