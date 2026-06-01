from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from minio.error import S3Error

from app.repositories.document_repository import (
    add_document_version,
    create_document_metadata,
    get_document_by_id,
    get_document_versions,
    list_active_documents,
    mark_document_as_deleted,
    update_document_indexing_status
)
from app.schemas.auth import CurrentUser
from app.services.log_service import log_file_action
from app.services.storage_service import (
    delete_pdf_from_storage,
    download_pdf_from_storage,
    upload_pdf_bytes_to_storage
)

from app.services.rag_indexing_service import index_pdf_for_rag
from app.repositories.vector_repository import delete_chunks_by_source


async def _index_pdf_background(
    document_id: str,
    version: int,
    filename: str,
    file_bytes: bytes,
    username: str
) -> None:
    status_updated = await update_document_indexing_status(
        document_id=document_id,
        version=version,
        status="processing"
    )

    if not status_updated:
        return

    try:
        current_document = await get_document_by_id(document_id)

        if (
            current_document is None
            or current_document.get("current_version") != version
            or current_document.get("is_deleted")
        ):
            return

        chunks_count = await index_pdf_for_rag(
            document_id=document_id,
            version=version,
            filename=filename,
            file_bytes=file_bytes,
            username=username
        )

        if chunks_count is None:
            return

        await update_document_indexing_status(
            document_id=document_id,
            version=version,
            status="indexed",
            chunks_count=chunks_count
        )
    except Exception as exception:
        error = str(exception)

        await update_document_indexing_status(
            document_id=document_id,
            version=version,
            status="failed",
            error=error
        )

        await log_file_action(
            action="rag_pdf_index_failed",
            username=username,
            document_id=document_id,
            filename=filename,
            severity="ERROR",
            metadata={
                "version": version,
                "error": error
            }
        )


async def _delete_document_assets_background(
    document_id: str,
    document: dict,
    username: str
) -> None:
    storage_keys = {
        version["storage_key"]
        for version in document.get("versions", [])
        if version.get("storage_key")
    }

    storage_keys.add(document["storage_key"])

    for storage_key in storage_keys:
        try:
            delete_pdf_from_storage(storage_key=storage_key)
        except S3Error as exception:
            await log_file_action(
                action="delete_storage_failed",
                username=username,
                document_id=document_id,
                filename=document.get("filename"),
                severity="ERROR",
                metadata={
                    "storage_key": storage_key,
                    "error": str(exception)
                }
            )

    try:
        await delete_chunks_by_source(
            source_type="pdf",
            source_id=document_id
        )
    except Exception as exception:
        await log_file_action(
            action="delete_vectors_failed",
            username=username,
            document_id=document_id,
            filename=document.get("filename"),
            severity="ERROR",
            metadata={
                "error": str(exception)
            }
        )

def validate_pdf_file(file: UploadFile) -> str:
    if file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required"
        )

    original_filename = Path(file.filename).name

    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only application/pdf is allowed"
        )

    return original_filename


async def get_existing_document_or_404(document_id: str) -> dict:
    document = await get_document_by_id(document_id)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document


async def upload_document(
    file: UploadFile,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks
) -> dict:
    original_filename = validate_pdf_file(file)

    file_uuid = str(uuid4())
    storage_key = f"documents/{file_uuid}/v1/{original_filename}"

    file_bytes = await file.read()

    storage_result = upload_pdf_bytes_to_storage(
        file_bytes=file_bytes,
        storage_key=storage_key,
        content_type=file.content_type or "application/pdf"
    )

    document = await create_document_metadata(
        filename=original_filename,
        content_type=storage_result["content_type"],
        size=storage_result["size"],
        storage_key=storage_result["storage_key"],
        uploaded_by=current_user.username
    )

    await log_file_action(
        action="upload",
        username=current_user.username,
        document_id=document["id"],
        filename=original_filename,
        severity="INFO",
        metadata={
            "storage_key": storage_key,
            "size": storage_result["size"],
            "version": 1
        }
    )

    background_tasks.add_task(
        _index_pdf_background,
        document_id=document["id"],
        version=document["current_version"],
        filename=document["filename"],
        file_bytes=file_bytes,
        username=current_user.username
    )

    return document


async def list_documents() -> list[dict]:
    return await list_active_documents()


async def download_document(
    document_id: str,
    current_user: CurrentUser
) -> dict:
    document = await get_existing_document_or_404(document_id)

    try:
        file_data = download_pdf_from_storage(
            storage_key=document["storage_key"]
        )
    except S3Error:
        await log_file_action(
            action="download",
            username=current_user.username,
            document_id=document_id,
            filename=document.get("filename"),
            severity="ERROR",
            metadata={
                "reason": "Failed to download file from storage"
            }
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file from storage"
        )

    await log_file_action(
        action="download",
        username=current_user.username,
        document_id=document_id,
        filename=document["filename"],
        severity="INFO",
        metadata={
            "storage_key": document["storage_key"],
            "version": document["current_version"]
        }
    )

    return {
        "file_data": file_data,
        "filename": document["filename"],
        "content_type": document["content_type"]
    }


async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks
) -> dict:
    document = await get_existing_document_or_404(document_id)

    deleted = await mark_document_as_deleted(
        document_id=document_id,
        deleted_by=current_user.username
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or already deleted"
        )

    background_tasks.add_task(
        _delete_document_assets_background,
        document_id=document_id,
        document=document,
        username=current_user.username
    )

    await log_file_action(
        action="delete",
        username=current_user.username,
        document_id=document_id,
        filename=document["filename"],
        severity="INFO",
        metadata={
            "storage_key": document["storage_key"],
            "version": document["current_version"]
        }
    )

    return {
        "message": "Document deleted successfully",
        "document_id": document_id
    }


async def upload_new_document_version(
    document_id: str,
    file: UploadFile,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks
) -> dict:
    document = await get_existing_document_or_404(document_id)

    original_filename = validate_pdf_file(file)

    new_version = document["current_version"] + 1
    storage_key = f"documents/{document_id}/v{new_version}/{original_filename}"

    file_bytes = await file.read()

    storage_result = upload_pdf_bytes_to_storage(
        file_bytes=file_bytes,
        storage_key=storage_key,
        content_type=file.content_type or "application/pdf"
    )

    version_data = {
        "version": new_version,
        "filename": original_filename,
        "content_type": storage_result["content_type"],
        "size": storage_result["size"],
        "storage_key": storage_result["storage_key"],
        "uploaded_by": current_user.username,
        "uploaded_at": datetime.now(timezone.utc)
    }

    updated_document = await add_document_version(
        document_id=document_id,
        version_data={
            **version_data,
            "indexing_status": "pending",
            "indexing_error": None,
            "indexed_at": None,
            "chunks_count": 0
        },
        expected_current_version=document["current_version"]
    )

    if updated_document is None:
        try:
            delete_pdf_from_storage(storage_key=storage_key)
        except S3Error:
            pass

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document version changed. Retry the upload."
        )

    await log_file_action(
        action="version_upload",
        username=current_user.username,
        document_id=document_id,
        filename=original_filename,
        severity="INFO",
        metadata={
            "storage_key": storage_key,
            "version": new_version,
            "previous_version": document["current_version"],
            "size": storage_result["size"]
        }
    )

    background_tasks.add_task(
        _index_pdf_background,
        document_id=document_id,
        version=new_version,
        filename=original_filename,
        file_bytes=file_bytes,
        username=current_user.username
    )

    return updated_document


async def list_document_versions(
    document_id: str,
    current_user: CurrentUser
) -> list[dict]:
    versions = await get_document_versions(document_id)

    if versions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    await log_file_action(
        action="version_list",
        username=current_user.username,
        document_id=document_id,
        severity="INFO",
        metadata={
            "versions_count": len(versions)
        }
    )

    return versions
