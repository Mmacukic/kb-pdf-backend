from app.core.config import settings
from app.repositories.log_repository import create_file_action_log


async def log_file_action(
    action: str,
    username: str,
    document_id: str | None = None,
    filename: str | None = None,
    severity: str = "INFO",
    metadata: dict | None = None
) -> dict:
    return await create_file_action_log(
        action=action,
        username=username,
        severity=severity,
        service=settings.service_name,
        document_id=document_id,
        filename=filename,
        metadata=metadata
    )