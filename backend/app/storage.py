# Handles uploading admin-added photos/videos to Supabase Storage (the
# "media" bucket) — used by routers/uploads.py whenever the admin dashboard
# adds a product photo or hero video. Routes images/videos through the
# watermarking step in watermark.py before they ever get saved.

import mimetypes
import uuid

from fastapi import HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from supabase import Client, create_client

from .config import get_settings
from .watermark import apply_watermark, apply_watermark_to_video

settings = get_settings()

_client: Client | None = None


def get_storage_client() -> Client:
    """Reuses one Supabase client across requests instead of reconnecting every time."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


async def upload_media_file(file: UploadFile, folder: str, watermark: str | None = None) -> str:
    """Uploads a file to the `media` bucket and returns its public URL.

    Photos and videos both get a tiled brand-mark watermark first when
    `watermark` is "fashion" or "hair" — piracy/screenshot deterrence for
    anything customer-facing (see watermark.py; video needs ffmpeg on PATH,
    which railpack.json installs at deploy time)."""
    content_type = file.content_type or "application/octet-stream"
    contents = await file.read()

    if watermark in ("fashion", "hair") and content_type.startswith("image/"):
        contents = await run_in_threadpool(apply_watermark, contents, watermark)
        content_type = "image/jpeg"
        extension = ".jpg"
    elif watermark in ("fashion", "hair") and content_type.startswith("video/"):
        try:
            contents = await run_in_threadpool(apply_watermark_to_video, contents, watermark)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Video watermarking failed: {exc}",
            ) from exc
        content_type = "video/mp4"
        extension = ".mp4"
    else:
        # No watermark requested (or not an image/video) — upload as-is.
        extension = mimetypes.guess_extension(content_type) or ""
        if not extension and file.filename and "." in file.filename:
            extension = "." + file.filename.rsplit(".", 1)[-1]

    # Random filename (not the original name) so uploads never collide or
    # leak the customer's/admin's local filesystem naming.
    object_path = f"{folder}/{uuid.uuid4().hex}{extension}"

    client = get_storage_client()
    try:
        client.storage.from_(settings.supabase_media_bucket).upload(
            object_path,
            contents,
            {"content-type": content_type},
        )
    except Exception as exc:  # supabase-py raises its own StorageException
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upload to storage failed: {exc}",
        ) from exc

    # The permanent public URL that gets saved into the product/hero_media
    # row and used directly as the <img>/<video> src on the live site.
    return client.storage.from_(settings.supabase_media_bucket).get_public_url(object_path)
