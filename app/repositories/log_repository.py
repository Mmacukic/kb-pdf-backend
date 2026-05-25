from datetime import datetime, timezone

from app.db.mongo import get_database


FILE_ACTION_LOGS_COLLECTION = "file_action_logs"


async def create_file_action_log(
    action: str,
    username: str,
    severity: str,
    service: str,
    document_id: str | None = None,
    filename: str | None = None,
    metadata: dict | None = None
) -> dict:
    db = get_database()

    log = {
        "timestamp": datetime.now(timezone.utc),
        "severity": severity,
        "service": service,
        "action": action,
        "username": username,
        "document_id": document_id,
        "filename": filename,
        "metadata": metadata or {}
    }

    result = await db[FILE_ACTION_LOGS_COLLECTION].insert_one(log)

    log["id"] = str(result.inserted_id)

    return log