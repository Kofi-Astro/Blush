import mimetypes
import uuid

from fastapi import HTTPException, UploadFile, status
from supabase import Client, create_client

from .config import get_settings

settings = get_settings()

_client: Client | None = None


def get_storage_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


async def upload_media_file(file: UploadFile, folder: str) -> str:
    """Uploads a file to the `media` bucket and returns its public URL."""
    extension = mimetypes.guess_extension(file.content_type or "") or ""
    if not extension and file.filename and "." in file.filename:
        extension = "." + file.filename.rsplit(".", 1)[-1]

    object_path = f"{folder}/{uuid.uuid4().hex}{extension}"
    contents = await file.read()

    client = get_storage_client()
    try:
        client.storage.from_(settings.supabase_media_bucket).upload(
            object_path,
            contents,
            {"content-type": file.content_type or "application/octet-stream"},
        )
    except Exception as exc:  # supabase-py raises its own StorageException
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upload to storage failed: {exc}",
        ) from exc

    return client.storage.from_(settings.supabase_media_bucket).get_public_url(object_path)
