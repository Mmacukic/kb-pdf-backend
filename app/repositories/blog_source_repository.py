from datetime import datetime, timezone

from bson import ObjectId

from app.db.mongo import get_database

BLOG_SOURCES_COLLECTION = "blog_sources"

async def create_blog_source(
    url: str,
    title: str,
    scraped_by: str,
    scraper: str,
    chunks_count: int,
    extracted_text: str | None = None,
    source_metadata: dict | None = None
) -> dict:
    db = get_database()

    now = datetime.now(timezone.utc)

    blog_source = {
        "url": url,
        "title": title,
        "scraped_by": scraped_by,
        "scraper": scraper,
        "extracted_text": extracted_text,
        "source_metadata": source_metadata or {},
        "chunks_count": chunks_count,
        "indexing_status": "pending",
        "indexing_error": None,
        "indexed_at": None,
        "approved": True,
        "created_at": now,
        "updated_at": now,
        "is_deleted": False
    }

    result = await db[BLOG_SOURCES_COLLECTION].insert_one(blog_source)

    blog_source["_id"] = result.inserted_id

    return serialize_blog_source(blog_source)


async def list_active_blog_sources() -> list[dict]:
    db = get_database()

    cursor = db[BLOG_SOURCES_COLLECTION].find({
        "is_deleted": False
    }).sort("created_at", -1)

    sources = []

    async for source in cursor:
        sources.append(serialize_blog_source(source))

    return sources


async def get_blog_source_by_id(source_id: str) -> dict | None:
    db = get_database()

    object_id = to_object_id(source_id)

    if object_id is None:
        return None

    source = await db[BLOG_SOURCES_COLLECTION].find_one({
        "_id": object_id,
        "is_deleted": False
    })

    if source is None:
        return None

    return serialize_blog_source(source)


async def mark_blog_source_as_deleted(
    source_id: str,
    deleted_by: str
) -> bool:
    db = get_database()

    object_id = to_object_id(source_id)

    if object_id is None:
        return False

    result = await db[BLOG_SOURCES_COLLECTION].update_one(
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

async def update_blog_source_indexing_status(
    source_id: str,
    status: str,
    chunks_count: int | None = None,
    error: str | None = None
) -> bool:
    db = get_database()

    object_id = to_object_id(source_id)

    if object_id is None:
        return False

    now = datetime.now(timezone.utc)

    fields = {
        "indexing_status": status,
        "indexing_error": error,
        "updated_at": now
    }

    if chunks_count is not None:
        fields["chunks_count"] = chunks_count

    if status == "indexed":
        fields["indexed_at"] = now

    result = await db[BLOG_SOURCES_COLLECTION].update_one(
        {
            "_id": object_id,
            "is_deleted": False
        },
        {
            "$set": fields
        }
    )

    return result.modified_count == 1

async def update_blog_source_scrape_result(
    source_id: str,
    url: str,
    title: str,
    scraper: str,
    status: str,
    chunks_count: int | None = None,
    error: str | None = None,
    extracted_text: str | None = None,
    source_metadata: dict | None = None
) -> bool:
    db = get_database()

    object_id = to_object_id(source_id)

    if object_id is None:
        return False

    now = datetime.now(timezone.utc)

    fields = {
        "url": url,
        "title": title,
        "scraper": scraper,
        "source_metadata": source_metadata or {},
        "indexing_status": status,
        "indexing_error": error,
        "updated_at": now
    }

    if extracted_text is not None:
        fields["extracted_text"] = extracted_text

    if chunks_count is not None:
        fields["chunks_count"] = chunks_count

    if status == "indexed":
        fields["indexed_at"] = now

    result = await db[BLOG_SOURCES_COLLECTION].update_one(
        {
            "_id": object_id,
            "is_deleted": False
        },
        {
            "$set": fields
        }
    )

    return result.modified_count == 1

async def create_blog_source_indexes() -> None:
    db = get_database()

    await db[BLOG_SOURCES_COLLECTION].create_index("url")
    await db[BLOG_SOURCES_COLLECTION].create_index("created_at")
    await db[BLOG_SOURCES_COLLECTION].create_index("is_deleted")
    await db[BLOG_SOURCES_COLLECTION].create_index("indexing_status")

def serialize_blog_source(blog_source: dict) -> dict:
    blog_source["id"] = str(blog_source["_id"])
    blog_source.pop("_id", None)
    return blog_source

def to_object_id(source_id: str) -> ObjectId | None:
    try:
        return ObjectId(source_id)
    except Exception:
        return None