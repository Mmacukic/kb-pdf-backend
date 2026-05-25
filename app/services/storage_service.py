from io import BytesIO

from fastapi import UploadFile
from minio import Minio


from app.core.config import settings


minio_client = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure
)


def ensure_bucket_exists() -> None:
    bucket_exists = minio_client.bucket_exists(
        settings.minio_bucket_name
    )

    if not bucket_exists:
        minio_client.make_bucket(
            settings.minio_bucket_name
        )


# async def upload_pdf_to_storage(
#     file: UploadFile,
#     storage_key: str
# ) -> dict:
#     file_content = await file.read()
#
#     file_stream = BytesIO(file_content)
#
#     minio_client.put_object(
#         bucket_name=settings.minio_bucket_name,
#         object_name=storage_key,
#         data=file_stream,
#         length=len(file_content),
#         content_type=file.content_type or "application/pdf"
#     )
#
#     return {
#         "storage_key": storage_key,
#         "size": len(file_content),
#         "content_type": file.content_type or "application/pdf"
#     }


def upload_pdf_bytes_to_storage(
    file_bytes: bytes,
    storage_key: str,
    content_type: str = "application/pdf"
) -> dict:
    file_stream = BytesIO(file_bytes)

    minio_client.put_object(
        bucket_name=settings.minio_bucket_name,
        object_name=storage_key,
        data=file_stream,
        length=len(file_bytes),
        content_type=content_type
    )

    return {
        "storage_key": storage_key,
        "size": len(file_bytes),
        "content_type": content_type
    }

def download_pdf_from_storage(storage_key: str) -> bytes:
    response = minio_client.get_object(
        bucket_name=settings.minio_bucket_name,
        object_name=storage_key
    )

    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_pdf_from_storage(storage_key: str) -> None:
    minio_client.remove_object(
        bucket_name=settings.minio_bucket_name,
        object_name=storage_key
    )