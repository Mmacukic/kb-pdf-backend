from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user, require_admin
from app.schemas.auth import CurrentUser
from app.schemas.document import (
        DocumentResponse,
        DeleteDocumentResponse,
        DocumentVersionResponse
        )
from app.services.document_service import (
    delete_document,
    download_document,
    list_documents,
    upload_document,
    list_document_versions,
    upload_new_document_version
)

router = APIRouter()


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_admin)
):
    return await upload_document(
        file=file,
        current_user=current_user,
        background_tasks=background_tasks
    )


@router.get(
    "",
    response_model=list[DocumentResponse]
)
async def get_documents(
    _current_user: CurrentUser = Depends(get_current_user)
):
    return await list_documents()


@router.get(
    "/{document_id}/download"
)
async def download_pdf(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    result = await download_document(
        document_id=document_id,
        current_user=current_user
    )

    return StreamingResponse(
        BytesIO(result["file_data"]),
        media_type=result["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"'
        }
    )


@router.delete(
    "/{document_id}",
    response_model=DeleteDocumentResponse
)
async def delete_pdf(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_admin)
):
    return await delete_document(
        document_id=document_id,
        current_user=current_user,
        background_tasks=background_tasks
    )

@router.post(
    "/{document_id}/versions",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_pdf_version(
    document_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_admin)
):
    return await upload_new_document_version(
        document_id=document_id,
        file=file,
        current_user=current_user,
        background_tasks=background_tasks
    )


@router.get(
    "/{document_id}/versions",
    response_model=list[DocumentVersionResponse]
)
async def get_pdf_versions(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    return await list_document_versions(
        document_id=document_id,
        current_user=current_user
    )
